import cv2 # type: ignore
import logging
from collections import deque
from datetime import datetime
from motion_detector.motion_processor import MotionProcessorInterface

logger = logging.getLogger(__name__)

class MotionDetector:
    def __init__(self, fps, motionProcessor: MotionProcessorInterface, minMotionArea = 10000):
        self.motionProcessor = motionProcessor
        self.minMotionArea = minMotionArea

        self.fps = fps

        # Used to smooth out the frames of motion when we lose motion for a few frames
        self.frameWithLastMotion = 0
        # Used to know when motion started so we can timestamp it
        self.timestampOfFirstMotionFrame = None

        # Initialize the circular buffer
        self.buffer = deque()
    
    def loadFirstFrame(self, frame1):
        self.frame1 = frame1
        self.frameCount = 1

    def rectangles_intersect(self, rect1, rect2):
        """ 
        Check if two rectangles intersect and return the minimum enclosing rectangle.
        Rectangles are in (x1, y1, x2, y2) format.
        """
        x1_min, y1_min, x1_max, y1_max = rect1
        x2_min, y2_min, x2_max, y2_max = rect2
        
        # Check for intersection
        intersect = not (x1_max < x2_min or x1_min > x2_max or y1_max < y2_min or y1_min > y2_max)
        
        if not intersect:
            return False, None
        
        # Calculate the minimum enclosing rectangle
        ex1 = min(x1_min, x2_min)
        ey1 = min(y1_min, y2_min)
        ex2 = max(x1_max, x2_max)
        ey2 = max(y1_max, y2_max)
        
        enclosing_rect = (ex1, ey1, ex2, ey2)
        
        return True, enclosing_rect

    def merge_intersecting_rectangles(self, rectangles):
        merged = []
        
        while rectangles:
            # Start with the first rectangle
            current = rectangles.pop(0)
            merged_flag = False
            
            for i in range(len(rectangles)):
                intersect, enclosing_rect = self.rectangles_intersect(current, rectangles[i])
                if intersect:
                    # Merge the intersecting rectangles
                    current = enclosing_rect
                    rectangles.pop(i)
                    merged_flag = True
                    break
            
            if merged_flag:
                # Put the merged rectangle back to the list for further merging
                rectangles.append(current)
            else:
                # No intersection, add to the result
                merged.append(current)

        return merged

    def process(self, frame):
        
        # We take a clone as we want to safe the origonal to buffer and not the one we have drawn on
        clone = self.frame1.copy()
        output = self.frame1
        self.debug = None

        self.frameCount += 1
        self.frame2 = frame

        # First do a diff of the two frames, this will tell us areas
        # which have changed and thus where motion has happened
        diff = cv2.absdiff(self.frame1, self.frame2)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)

        # Now find the contours of the areas. These are the bounding boxes around the motion
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        motion = False
        rectanglesToMerge = []

        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Ignore small areas of motion
            if area < self.minMotionArea:
                continue

            motion = True

            # If this is the first frame of motion we have seen then save the time so we can tag it
            if self.timestampOfFirstMotionFrame is None:
                self.timestampOfFirstMotionFrame = datetime.now()
                logger.info("Motion detected")

            (x, y, w, h) = cv2.boundingRect(contour)
            rectanglesToMerge.append((x, y, x + w, y + h))

        # Draw a box round them
        for rect in self.merge_intersecting_rectangles(rectanglesToMerge):
            (x, y, x2, y2) = rect
            cv2.rectangle(output, (x, y), (x2, y2), (0, 255, 0), 2)

        if motion:
            self.buffer.append(clone)
            self.frameWithLastMotion = self.frameCount
        elif self.timestampOfFirstMotionFrame is not None and self.frameWithLastMotion > self.frameCount - self.fps:
            # Motion not seen BUT it was seen less than 1s ago so include
            # NB This smooths the output as it avoids lots of little frames with just 1 or 2 frames of motion in
            self.buffer.append(clone)
        elif self.timestampOfFirstMotionFrame is not None:
            # No motion detected in this frame, but we did see some in the past so save buffer
            self.motionProcessor.process(self.timestampOfFirstMotionFrame, self.frameCount, self.buffer)
            self.buffer.clear()
            self.timestampOfFirstMotionFrame = None

        # Switch the frames so when we process frame n+1 against n
        self.frame1 = self.frame2
        return (output, self.debug)
