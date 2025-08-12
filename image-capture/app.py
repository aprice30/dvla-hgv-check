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
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 10
    print(f"Camera FPS: {fps}")

    motion_processor = FileSavingMotionProcessor(output_dir="/app/output")
    detector = MotionDetector(fps=int(fps), motionProcessor=motion_processor)

    ret, frame = cap.read()
    if not ret:
        print("Failed to read first frame")
        return
    detector.loadFirstFrame(frame)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read frame")
            break

        detector.process(frame)

    cap.release()

if __name__ == "__main__":
    main()
