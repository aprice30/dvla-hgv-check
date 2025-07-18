import logging, os, json
from DvlaClient.vehicle import Vehicle
from Model import model
import database

logger = logging.getLogger(__name__)

def first_or_none(lst):
    return lst[0] if lst else None

class Storage:
    def __init__(self):
        return

    def init_db(self):
        if not os.path.exists(database.db_path):
            logger.warning(f"DB is not setup in {database.db_path}: Building!")

            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE Capture (
                    CaptureId INTEGER PRIMARY KEY,
                    Filename TEXT NOT NULL,
                    Timestamp TIMESTAMP NOT NULL,
                    RawJson TEXT NOT NULL
                );
            ''')
            cursor.execute(''' 
                CREATE TABLE VehicleResult (
                    CaptureId INTEGER,
                    PlateBox TEXT,  -- JSON stored as text
                    VehicleBox TEXT,  -- JSON stored as text
                    Orientation TEXT,
                    DwellTime REAL,
                    Region TEXT,
                    RawPlate TEXT,
                    DvlaPlate TEXT,
                    FOREIGN KEY (CaptureId) REFERENCES Capture(CaptureId),
                    FOREIGN KEY (DvlaPlate) REFERENCES Plate(Plate)
                );
            ''')
            cursor.execute('''
                CREATE TABLE Plate (
                    Plate TEXT PRIMARY KEY NOT NULL,
                    VehicleMake TEXT,
                    VehicleColour TEXT,
                    RevenueWeight INTEGER,
                    WheelPlan TEXT,
                    TypeApproval TEXT
                );
            ''')
            conn.commit()
            conn.close()
    
    def insert_capture(self, filename: str, timestamp: str, json: str) -> int:
        logger.debug(f"Storing capture event for {filename} @ {timestamp}")

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Capture (Filename, Timestamp, RawJson)
            VALUES (?, ?, ?)
        ''', (filename, timestamp, json))

        new_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return new_id
    
    def update_dvla_plate(self, vehicle: Vehicle):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO Plate (
                Plate, 
                VehicleMake, 
                VehicleColour, 
                RevenueWeight, 
                WheelPlan,
                TypeApproval
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (vehicle.registrationNumber, vehicle.make, vehicle.colour, vehicle.revenueWeight, vehicle.wheelplan, vehicle.typeApproval))

        conn.commit()
        conn.close()
    
    def save_vehicle_result(self, capture_id: int, result: model.Result, dvla_plate: str):
        logger.debug(f"Storing capture event for {result} with DvlaPlate={dvla_plate}")

        # Pick the highest scored orientation
        orientation = first_or_none(result.orientation)
        if orientation is not None:
            orientation = orientation.orientation

        plat_box_str = json.dumps(result.box.dict())
        vehicle_box_str = json.dumps(result.vehicle.box.dict())

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO VehicleResult (
                CaptureId,
                PlateBox,
                VehicleBox,
                Orientation,
                DwellTime,
                Region,
                RawPlate,
                DvlaPlate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (capture_id, plat_box_str, vehicle_box_str, orientation, result.position_sec, result.region.code, result.plate, dvla_plate))

        conn.commit()
        conn.close()