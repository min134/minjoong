import argparse
import os
import shutil
import subprocess
import sys
import threading
import time

import cv2
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


def start_gstreamer(
    width: int, height: int, fps: int, bitrate: int, host: str, port: int
) -> subprocess.Popen:
    global stderr_thread
    gst_launch = shutil.which("gst-launch-1.0")
    if gst_launch is None:
        raise RuntimeError("gst-launch-1.0 was not found in PATH")
    stream = subprocess.Popen(
        [
            gst_launch,
            "-e",
            "fdsrc",
            "fd=0",
            f"blocksize={width * height * 3}",
            "do-timestamp=true",
            "!",
            "rawvideoparse",
            "format=bgr",
            f"width={width}",
            f"height={height}",
            f"framerate={fps}/1",
            "!",
            "queue",
            "max-size-buffers=2",
            "leaky=downstream",
            "!",
            "videoconvert",
            "!",
            "x264enc",
            "tune=zerolatency",
            "speed-preset=ultrafast",
            f"bitrate={bitrate}",
            "!",
            "rtph264pay",
            "config-interval=1",
            "pt=96",
            "!",
            "udpsink",
            f"host={host}",
            f"port={port}",
            "sync=false",
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    stderr_thread = threading.Thread(
        target=report_gstreamer_stderr,
        args=(stream,),
        daemon=True,
    )
    stderr_thread.start()
    return stream


def report_gstreamer_stderr(process: subprocess.Popen) -> None:
    if process.stderr is None:
        return
    for line in iter(process.stderr.readline, b""):
        print(f"[gstreamer] {line.decode(errors='replace')}", end="", file=sys.stderr)


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
stderr_thread = None
camera_started = False


def write_frame(frame) -> None:
    if stream is None or stream.stdin is None:
        raise RuntimeError("GStreamer stdin is not available")
    if stream.poll() is not None:
        raise RuntimeError(f"GStreamer exited before frame write (code {stream.returncode})")
    stream.stdin.write(frame.tobytes())
    stream.stdin.flush()


try:
    picam2.start()
    camera_started = True
    time.sleep(0.5)

    frame = picam2.capture_array()
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    stream = start_gstreamer(WIDTH, HEIGHT, FPS, BITRATE, args.host, args.port)
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
        if stream.stdin is not None and stream.poll() is None:
            stream.stdin.close()
        if stream.poll() is None:
            try:
                stream.wait(timeout=2)
            except subprocess.TimeoutExpired:
                stream.terminate()
                try:
                    stream.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    stream.kill()
                    stream.wait()
        if stderr_thread is not None:
            stderr_thread.join(timeout=1)
    if camera_started:
        picam2.stop()
    picam2.close()
