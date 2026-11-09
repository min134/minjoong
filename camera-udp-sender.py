import argparse
import os
import sys
import time

import cv2

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
except (ImportError, ValueError) as exc:
    print(
        "Python GI/GStreamer is required. Install it with:\n"
        "sudo apt update && sudo apt install -y python3-gi "
        "gir1.2-gstreamer-1.0 gstreamer1.0-tools "
        "gstreamer1.0-plugins-base gstreamer1.0-plugins-good "
        "gstreamer1.0-plugins-ugly",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from picamera2 import Picamera2


PORT = 5000
PROFILES = {
    "720p-2000": (1280, 720, 2000),
    "640x480-500": (640, 480, 500),
    "720p-4000": (1280, 720, 4000),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send Canny camera frames over RTP/H264 UDP")
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILES),
        default=os.environ.get("VIDEO_PROFILE", "640x480-500"),
        help="resolution and bitrate preset (default: %(default)s)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("VIDEO_HOST", "192.168.0.153"),
        help="receiver address; VIDEO_HOST is used when omitted",
    )
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args


def start_gstreamer(width: int, height: int, fps: int, bitrate: int, host: str, port: int):
    Gst.init(None)
    pipeline = Gst.parse_launch(
        "appsrc name=source is-live=true format=time do-timestamp=true "
        f"caps=video/x-raw,format=BGR,width={width},height={height},framerate={fps}/1 "
        "! videoconvert "
        f"! x264enc tune=zerolatency speed-preset=ultrafast bitrate={bitrate} "
        "! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={host} port={port} sync=false"
    )
    appsrc = pipeline.get_by_name("source")
    if appsrc is None:
        pipeline.set_state(Gst.State.NULL)
        raise RuntimeError("GStreamer appsrc element was not created")
    result = pipeline.set_state(Gst.State.PLAYING)
    if result == Gst.StateChangeReturn.FAILURE:
        pipeline.set_state(Gst.State.NULL)
        raise RuntimeError("GStreamer pipeline failed to enter PLAYING")
    _, state, _ = pipeline.get_state(5 * Gst.SECOND)
    if state != Gst.State.PLAYING:
        pipeline.set_state(Gst.State.NULL)
        raise RuntimeError(f"GStreamer pipeline state is {state.value_nick}, not PLAYING")
    return pipeline, appsrc


args = parse_args()
WIDTH, HEIGHT, BITRATE = PROFILES[args.profile]
FPS = 30

try:
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"format": "RGB888", "size": (WIDTH, HEIGHT)},
    )
    picam2.configure(config)
except Exception as exc:
    print(
        "No camera was detected, so the sender cannot start. Run "
        "rpicam-hello --list-cameras or libcamera-hello --list-cameras, "
        f"then check the camera cable and camera enable setting. ({exc})",
        file=sys.stderr,
    )
    sys.exit(1)

stream = None
appsrc = None
camera_started = False


def write_frame(frame) -> None:
    if appsrc is None:
        raise RuntimeError("GStreamer appsrc is not available")
    result = appsrc.emit("push-buffer", Gst.Buffer.new_wrapped(frame.tobytes()))
    if result != Gst.FlowReturn.OK:
        raise RuntimeError(f"GStreamer push-buffer failed: {result.value_nick}")


try:
    picam2.start()
    camera_started = True
    time.sleep(0.5)

    frame = picam2.capture_array()
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    stream, appsrc = start_gstreamer(WIDTH, HEIGHT, FPS, BITRATE, args.host, args.port)
    write_frame(edge_frame)

    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        write_frame(edge_frame)
except KeyboardInterrupt:
    pass
except (BrokenPipeError, RuntimeError) as exc:
    print(f"Sender stopped: {exc}", file=sys.stderr)
finally:
    if stream is not None:
        if appsrc is not None:
            appsrc.emit("end-of-stream")
        stream.set_state(Gst.State.NULL)
    if camera_started:
        picam2.stop()
    picam2.close()
