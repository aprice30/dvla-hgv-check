import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# DVLA API Settings
DVLA_API_KEY = os.getenv("DVLA_API_KEY", "MISSING")
DVLA_API_URL = os.getenv("DVLA_API_URL", "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles")

# Firestore Settings
FIRESTORE_CREDS_PATH = os.getenv("FIRESTORE_CREDS_PATH", str(BASE_DIR / "firestore.json"))

# Storage Settings
DETECTIONS_DIR = os.getenv("DETECTIONS_DIR", str(BASE_DIR / "detections"))
