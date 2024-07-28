import logging
import os
from DvlaClient.dvla_client import DvlaClient

logger = logging.getLogger(__name__)

class PlateProcessor:
    def __init__(self):
        # Create a DVLA client so we can query plates
        api_key = os.getenv('DVLA_API_KEY', 'MISSING')
        self.dvla_client = DvlaClient(api_key)
    
    def process(self, json):
        # Send our plate data for further processing
        for result in json['results']:
            for candidate in result['candidates']:
                logging.info(f"Running DVLA check against Plate={candidate['plate']}")
                self.dvla_client.check_plate(candidate['plate'])