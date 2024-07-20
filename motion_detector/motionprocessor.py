import logging
import ffmpegcv # type: ignore
import threading
from collections import deque
from queue import Queue
from datetime import datetime

logger = logging.getLogger(__name__)

class MotionProcessorInterface:
    def process(self, timestamp: datetime, frameCount: int, buffer: deque):
        pass

class MotionProcessor(MotionProcessorInterface):
    def __init__(self, outputPath):
        self.outputPath: str = outputPath
        self.queue = Queue()

        # Start a thread to process the buffer in the background
        t = threading.Thread(target=self.processQueue, args=(), daemon=True)
        t.start()
    
    def process(self, timestamp: datetime, frameCount: int, frames: deque):
        # Create the filename
        formatted_time = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        fileName = "{}/{}_{}.mp4".format(self.outputPath, formatted_time, frameCount)
        
        payload = MotionPayload(fileName, frames.copy())
        self.queue.put(payload)

    def processQueue(self):
        payload: MotionPayload
        for payload in iter(self.queue.get, None): # Replace `None` as you need.
            logger.info("Saving motion to %s", payload.fileName)

            try:
                with ffmpegcv.VideoWriter(payload.fileName, None, 10) as out:
                    for frame in payload.frames:
                        out.write(frame)
            except:
                logger.exception("Failed to save clip")

class MotionPayload:
    def __init__(self, fileName: str, frames: deque):
        self.fileName: str = fileName
        self.frames: deque = frames