import logging
import os
from DvlaClient.dvla_client import DvlaClient
from Model import model

logger = logging.getLogger(__name__)

class PlateProcessor:
    def __init__(self):
        # Create a DVLA client so we can query plates
        api_key = os.getenv('DVLA_API_KEY', 'MISSING')
        self.dvla_client = DvlaClient(api_key)
    
    def process(self, root: model.Root):
        # Each root could contain multiple hits for vehicles and each one may have multiple possible plates
        # lets handle each in turn
        for result in root.data.results:
            result: model.Result
            self._process_result(result)
    
    def _process_result(self, result: model.Result):
        for candidate in result.candidates:
            candidate: model.Candidate
            logging.info(f"Running DVLA check against Plate={candidate.plate}")
            self.dvla_client.check_plate(candidate.plate)