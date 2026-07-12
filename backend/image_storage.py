import os
import io
import re
import logging
from typing import List, Tuple, Dict, Any
from PIL import Image

import config

logger = logging.getLogger("backend.image_storage")

class ImageStorage:
    def __init__(self, detections_dir: str = None):
        self.detections_dir = detections_dir or config.DETECTIONS_DIR

    def _get_frame_number(self, filename: str) -> int:
        """
        Helper to extract the numerical index from a frame filename (e.g., "frame_27" -> 27)
        """
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else 0

    def save_event_media(self, event_id: str, files_data: List[Tuple[str, bytes]], detections: List[Dict[str, Any]]):
        """
        Saves and compresses the key frame JPEG snapshot(s) where plates were detected.
        Stores them under: detections/detection_<event_id>/
        Each file is named after its database record ID: <event_id>_<plate>.jpg (which is the detection_id).
        """
        try:
            # Create subfolder detection_<event_id>
            folder_path = os.path.join(self.detections_dir, f"detection_{event_id}")
            os.makedirs(folder_path, exist_ok=True)
            
            # Create a lookup mapping from frame_index to detection metadata
            frame_to_detection = {d["frame_index"]: d for d in detections}
            
            for filename, content in files_data:
                frame_num = self._get_frame_number(filename)
                
                # Map the frame to its corresponding detection record ID
                detection_info = frame_to_detection.get(frame_num)
                if detection_info:
                    plate = detection_info["plate"]
                    # Matches the detection_id schema: {event_id}_{plate}
                    file_name = f"{event_id}_{plate}.jpg"
                else:
                    # Fallback naming if mismatch occurs
                    file_name = f"unknown_{event_id}_frame_{frame_num}.jpg"
                
                file_path = os.path.join(folder_path, file_name)
                
                # Compress and resize using Pillow
                try:
                    img = Image.open(io.BytesIO(content))
                    
                    # Shrink image down to a maximum width of 1280px, maintaining aspect ratio
                    max_width = 1280
                    if img.width > max_width:
                        w_percent = (max_width / float(img.width))
                        h_size = int((float(img.height) * float(w_percent)))
                        img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                        logger.info(f"Resized frame '{filename}' from {img.width}px width to 1280px")
                    
                    # Save image as JPEG with 80% quality
                    img.save(file_path, "JPEG", quality=80)
                    logger.info(f"Saved compressed snapshot: {file_path}")
                except Exception as img_err:
                    logger.error(f"Failed to process image frame {filename}: {img_err}")

        except Exception as e:
            logger.error(f"Failed to save event media files for Event={event_id}: {e}")
