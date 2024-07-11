import logging
import ffmpegcv # type: ignore
import threading
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class MotionProcessorInterface:
    def process(self, timestamp: datetime, frameCount: int, buffer: deque):
        pass

class MotionProcessor(MotionProcessorInterface):
    def __init__(self, outputPath):
        self.outputPath = outputPath

        self.buffer = deque()
    
    def process(self, timestamp: datetime, frameCount: int, buffer: deque):
        # Create the filename
        formatted_time = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        fileName = "{}/{}_{}.mp4".format(self.outputPath, formatted_time, frameCount)
        logger.info("Saving motion to %s", fileName)

        try:

            with ffmpegcv.VideoWriter(fileName, None, 10) as out:
                for frame in buffer:
                 out.write(frame)
        except:
            logger.exception("Failed to save clip")