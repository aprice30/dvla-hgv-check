from pydantic import BaseModel
from typing import Optional

class Vehicle(BaseModel):
    artEndDate: Optional[str] = None
    co2Emissions: Optional[int] = None
    colour: Optional[str] = None
    engineCapacity: Optional[int] = None
    fuelType: Optional[str] = None
    make: Optional[str] = None
    markedForExport: Optional[bool] = None
    monthOfFirstRegistration: Optional[str] = None
    motStatus: Optional[str] = None
    registrationNumber: str
    revenueWeight: Optional[int] = None
    taxDueDate: Optional[str] = None
    taxStatus: Optional[str] = None
    typeApproval: Optional[str] = None
    wheelplan: Optional[str] = None
    yearOfManufacture: Optional[int] = None
    euroStatus: Optional[str] = None
    realDrivingEmissions: Optional[str] = None
    dateOfLastV5CIssued: Optional[str] = None