import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
    force=True
)

import cv2
import os
from datetime import datetime
from motion_detector.motion_detector import MotionDetector

from picamera2 import Picamera2

class FileSavingMotionProcessor:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def process(self, timestamp, frame_count, buffer):
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(self.output_dir, ts_str)
        os.makedirs(folder, exist_ok=True)
        for i, frame in enumerate(buffer):
            filename = os.path.join(folder, f"frame_{frame_count - len(buffer) + i}.jpg")
            cv2.imwrite(filename, frame)
        print(f"Saved {len(buffer)} frames to {folder}")

def main():
    # Initialize PiCamera2
    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()

    fps = 10  # Picamera2 doesn’t always expose FPS directly, set a sensible default
    print(f"Camera FPS (assumed): {fps}")

    motion_processor = FileSavingMotionProcessor(output_dir="/app/output")
    detector = MotionDetector(fps=int(fps), motionProcessor=motion_processor)

    # Capture the first frame
    frame = picam2.capture_array()
    if frame is None:
        print("Failed to read first frame")
        return
    detector.loadFirstFrame(frame)

    frame_count = 0
    while True:
        frame = picam2.capture_array()
        if frame is None:
            print("Failed to read frame")
            break

        frame_count += 1
        detector.process(frame)

if __name__ == "__main__":
    main()