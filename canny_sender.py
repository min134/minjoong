import os
import time

import cv2
from picamera2 import Picamera2


WIDTH = 640
HEIGHT = 480
FPS = 30
PORT = 5000
HOST = os.environ.get("VIDEO_HOST", "127.0.0.1")


def create_writer() -> cv2.VideoWriter:
    pipeline = (
        "appsrc name=src is-live=true block=true format=time "
        f"caps=video/x-raw,format=BGR,width={WIDTH},height={HEIGHT},framerate={FPS}/1 "
        "! videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast "
        "! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={HOST} port={PORT} sync=false"
    )
    writer = cv2.VideoWriter(
        pipeline,
        cv2.CAP_GSTREAMER,
        0,
        FPS,
        (WIDTH, HEIGHT),
        True,
    )
    if not writer.isOpened():
        raise RuntimeError("GStreamer video writer could not be opened")
    return writer


picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"format": "RGB888", "size": (WIDTH, HEIGHT)},
)
picam2.configure(config)
writer = None

try:
    writer = create_writer()
    picam2.start()
    time.sleep(0.5)

    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        writer.write(edge_frame)
except KeyboardInterrupt:
    pass
finally:
    if writer is not None:
        writer.release()
    picam2.stop()
    picam2.close()
