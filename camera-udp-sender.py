import argparse
import os
import shutil
import subprocess
import sys
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
    gst_launch = shutil.which("gst-launch-1.0")
    if gst_launch is None:
        raise RuntimeError("gst-launch-1.0 was not found in PATH")
    return subprocess.Popen(
        [
            gst_launch,
            "fdsrc",
            "fd=0",
            "!",
            "rawvideoparse",
            "format=bgr",
            f"width={width}",
            f"height={height}",
            f"framerate={fps}/1",
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
    )


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
camera_started = False

try:
    stream = start_gstreamer(WIDTH, HEIGHT, FPS, BITRATE, args.host, args.port)
    if stream.stdin is None:
        raise RuntimeError("Could not open GStreamer input")

    picam2.start()
    camera_started = True
    time.sleep(0.5)

    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        stream.stdin.write(edge_frame.tobytes())
except (KeyboardInterrupt, BrokenPipeError):
    pass
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
    if camera_started:
        picam2.stop()
    picam2.close()
