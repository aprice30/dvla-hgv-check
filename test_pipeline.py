import os
# Resolve OpenMP thread pool conflicts between PyTorch and PaddlePaddle
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
# Disable Ultralytics telemetry/updates to prevent network delays
os.environ["ULTRALYTICS_TELEMETRY"] = "false"
os.environ["YOLO_VERBOSE"] = "False"

import cv2
import numpy as np
from ultralytics import YOLO

def main():
    image_path = "test_plate.jpg"
    if not os.path.exists(image_path):
        image_path = "test_plate.jpeg"
        
    # 1. Check if the test image exists
    if not os.path.exists(image_path):
        print(f"Error: Neither 'test_plate.jpg' nor 'test_plate.jpeg' was found in the directory.")
        print("Please place a test image in this directory and run the script again.")
        return

    print("--- Step 1: Loading Detector Model ---")
    # Download YOLOv8 License Plate Detector weights from Hugging Face
    from huggingface_hub import hf_hub_download
    print("Downloading/loading YOLOv8 license plate detector weights...")
    model_path = hf_hub_download(repo_id="Koushim/yolov8-license-plate-detection", filename="best.pt")
    detector_model = YOLO(model_path)

    # Disable Ultralytics telemetry/updates to prevent network delays
    os.environ["ULTRALYTICS_TELEMETRY"] = "false"
    os.environ["YOLO_VERBOSE"] = "False"

    print("\n--- Step 2: Running Plate Detection ---")
    img = cv2.imread(image_path)
    h, w, _ = img.shape
    print(f"Loaded image: {image_path} ({w}x{h})")

    # Run detection (force CPU to avoid PyTorch MPS initialization hangs on macOS)
    print("Calling detector_model(img, device='cpu')...")
    import time
    start_det = time.time()
    results = detector_model(img, device="cpu")[0]
    det_time = time.time() - start_det
    print(f"detector_model call completed successfully in {det_time:.3f} seconds!")
    
    if len(results.boxes) == 0:
        print("No license plates detected in the image.")
        return

    print(f"Detected {len(results.boxes)} plate candidate(s). Processing...")

    # Process each detected plate
    for idx, box in enumerate(results.boxes):
        # Bounding box coordinates
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        print(f"\nCandidate {idx+1}: Box [{x1}, {y1}, {x2}, {y2}] with Confidence {conf:.2%}")

        # Crop the plate with a small margin to make OCR easier
        margin = 5
        x1_m = max(0, x1 - margin)
        y1_m = max(0, y1 - margin)
        x2_m = min(w, x2 + margin)
        y2_m = min(h, y2 + margin)
        
        plate_crop = img[y1_m:y2_m, x1_m:x2_m]
        
        # Save crop for reference/debugging
        crop_filename = f"plate_crop_{idx+1}.jpg"
        cv2.imwrite(crop_filename, plate_crop)
        print(f"Saved cropped plate image to '{crop_filename}'")

        # 3. OCR Stage via PaddleOCR
        print(f"Loading PaddleOCR...")
        import time
        start_ocr_init = time.time()
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        ocr_init_time = time.time() - start_ocr_init
        
        print(f"Running PaddleOCR on candidate {idx+1}...")
        start_ocr_run = time.time()
        ocr_result = ocr.ocr(plate_crop)
        ocr_run_time = time.time() - start_ocr_run
        print(f"PaddleOCR loaded in {ocr_init_time:.3f}s, and ran inference in {ocr_run_time:.3f}s")

        if not ocr_result or not ocr_result[0]:
            print("PaddleOCR could not read any text on the cropped plate.")
            continue

        # Extract text and confidence securely from PaddleOCR response
        print(f"Raw OCR Result: {ocr_result}")
        detected_text = ""
        highest_ocr_conf = 0.0
        
        try:
            res_dict = ocr_result[0]
            if isinstance(res_dict, dict) and 'rec_texts' in res_dict:
                texts = res_dict.get('rec_texts', [])
                scores = res_dict.get('rec_scores', [])
                for text, ocr_conf in zip(texts, scores):
                    print(f" - Read: '{text}' (Confidence: {ocr_conf:.2%})")
                    if ocr_conf > highest_ocr_conf:
                        detected_text = str(text).replace(" ", "").upper()
                        highest_ocr_conf = ocr_conf
            else:
                # Fallback for traditional PaddleOCR list formats
                for line in ocr_result[0]:
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        val = line[1]
                        if isinstance(val, (list, tuple)) and len(val) >= 2:
                            text, ocr_conf = val[0], val[1]
                        else:
                            text, ocr_conf = val, 1.0
                    else:
                        text, ocr_conf = str(line), 1.0
                    
                    print(f" - Read: '{text}' (Confidence: {ocr_conf:.2%})")
                    if ocr_conf > highest_ocr_conf:
                        detected_text = str(text).replace(" ", "").upper()
                        highest_ocr_conf = ocr_conf
        except Exception as e:
            print(f"Error parsing OCR results: {e}")

        # Draw box and write the text on the original image
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(
            img, 
            f"{detected_text} ({highest_ocr_conf:.2f})", 
            (x1, max(y1 - 10, 30)), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.9, 
            (0, 255, 0), 
            2
        )

    # Save output image with visual markings
    output_path = "result.jpg"
    cv2.imwrite(output_path, img)
    print(f"\nProcessed image saved to '{output_path}' with visual boxes and text.")

if __name__ == "__main__":
    main()
