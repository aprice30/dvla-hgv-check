import logging
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class MotionProcessorInterface:
    def process(self, timestamp: datetime, frameCount: int, buffer: deque):
        pass