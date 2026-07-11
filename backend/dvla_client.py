import os
import time
import logging
import requests
from threading import Lock
from functools import wraps
from datetime import datetime, timezone, timedelta
from typing import Optional
from google.cloud import firestore

import config

logger = logging.getLogger("backend.dvla_client")

# DVLA API configuration from config
DVLA_API_KEY = config.DVLA_API_KEY
DVLA_API_URL = config.DVLA_API_URL

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
        self.api_key = api_key or DVLA_API_KEY
        self.url = url or DVLA_API_URL
        
        # Initialize Firestore Client for Caching
        self.db = None
        if os.path.exists(config.FIRESTORE_CREDS_PATH):
            try:
                self.db = firestore.Client.from_service_account_json(config.FIRESTORE_CREDS_PATH)
                logger.info("Firestore client initialized for DVLA caching.")
            except Exception as e:
                logger.error(f"Failed to initialize Firestore client for DVLA caching: {e}")
        else:
            logger.warning(
                f"Firestore credentials file not found at '{config.FIRESTORE_CREDS_PATH}'. "
                "DVLA cache lookups and saves will be skipped."
            )
            
        logger.info(f"Starting DVLA Client with Key={'***' + self.api_key[-4:] if len(self.api_key) > 4 else self.api_key}")

    def _get_cached_plate(self, plate: str) -> Optional[dict]:
        """
        Retrieves the cached DVLA details for a plate if it exists and is still valid.
        Returns None if not found, expired, or if DB is unavailable.
        """
        if not self.db:
            return None

        try:
            doc = self.db.collection("dvla_cache").document(plate).get()
            if doc.exists:
                cache_entry = doc.to_dict()
                expire_at = cache_entry.get("expire_at")
                if expire_at and expire_at > datetime.now(timezone.utc):
                    logger.info(f"[Cache HIT] Reusing cached DVLA details for plate '{plate}'")
                    return cache_entry.get("data")
                else:
                    logger.info(f"[Cache EXPIRED] Stale cache found for plate '{plate}'.")
        except Exception as e:
            logger.error(f"[Cache Error] Failed to read cache for plate '{plate}': {e}")
            
        return None

    def _save_to_cache(self, plate: str, data: dict):
        """
        Saves the DVLA details for a plate to the Firestore cache collection,
        setting it to expire in 72 hours.
        """
        if not self.db:
            return

        try:
            expire_at = datetime.now(timezone.utc) + timedelta(hours=72)
            self.db.collection("dvla_cache").document(plate).set({
                "data": data,
                "expire_at": expire_at
            })
            logger.info(f"[Cache SAVE] Saved details for plate '{plate}' to cache (expires: {expire_at})")
        except Exception as e:
            logger.error(f"[Cache Error] Failed to write cache for plate '{plate}': {e}")

    @rate_limiter(calls_per_second=1)
    def check_plate(self, plate: str) -> Optional[dict]:
        # 1. Try to read from cache first
        cached_data = self._get_cached_plate(plate)
        if cached_data is not None:
            return cached_data

        # 2. Cache Miss - perform live API query
        logger.info(f"Querying DVLA API for plate: '{plate}'")
        if not self.api_key or self.api_key == "MISSING":
            logger.warning("DVLA API key is missing or not configured. Skipping API check.")
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
                logger.info(f"Plate '{plate}' found details: {data}")
                
                # 3. Save the result to Firestore cache
                self._save_to_cache(plate, data)
                
                return data
            else:
                logger.warning(f"Plate '{plate}' not found in DVLA. Code={response.status_code} Message={response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception while querying DVLA API for plate '{plate}': {e}")
            return None
