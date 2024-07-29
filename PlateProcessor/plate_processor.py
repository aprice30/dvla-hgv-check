import logging
import os, json
from DvlaClient.dvla_client import DvlaClient
from Model import model
from PlateProcessor.storage import Storage

logger = logging.getLogger(__name__)

class PlateProcessor:
    def __init__(self):
        # Create a DVLA client so we can query plates
        api_key = os.getenv('DVLA_API_KEY', 'MISSING')
        self.dvla_client = DvlaClient(api_key)

        # Setup our DB
        self.db = Storage()
    
    def process(self, json_str: str):

        json_data = json.loads(json_str)
        root = model.Root(**json_data)

        # Store an event for this capture event as a whole first
        capture_id = self.db.insert_capture(root.data.filename, root.data.timestamp, json_str)

        # Each capture could contain multiple hits for vehicles and each one may have multiple possible plates
        # lets handle each in turn
        for result in root.data.results:
            result: model.Result
            self._process_result(result, capture_id)
    
    def _process_result(self, result: model.Result, capture_id: int):
        # We need to determine which plate is correct. To do this we will take each
        # candidate in turn. We will do a DVLA check for it.
        dvla_vehicle = None
        for candidate in result.candidates:
            candidate: model.Candidate
            candidate.plate = "LS18YHP"
            logging.info(f"Running DVLA check against Plate={candidate.plate}")
            dvla_vehicle = self.dvla_client.check_plate(candidate.plate)

            if dvla_vehicle is not None:
                # We had a positive hit on this plate, we will use this
                break
        
        dvla_plate = None
        if dvla_vehicle is not None:
            # We found a hit from the DVLA for this plate
            self.db.update_dvla_plate(dvla_vehicle)
            dvla_plate = dvla_vehicle.registrationNumber
        
        # Save our result record
        self.db.save_vehicle_result(capture_id, result, dvla_plate)