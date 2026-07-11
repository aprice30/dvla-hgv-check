import os
import sys
import time
import queue
import threading
import cv2
import logging
import requests
import json
from pathlib import Path

# Add project root to sys.path to resolve imports cleanly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from detection_engine.engine import DetectionEngine
from detection_engine.motion import MotionDetector
import detection_engine.config as config

from detection_engine.dvla_client import DvlaClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

# Thread-safe queue for sharing motion events between threads
motion_queue = queue.Queue()

def detection_worker(engine):
    """
    Consumer Thread: Pulls batches of frames from the queue and runs
    the YOLO + OCR detection engine on every frame in the batch.
    """
    logger.info("[Worker] Detection worker thread started.")
    dvla_client = DvlaClient()
    while True:
        try:
            # Block until an event is available in the queue
            payload = motion_queue.get()
            if payload is None:
                # Poison pill to stop the thread
                break

            timestamp = payload["timestamp"]
            frames = payload["frames"]
            ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
            # Smart sampling: Pick frames at 25%, 50%, and 75% marks of the motion event.
            # If the batch has 3 frames or fewer, process all of them to be safe.
            frames_to_process = []
            if len(frames) <= 3:
                frames_to_process = [(idx, f) for idx, f in enumerate(frames)]
            else:
                indices = [int(len(frames) * 0.25), int(len(frames) * 0.50), int(len(frames) * 0.75)]
                # Ensure sorted, unique indices in case of overlaps in very small ranges
                unique_indices = sorted(list(set(indices)))
                frames_to_process = [(idx, frames[idx]) for idx in unique_indices]

            logger.info(
                f"[Worker] Processing event from {ts_str}. "
                f"Total frames: {len(frames)}, Sampled: {[idx for idx, _ in frames_to_process]}"
            )

            # Run the engine on sampled frames in this batch
            all_results = []
            for i, frame in frames_to_process:
                # Run plate detection and OCR on the frame
                results = engine.process_image(frame)
                
                for res in results:
                    # Enrich results with timestamp and frame identifier
                    res["timestamp"] = timestamp
                    res["frame_index"] = i
                    all_results.append(res)

            # Log consolidated results for the motion event
            logger.info(f"[Worker] Finished event. Detected {len(all_results)} total plate hits.")
            
            # Simple consolidation/deduplication for console output
            unique_plates = {}
            for res in all_results:
                plate = res["text"]
                conf = res["ocr_confidence"]
                if plate not in unique_plates or conf > unique_plates[plate]["ocr_confidence"]:
                    unique_plates[plate] = res

            for plate, details in unique_plates.items():
                logger.info(
                    f"[Result] Matched Plate: '{plate}' | "
                    f"OCR Conf: {details['ocr_confidence']:.2%} | "
                    f"Plate Conf: {details['plate_confidence']:.2%} | "
                    f"Frame Index: {details['frame_index']}"
                )
                # Call the DVLA API and log the details
                dvla_details = dvla_client.check_plate(plate)
                if dvla_details:
                    logger.info(f"[Result] DVLA Details for '{plate}': {dvla_details}")
                else:
                    logger.warning(f"[Result] No DVLA Details returned for '{plate}'")

            # 3. Post results and frames payload to API if enabled
            if config.SEND_TO_API and unique_plates:
                logger.info(f"[Worker] Sending {len(unique_plates)} plates and {len(frames)} frames to API...")
                try:
                    # Construct metadata JSON
                    metadata_payload = {
                        "timestamp": timestamp.isoformat(),
                        "plates": [
                            {
                                "text": details["text"],
                                "ocr_confidence": details["ocr_confidence"],
                                "plate_confidence": details["plate_confidence"],
                                "box": details["box"],
                                "frame_index": details["frame_index"]
                            }
                            for details in unique_plates.values()
                        ]
                    }

                    # Encode all frames of the motion buffer to JPEG bytes
                    files = {}
                    for idx, frame in enumerate(frames):
                        success, encoded_img = cv2.imencode(".jpg", frame)
                        if success:
                            files[f"frame_{idx}"] = (f"frame_{idx}.jpg", encoded_img.tobytes(), "image/jpeg")

                    # Attach metadata as a string form field
                    data = {"metadata": json.dumps(metadata_payload)}

                    # Send POST request (timeout ensures we don't hang if server is slow/down)
                    response = requests.post(config.API_URL, data=data, files=files, timeout=15)
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"[Worker] Successfully posted event to API. Response: {response.text}")
                    else:
                        logger.error(f"[Worker] Failed to post event. Status: {response.status_code}, Response: {response.text}")
                except Exception as ex:
                    logger.error(f"[Worker] Exception occurred while posting to API: {ex}")

            motion_queue.task_done()
        except Exception as e:
            logger.exception(f"[Worker] Error processing batch: {e}")

def main():
    # 1. Initialize the Detection Engine
    engine = DetectionEngine()

    # 2. Start the detection worker thread
    worker_thread = threading.Thread(target=detection_worker, args=(engine,), daemon=True)
    worker_thread.start()

    # 3. Determine the video source (RTSP stream URL or webcam or test video file)
    # Default to a local camera device (0) or RTSP url if set in env vars
    source_url = os.getenv("CAMERA_SOURCE", "0")
    if source_url.isdigit():
        source_url = int(source_url)  # Use integer for local webcam index (e.g. 0)

    logger.info(f"Connecting to video source: {source_url}")
    cap = cv2.VideoCapture(source_url)

    if not cap.isOpened():
        logger.error(f"Error: Could not open video source {source_url}")
        sys.exit(1)

    # Read FPS from camera source or fallback to 10
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or fps > 100:
        fps = 10
    logger.info(f"Camera FPS: {fps}")

    # 4. Initialize the Motion Detector
    detector = MotionDetector(fps=int(fps), queue=motion_queue)

    # 5. Capture loop (Producer)
    logger.info("Entering main capture loop. Press Ctrl+C to exit.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame from source.")
                # If reading from a video file or stream disconnects, sleep briefly and retry
                time.sleep(0.1)
                continue

            # Process the frame with the motion detector
            # This returns an annotated frame (e.g. showing boxes) which can be displayed/saved
            _ = detector.process(frame)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")
    finally:
        cap.release()
        # Clean up the worker thread
        motion_queue.put(None)
        worker_thread.join(timeout=3)
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()
