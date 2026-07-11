import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from google.cloud import firestore
import config

logger = logging.getLogger("backend.repository")

class EventRepository:
    def __init__(self):
        self.db = None
        if os.path.exists(config.FIRESTORE_CREDS_PATH):
            try:
                self.db = firestore.Client.from_service_account_json(config.FIRESTORE_CREDS_PATH)
                logger.info("Firestore client successfully initialized in Repository.")
            except Exception as e:
                logger.error(f"Failed to initialize Firestore client in Repository: {e}")
        else:
            logger.warning(
                f"Firestore credentials file not found at '{config.FIRESTORE_CREDS_PATH}'. "
                "Database operations will be skipped."
            )

    def save_event(self, event_id: str, timestamp: datetime, plates: List[Dict[str, Any]], received_frames_count: int) -> bool:
        """
        Saves the initial event metadata to the 'events' collection
        and creates initial pending entries in the 'detections' collection.
        """
        if not self.db:
            logger.warning(f"Firestore not available. Skipping save for Event={event_id}")
            return False

        try:
            # 1. Save main Event document
            event_data = {
                "event_id": event_id,
                "timestamp": timestamp,
                "received_frames_count": received_frames_count,
                "created_at": datetime.now(timezone.utc)
            }
            self.db.collection("events").document(event_id).set(event_data)
            logger.info(f"Saved event: {event_id}")

            # 2. Save individual Detection documents
            for d in plates:
                plate = d["plate"]
                detection_id = f"{event_id}_{plate}"
                detection_data = {
                    "detection_id": detection_id,
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "plate": plate,
                    "ocr_confidence": d["ocr_confidence"],
                    "plate_confidence": d["plate_confidence"],
                    "box": d["box"],
                    "frame_index": d["frame_index"],
                    
                    # Pre-allocated DVLA columns (pending resolution)
                    "make": None,
                    "weight_kg": None,
                    "vehicle_class": None,
                    "dvla_status": "pending",
                    "created_at": datetime.now(timezone.utc)
                }
                self.db.collection("detections").document(detection_id).set(detection_data)
                logger.info(f"Saved pending detection: {detection_id}")

            return True
        except Exception as e:
            logger.error(f"Failed to write event/detections to Firestore: {e}")
            return False

    def update_dvla_results(self, event_id: str, plate: str, dvla_details: Dict[str, Any]) -> bool:
        """
        Calculates vehicle HGV stats and updates the specific detection record.
        """
        if not self.db:
            return False

        detection_id = f"{event_id}_{plate}"
        try:
            # Classification rules (Specifically highlighting target HGVs >= 7.5t):
            # - < 3500 kg: Car / Light Vehicle (<3.5t)
            # - 3500 kg to 7499 kg: Medium Goods Vehicle (3.5t - 7.5t)
            # - >= 7500 kg: Heavy Goods Vehicle (>=7.5t)
            weight_kg = dvla_details.get("revenueWeight")
            if not weight_kg:
                vehicle_class = "Unknown"
            elif weight_kg < 3500:
                vehicle_class = "Car / Light Vehicle (<3.5t)"
            elif weight_kg < 7500:
                vehicle_class = "Medium Goods Vehicle (3.5t - 7.5t)"
            else:
                vehicle_class = "Heavy Goods Vehicle (>=7.5t)"

            update_data = {
                "make": dvla_details.get("make"),
                "weight_kg": weight_kg,
                "vehicle_class": vehicle_class,
                "dvla_status": "completed",
                "dvla_details": dvla_details,
                "updated_at": datetime.now(timezone.utc)
            }

            self.db.collection("detections").document(detection_id).update(update_data)
            logger.info(f"Updated detection {detection_id} with DVLA details (Class: {vehicle_class})")
            return True
        except Exception as e:
            logger.error(f"Failed to update detection {detection_id} in Firestore: {e}")
            return False

    def update_dvla_failed(self, event_id: str, plate: str) -> bool:
        """
        Sets the DVLA lookup status to failed for the specific detection.
        """
        if not self.db:
            return False

        detection_id = f"{event_id}_{plate}"
        try:
            self.db.collection("detections").document(detection_id).update({
                "dvla_status": "failed_or_no_match",
                "updated_at": datetime.now(timezone.utc)
            })
            logger.info(f"Updated detection {detection_id} status to failed")
            return True
        except Exception as e:
            logger.error(f"Failed to update detection {detection_id} status to failed: {e}")
            return False
