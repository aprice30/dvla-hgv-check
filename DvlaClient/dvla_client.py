import requests
import logging
from typing import Tuple
from DvlaClient.rate_limiter import rate_limiter
from DvlaClient.vehicle import Vehicle

logger = logging.getLogger(__name__)

# A client which can send POST requests to the DVLA API to check the details of a license plate
# returns either a JSON array with the details or None if not found
class DvlaClient:
    def __init__(self, api_key: str):
        self.url = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"
        self.api_key = api_key
        logger.info(f"Starting DVLA Client with Key={self.api_key}")

    # This API only allows us to query it once a second so limit requests to ensure we don't overload it
    @rate_limiter(calls_per_second=1)
    def check_plate(self, plate) -> Vehicle:
        logger.info(f"Checking Plater={plate}")
        # Define the JSON object
        payload = {
            "registrationNumber": plate
        }

        # Define the headers
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Make the POST request
        response = requests.post(self.url, json=payload, headers=headers)

        # Handle the response
        if response.status_code == 200:
            json = response.json()
            logger.info(f"Plate={plate} found Data={json}")
            vehicle = Vehicle(**json)
            return vehicle
        else:
            logger.warning(f"Plate={plate} not found Code={response.status_code} Message={response.text}")
            return None