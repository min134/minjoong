import os
import subprocess
import time

import cv2
from picamera2 import Picamera2


WIDTH = 640
HEIGHT = 480
FPS = 30
PORT = 5000
HOST = os.environ.get("VIDEO_HOST", "127.0.0.1")


def start_gstreamer() -> subprocess.Popen:
    return subprocess.Popen(
        [
            "gst-launch-1.0",
            "fdsrc",
            "fd=0",
            "!",
            "rawvideoparse",
            "format=bgr",
            f"width={WIDTH}",
            f"height={HEIGHT}",
            f"framerate={FPS}/1",
            "!",
            "videoconvert",
            "!",
            "x264enc",
            "tune=zerolatency",
            "speed-preset=ultrafast",
            "!",
            "rtph264pay",
            "config-interval=1",
            "pt=96",
            "!",
            "udpsink",
            f"host={HOST}",
            f"port={PORT}",
            "sync=false",
        ],
        stdin=subprocess.PIPE,
    )


picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (WIDTH, HEIGHT)},
)
picam2.configure(config)
stream = None

try:
    stream = start_gstreamer()
    if stream.stdin is None:
        raise RuntimeError("Could not open GStreamer input")

    picam2.start()
    time.sleep(0.5)

    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        stream.stdin.write(edge_frame.tobytes())
except KeyboardInterrupt:
    pass
finally:
    if stream is not None:
        if stream.stdin is not None:
            stream.stdin.close()
        stream.wait()
    picam2.stop()
    picam2.close()
