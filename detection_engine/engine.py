import os
import re
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

    def clean_and_validate_plate(self, text):
        """
        Cleans OCR output by converting common digit/letter confusions and 
        validates the plate against the DVLA INF104 modern registration spec.
        
        Returns:
            tuple: (corrected_text or None, failure_reason_string or None)
        """
        # 1. Clean spacing and non-alphanumeric chars
        cleaned = "".join([c for c in text if c.isalnum()]).upper()

        # If the text is too short or too long for a modern UK plate (typically 7 chars)
        if len(cleaned) != 7:
            return None, f"Length is {len(cleaned)} (must be exactly 7 characters)"

        # Split into parts: Tag (2 letters), Age (2 numbers), Random Suffix (3 letters)
        tag, age, suffix = cleaned[0:2], cleaned[2:4], cleaned[4:7]

        # 2. Heuristic Corrections for common OCR confusions
        letter_replacements = {
            '1': 'L',  # 1 -> L
            '0': 'O',  # 0 -> O
            '2': 'Z',  # 2 -> Z
            '5': 'S',  # 5 -> S
            '8': 'B'   # 8 -> B
        }
        
        digit_replacements = {
            'I': '1',  # I -> 1
            'O': '0',  # O -> 0
            'Q': '0',  # Q -> 0
            'S': '5',  # S -> 5
            'Z': '2',  # Z -> 2
            'B': '8',  # B -> 8
            'G': '6'   # G -> 6
        }

        # Apply corrections to the tag & suffix (letters)
        for num, letter in letter_replacements.items():
            tag = tag.replace(num, letter)
            suffix = suffix.replace(num, letter)

        # Apply corrections to the age identifier (digits)
        for letter, num in digit_replacements.items():
            age = age.replace(letter, num)
            
        # Reassemble the corrected string
        corrected = f"{tag}{age}{suffix}"

        # 3. Apply INF104 Rules and Regex validation
        # - Tag (first 2 letters): Cannot contain I, Q, or Z
        # - Age (next 2 chars): Must be digits
        # - Suffix (last 3 letters): Cannot contain I or Q (but can contain Z)
        if re.search(r"[IQZ]", tag):
            return None, f"Local memory tag '{tag}' contains invalid characters (I, Q, or Z)"
        if not age.isdigit():
            return None, f"Age identifier '{age}' must contain only digits"
        if re.search(r"[IQ]", suffix):
            return None, f"Random suffix '{suffix}' contains invalid characters (I or Q)"
        if not suffix.isalpha():
            return None, f"Random suffix '{suffix}' must contain only letters"

        return corrected, None

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

            corrected_text, reason = self.clean_and_validate_plate(detected_text)
            if not corrected_text:
                print(f"[Engine] Plate '{detected_text}' rejected: {reason}")
                continue

            if corrected_text != detected_text:
                print(f"[Engine] Corrected plate: '{detected_text}' -> '{corrected_text}'")
            else:
                print(f"[Engine] Validated plate: '{detected_text}'")

            detections.append({
                "box": [x1, y1, x2, y2],
                "plate_confidence": plate_conf,
                "text": corrected_text,
                "ocr_confidence": highest_ocr_conf,
                "crop_path": str(crop_path)
            })

        print(f"[Engine] Processed {filename} in {time.time() - start_time:.3f}s. Found {len(detections)} plates.")
        return detections
