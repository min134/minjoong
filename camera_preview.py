from picamera2 import Picamera2
import cv2
import time

picam2 = Picamera2()

try:
    config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(0.5)

    while True:
        frame = picam2.capture_array()
        cv2.imshow("Camera-window", frame)

        if cv2.waitKey(1) == 27:
            break
finally:
    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()
