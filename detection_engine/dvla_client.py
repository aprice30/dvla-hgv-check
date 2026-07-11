import time
import logging
import requests
from threading import Lock
from functools import wraps
import detection_engine.config as config

logger = logging.getLogger(__name__)

def rate_limiter(calls_per_second):
    lock = Lock()
    min_interval = 1.0 / calls_per_second

    def decorator(func):
        last_call = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                elapsed = time.time() - last_call[0]
                wait_time = max(0, min_interval - elapsed)
                if wait_time > 0:
                    time.sleep(wait_time)
                result = func(*args, **kwargs)
                last_call[0] = time.time()
                return result

        return wrapper

    return decorator

class DvlaClient:
    def __init__(self, api_key: str = None, url: str = None):
        self.api_key = api_key or config.DVLA_API_KEY
        self.url = url or config.DVLA_API_URL
        logger.info(f"Starting DVLA Client with Key={self.api_key}")

    @rate_limiter(calls_per_second=1)
    def check_plate(self, plate: str) -> dict:
        logger.info(f"[DVLA] Checking Plate={plate}")
        if not self.api_key or self.api_key == "MISSING":
            logger.warning("[DVLA] API key is missing or not configured. Skipping check.")
            return None

        payload = {
            "registrationNumber": plate
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[DVLA] Plate={plate} found Data={data}")
                return data
            else:
                logger.warning(f"[DVLA] Plate={plate} not found Code={response.status_code} Message={response.text}")
                return None
        except Exception as e:
            logger.error(f"[DVLA] Exception while querying DVLA API for {plate}: {e}")
            return None
