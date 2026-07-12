import cv2
import logging
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class MotionDetector:
    def __init__(self, fps, queue, min_motion_area=10000):
        """
        Args:
            fps: Expected/actual frames per second of the video source.
            queue: The Python queue.Queue to write motion frame payloads to.
            min_motion_area: Minimum bounding box contour area to qualify as motion.
        """
        self.queue = queue
        self.min_motion_area = min_motion_area
        self.fps = fps

        self.frame_width = None
        self.frame_height = None
        self.frame1 = None
        self.frame_count = 0

        # Motion event tracking
        self.frame_with_last_motion = 0
        self.timestamp_of_first_motion = None
        self.buffer = []

    def load_first_frame(self, frame):
        self.frame1 = frame.copy()
        self.frame_height, self.frame_width, _ = frame.shape
        self.frame_count = 1

    def rectangles_intersect(self, rect1, rect2):
        x1_min, y1_min, x1_max, y1_max = rect1
        x2_min, y2_min, x2_max, y2_max = rect2
        
        intersect = not (x1_max < x2_min or x1_min > x2_max or y1_max < y2_min or y1_min > y2_max)
        if not intersect:
            return False, None
        
        ex1 = min(x1_min, x2_min)
        ey1 = min(y1_min, y2_min)
        ex2 = max(x1_max, x2_max)
        ey2 = max(y1_max, y2_max)
        return True, (ex1, ey1, ex2, ey2)

    def merge_intersecting_rectangles(self, rectangles):
        merged = []
        while rectangles:
            current = rectangles.pop(0)
            merged_flag = False
            for i in range(len(rectangles)):
                intersect, enclosing_rect = self.rectangles_intersect(current, rectangles[i])
                if intersect:
                    current = enclosing_rect
                    rectangles.pop(i)
                    merged_flag = True
                    break
            if merged_flag:
                rectangles.append(current)
            else:
                merged.append(current)
        return merged

    def process(self, frame):
        """
        Processes a single frame for motion detection.
        If motion is detected, saves frame to self.buffer.
        If motion stops, writes the buffer payload to the queue.
        """
        if self.frame1 is None:
            self.load_first_frame(frame)
            return frame

        self.frame_count += 1
        frame2 = frame.copy()

        # Step 1: Calculate pixel difference between successive frames
        diff = cv2.absdiff(self.frame1, frame2)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)

        # Step 2: Find contours of moving areas
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        motion = False
        rectangles_to_merge = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_motion_area:
                continue

            motion = True
            if self.timestamp_of_first_motion is None:
                self.timestamp_of_first_motion = datetime.now()
                logger.info("[Motion] Motion started detected.")

            (x, y, w, h) = cv2.boundingRect(contour)
            rectangles_to_merge.append((x, y, x + w, y + h))

        # Accumulate frames during motion
        if motion:
            self.buffer.append(frame2)
            self.frame_with_last_motion = self.frame_count
        elif self.timestamp_of_first_motion is not None and self.frame_with_last_motion > self.frame_count - max(1, int(self.fps * 0.25)):
            # Keep saving frames for 250ms after last motion to smooth out breaks
            self.buffer.append(frame2)
        elif self.timestamp_of_first_motion is not None:
            # Motion stopped completely! Queue the batch of frames for the Detection Engine
            payload = {
                "timestamp": self.timestamp_of_first_motion,
                "frames": list(self.buffer)
            }
            logger.info(f"[Motion] Motion ended. Queueing batch of {len(self.buffer)} frames.")
            self.queue.put(payload)
            
            # Reset event tracking
            self.buffer = []
            self.timestamp_of_first_motion = None

        # Draw visual bounding box output for debugging/monitoring
        annotated_frame = frame2.copy()
        for rect in self.merge_intersecting_rectangles(rectangles_to_merge):
            (x1, y1, x2, y2) = rect
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        self.frame1 = frame2
        return annotated_frame
