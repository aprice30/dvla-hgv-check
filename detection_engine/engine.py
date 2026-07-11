import os
import time
import cv2
import numpy as np

# Set environment variables immediately before imports to avoid OpenMP conflicts
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["ULTRALYTICS_TELEMETRY"] = "false"
os.environ["YOLO_VERBOSE"] = "False"

from ultralytics import YOLO
from huggingface_hub import hf_hub_download
import detection_engine.config as config

class DetectionEngine:
    def __init__(self):
        print("[Engine] Initializing Detection Engine...")
        
        # 1. Load YOLOv8 License Plate Detector
        print("[Engine] Loading YOLO detector weights...")
        self.model_path = hf_hub_download(
            repo_id=config.YOLO_REPO, 
            filename=config.YOLO_FILENAME,
            cache_dir=str(config.MODELS_DIR)
        )
        self.detector = YOLO(self.model_path)
        
        # 2. Defer PaddleOCR initialization until first run to avoid thread pool conflicts
        self.ocr = None
        print("[Engine] Detection Engine initialized and ready.")

    def _init_ocr(self):
        """Lazy load PaddleOCR to ensure it runs correctly alongside PyTorch."""
        if self.ocr is None:
            print("[Engine] Initializing PaddleOCR backend...")
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_textline_orientation=config.OCR_USE_TEXTLINE_ORIENTATION,
                lang=config.OCR_LANG
            )
            print("[Engine] PaddleOCR loaded successfully.")

    def process_image(self, image_input):
        """
        Processes an image path or pre-loaded ndarray.
        Returns:
            list of dicts containing:
                - box: [x1, y1, x2, y2]
                - plate_confidence: float
                - text: str (verified plate)
                - ocr_confidence: float
                - crop_path: str
        """
        # Handle file paths vs pre-loaded images
        if isinstance(image_input, (str, os.PathLike)):
            img = cv2.imread(str(image_input))
            if img is None:
                raise FileNotFoundError(f"Could not load image at path: {image_input}")
            filename = os.path.basename(image_input)
        else:
            img = image_input
            filename = f"capture_{int(time.time())}.jpg"

        h, w, _ = img.shape
        start_time = time.time()
        
        # Step 1: Detect plates using YOLO
        # Running on CPU to ensure M1/M2 Mac compatibility out of the box
        results = self.detector(img, device="cpu")[0]
        
        detections = []
        if len(results.boxes) == 0:
            return detections

        # Initialize OCR now that YOLO has finished its forward pass
        self._init_ocr()

        for idx, box in enumerate(results.boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            plate_conf = float(box.conf[0])

            # Filter low confidence plate detections
            if plate_conf < config.MIN_PLATE_CONFIDENCE:
                continue

            # Add a small padding margin around the plate before cropping for cleaner OCR
            margin = 5
            x1_m = max(0, x1 - margin)
            y1_m = max(0, y1 - margin)
            x2_m = min(w, x2 + margin)
            y2_m = min(h, y2 + margin)
            
            plate_crop = img[y1_m:y2_m, x1_m:x2_m]
            
            # Save crop to output folder for record/viewing
            crop_name = f"crop_{idx+1}_{filename}"
            crop_path = config.OUTPUT_DIR / crop_name
            cv2.imwrite(str(crop_path), plate_crop)

            # Step 2: Run OCR on the crop
            ocr_result = self.ocr.ocr(plate_crop)
            
            detected_text = ""
            highest_ocr_conf = 0.0

            if ocr_result and ocr_result[0]:
                res_dict = ocr_result[0]
                if isinstance(res_dict, dict) and 'rec_texts' in res_dict:
                    # PaddleX output format
                    texts = res_dict.get('rec_texts', [])
                    scores = res_dict.get('rec_scores', [])
                    for text, score in zip(texts, scores):
                        if score > highest_ocr_conf:
                            detected_text = str(text).replace(" ", "").upper()
                            highest_ocr_conf = float(score)
                else:
                    # Traditional PaddleOCR nested list output format
                    for line in ocr_result[0]:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            val = line[1]
                            if isinstance(val, (list, tuple)) and len(val) >= 2:
                                text, score = val[0], val[1]
                            else:
                                text, score = val, 1.0
                            if score > highest_ocr_conf:
                                detected_text = str(text).replace(" ", "").upper()
                                highest_ocr_conf = float(score)

            # Filter low confidence text matches
            if highest_ocr_conf < config.MIN_OCR_CONFIDENCE:
                continue

            detections.append({
                "box": [x1, y1, x2, y2],
                "plate_confidence": plate_conf,
                "text": detected_text,
                "ocr_confidence": highest_ocr_conf,
                "crop_path": str(crop_path)
            })

        print(f"[Engine] Processed {filename} in {time.time() - start_time:.3f}s. Found {len(detections)} plates.")
        return detections
