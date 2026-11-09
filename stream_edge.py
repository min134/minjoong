import sys
import time
import cv2
from picamera2 import Picamera2

PC_IP = "192.168.0.153"
PORT = 5000
FPS = 30

settings = {
    "1": (1280, 720, 2000),
    "2": (640, 480, 500),
    "3": (1280, 720, 4000),
}

mode = sys.argv[1] if len(sys.argv) > 1 else "1"
if mode not in settings:
    sys.exit("Usage: python3 stream_edge.py [1|2|3]")

W, H, BITRATE = settings[mode]

pipeline = (
    "appsrc ! videoconvert ! video/x-raw,format=I420 ! "
    "x264enc tune=zerolatency speed-preset=ultrafast "
    f"bitrate={BITRATE} key-int-max=30 ! "
    "rtph264pay config-interval=1 pt=96 ! "
    f"udpsink host={PC_IP} port={PORT}"
)

out = cv2.VideoWriter(pipeline, cv2.CAP_GSTREAMER, 0, FPS, (W, H), True)
if not out.isOpened():
    out.release()
    raise RuntimeError("VideoWriter initialization failed. Check GStreamer and pipeline.")

picam2 = Picamera2()
started = False
try:
    picam2.configure(picam2.create_video_configuration(
        main={"format": "RGB888", "size": (W, H)},
        controls={"FrameRate": FPS}
    ))
    picam2.start()
    started = True
    time.sleep(0.5)

    print(f"Mode {mode}: {W}x{H}, requested {FPS} fps, {BITRATE} kbps")
    print(f"Sending to {PC_IP}:{PORT} (Ctrl+C to stop)")

    frames = 0
    start_time = time.monotonic()
    while True:
        frame = picam2.capture_array()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edge = cv2.Canny(gray, 100, 200)
        out.write(cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR))

        frames += 1
        elapsed = time.monotonic() - start_time
        if elapsed >= 5:
            print(f"Processing/send loop: {frames / elapsed:.1f} fps")
            frames = 0
            start_time = time.monotonic()
except KeyboardInterrupt:
    print("Stopped")
finally:
    if started:
        picam2.stop()
    picam2.close()
    out.release()
