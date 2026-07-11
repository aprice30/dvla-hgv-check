import os
from pathlib import Path

# Base Directories
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent

# Model Settings
# We will cache models locally in the engine directory
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# YOLO Plate Detector Weights
YOLO_REPO = "Koushim/yolov8-license-plate-detection"
YOLO_FILENAME = "best.pt"

# OCR Settings
OCR_LANG = "en"
OCR_USE_TEXTLINE_ORIENTATION = True

# Processing Parameters
MIN_PLATE_CONFIDENCE = 0.40  # Minimum confidence score to accept a plate bounding box
MIN_OCR_CONFIDENCE = 0.60    # Minimum confidence score to accept OCR read text

# Storage / Outputs
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# DVLA API Settings
DVLA_API_KEY = os.getenv("DVLA_API_KEY", "MISSING")
DVLA_API_URL = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"

# Central API Settings
API_URL = os.getenv("API_URL", "http://localhost:8000/api/event")
SEND_TO_API = os.getenv("SEND_TO_API", "false").lower() == "true"
