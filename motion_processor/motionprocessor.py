import cv2

class MotionProcessor:
    def __init__(self, minMotionArea = 2000):
        self.minMotionArea = minMotionArea
        return
    
    def loadAndFindContours(self, frame1, frame2):
        self.frame1 = frame1
        self.frame2 = frame2

        diff = cv2.absdiff(self.frame1, self.frame2)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(diff_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)

        self.contours, _ = cv2.findContours( dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    def _includeContour(self, contour) -> bool:
        return cv2.contourArea(contour) > self.minMotionArea

    def isMotionDetected(self) -> bool:
        for contour in self.contours:
            # Motion only found if the contour is larger than the min size
            if self._includeContour(contour):
                return True
            
        return False
    
    def getOutputFrame(self):
        output = self.frame1.copy()
        for contour in self.contours:

            if self._includeContour(contour):
                (x, y, w, h) = cv2.boundingRect(contour)

                cv2.rectangle(output, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(output, "STATUS: {}".format('MOTION DETECTED'), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                    1, (217, 10, 10), 2)
            
        return output