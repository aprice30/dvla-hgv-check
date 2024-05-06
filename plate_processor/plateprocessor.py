import cv2
import imutils
from skimage.segmentation import clear_border
import numpy as np

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
            # roi = output[y:y+h, x:x+w]
            # roi_grey = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # cnts = self._find_numberplates(roi_grey)
            # roi, lpCnt = self._locate_license_plate(roi_grey, cnts)

            # if lpCnt is not None:
            #     # Found a numberplace us it
            #     (cx, cy, cw, ch) = cv2.boundingRect(lpCnt)

            #     output = roi[cy:cy+ch, cx:cx+cw]

        # Switch the frames so when we process frame n+1 against n
        self.frame1 = self.frame2
        return output
    
    def _find_numberplates(self, grey):
        # perform a blackhat morphological operation that will allow
        # us to reveal dark regions (i.e., text) on light backgrounds
        # (i.e., the license plate itself)
        rectKern = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(grey, cv2.MORPH_BLACKHAT, rectKern)
        
        # next, find regions in the image that are light
        squareKern = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        light = cv2.morphologyEx(grey, cv2.MORPH_CLOSE, squareKern)
        light = cv2.threshold(light, 0, 255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # compute the Scharr gradient representation of the blackhat
        # image in the x-direction and then scale the result back to
        # the range [0, 255]
        gradX = cv2.Sobel(blackhat, ddepth=cv2.CV_32F,
            dx=1, dy=0, ksize=-1)
        gradX = np.absolute(gradX)
        (minVal, maxVal) = (np.min(gradX), np.max(gradX))
        gradX = 255 * ((gradX - minVal) / (maxVal - minVal))
        gradX = gradX.astype("uint8")

        # blur the gradient representation, applying a closing
        # operation, and threshold the image using Otsu's method
        gradX = cv2.GaussianBlur(gradX, (5, 5), 0)
        gradX = cv2.morphologyEx(gradX, cv2.MORPH_CLOSE, rectKern)
        thresh = cv2.threshold(gradX, 0, 255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # perform a series of erosions and dilations to clean up the
        # thresholded image
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=2)

        # take the bitwise AND between the threshold result and the
        # light regions of the image
        thresh = cv2.bitwise_and(thresh, thresh, mask=light)
        thresh = cv2.dilate(thresh, None, iterations=2)
        thresh = cv2.erode(thresh, None, iterations=1)

        # find contours in the thresholded image and sort them by
        # their size in descending order, keeping only the largest
        # ones
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

        return cnts

    def _locate_license_plate(self, gray, candidates, clearBorder=False):
		# initialize the license plate contour and ROI
        lpCnt = None
        roi = None
		# loop over the license plate candidate contours
        for c in candidates:
			# compute the bounding box of the contour and then use
			# the bounding box to derive the aspect ratio
            (x, y, w, h) = cv2.boundingRect(c)
            ar = w / float(h)

            # check to see if the aspect ratio is rectangular
            if ar >= self.minAR and ar <= self.maxAR:
				# store the license plate contour and extract the
				# license plate from the grayscale image and then
				# threshold it
                lpCnt = c
                licensePlate = gray[y:y + h, x:x + w]
                roi = cv2.threshold(licensePlate, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

                # check to see if we should clear any foreground
				# pixels touching the border of the image
				# (which typically, not but always, indicates noise)
                if clearBorder:
                    roi = clear_border(roi)
                break
		
        # return a 2-tuple of the license plate ROI and the contour
		# associated with it
        return (roi, lpCnt)