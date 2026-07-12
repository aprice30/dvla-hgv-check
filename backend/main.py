import logging
import json
import uuid
import uuid6
from typing import List, Tuple
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel, Field

import config
from dvla_client import DvlaClient
from repository import EventRepository
from image_storage import ImageStorage

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend")

app = FastAPI(title="DVLA HGV Check - Backend")

# Initialize central services
dvla_client = DvlaClient()
event_repo = EventRepository()
image_storage = ImageStorage()

class Detection(BaseModel):
    plate: str = Field(..., alias="text")
    ocr_confidence: float
    plate_confidence: float
    box: List[int]
    frame_index: int

    class Config:
        populate_by_name = True

class EventMetadata(BaseModel):
    timestamp: datetime
    plates: List[Detection]

def run_dvla_check_task(event_id: str, plate: str):
    """
    Background worker task to query the DVLA API for a given plate,
    log the results, and update the matching database document.
    """
    logger.info(f"[Task] Starting DVLA lookup for Event={event_id} | Plate='{plate}'")
    dvla_details = dvla_client.check_plate(plate)
    
    if dvla_details:
        logger.info(f"[Task] SUCCESS - Event={event_id} | Plate='{plate}' -> DVLA Details: {dvla_details}")
        event_repo.update_dvla_results(event_id, plate, dvla_details)
    else:
        logger.warning(f"[Task] FAILED/NO MATCH - Event={event_id} | Plate='{plate}'")
        event_repo.update_dvla_failed(event_id, plate)

def process_and_save_frames_task(event_id: str, files_data: List[Tuple[str, bytes]], detections: List[dict]):
    """
    Background task wrapper that delegates image processing and snapshot compression
    to the ImageStorage service class.
    """
    image_storage.save_event_media(event_id, files_data, detections)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/event")
async def receive_event(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint to receive events from the detection camera node.
    Saves event metadata to Firestore, copies image frames to storage,
    compiles a summary GIF, and runs background DVLA lookups.
    """
    try:
        form = await request.form()
    except Exception as e:
        logger.error(f"Failed to parse form data: {e}")
        raise HTTPException(status_code=400, detail="Invalid multipart form data")

    metadata_str = form.get("metadata")
    if not metadata_str:
        raise HTTPException(status_code=400, detail="Missing 'metadata' field in form data")

    try:
        metadata_json = json.loads(metadata_str)
        metadata = EventMetadata(**metadata_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode metadata JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON in 'metadata'")
    except Exception as e:
        logger.error(f"Metadata validation failed: {e}")
        raise HTTPException(status_code=422, detail=f"Metadata validation error: {str(e)}")

    # Generate a unique event ID (UUIDv7 - time sortable)
    event_id = str(uuid6.uuid7())

    # Retrieve all files from the multipart form
    uploaded_files = {}
    for key, value in form.items():
        if hasattr(value, "file") and hasattr(value, "filename"):
            uploaded_files[key] = value

    # Log the incoming event details
    logger.info("=" * 60)
    logger.info(f"Received motion event. Generated ID: {event_id}")
    logger.info(f"Timestamp: {metadata.timestamp}")
    logger.info(f"Associated image frames: {len(uploaded_files)} files")
    logger.info(f"Unique plates detected ({len(metadata.plates)} total):")
    for idx, detection in enumerate(metadata.plates):
        logger.info(
            f"  [{idx + 1}] Plate: '{detection.plate}' | "
            f"OCR Conf: {detection.ocr_confidence:.2%} | "
            f"Plate Conf: {detection.plate_confidence:.2%} | "
            f"Frame Index: {detection.frame_index}"
        )
    logger.info("=" * 60)

    # Read frame file bytes in request thread before stream closes
    files_data = []
    for filename, upload_file in uploaded_files.items():
        try:
            content = await upload_file.read()
            files_data.append((filename, content))
        except Exception as read_err:
            logger.error(f"Failed to read file {filename} bytes: {read_err}")

    # Save event metadata to database repository
    plates_data = [
        {
            "plate": d.plate,
            "ocr_confidence": d.ocr_confidence,
            "plate_confidence": d.plate_confidence,
            "box": d.box,
            "frame_index": d.frame_index
        } for d in metadata.plates
    ]
    event_repo.save_event(
        event_id=event_id,
        timestamp=metadata.timestamp,
        plates=plates_data,
        received_frames_count=len(uploaded_files)
    )

    # Queue the DVLA lookup tasks for each unique plate in the background
    for detection in metadata.plates:
        background_tasks.add_task(run_dvla_check_task, event_id, detection.plate)

    # Queue the frame saving task in the background
    if files_data:
        background_tasks.add_task(process_and_save_frames_task, event_id, files_data, plates_data)

    # Return acknowledgement immediately
    return {
        "status": "accepted",
        "event_id": event_id,
        "processed_plates": len(metadata.plates),
        "received_frames": len(uploaded_files)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
