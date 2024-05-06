import cv2
import imutils
import numpy as np
import logging

gunicorn_logger = logging.getLogger('gunicorn.error')
logger = logging.getLogger(__name__)
logger.setLevel(gunicorn_logger.level)
logger.handlers = gunicorn_logger.handlers

class PlateProcessor:
    def __init__(self, minMotionArea = 2000):
        self.minMotionArea = minMotionArea
        self.minAR = 4
        self.maxAR = 5

        self.frameWidth = 1250
        return
    
    def loadFirstFrame(self, frame1):
        self.frame1 = imutils.resize(frame1, width=self.frameWidth)

    def process(self, frame):
        output = self.frame1
        self.debug = None
        
        # Apply the same op to frame2 so its the same size as frame1
        self.frame2 = imutils.resize(frame, width=self.frameWidth)

        # First do a diff of the two frames, this will tell us areas
        # which have changed and thus where motion has happened
        diff = cv2.absdiff(self.frame1, self.frame2)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)

        # Now find the contours of the areas. These are the bounding boxes around the motion
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        largestContourArea = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Only look at contours larger than the min & only process if bigger than
            # what we have seen before (a car/lorry will be the largest area of motion)
            # TODO: Don't do largest only, if 2 cars are in frame it will ignore the smaller
            if area < max(self.minMotionArea, largestContourArea):
                continue;
            largestContourArea = area
        
            # Draw a box around the motion
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(output, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Only look at the area triggering motion
            roi = output[y:y+h, x:x+w]
            self.debug = roi     

        # Switch the frames so when we process frame n+1 against n
        self.frame1 = self.frame2
        return (output, self.debug)