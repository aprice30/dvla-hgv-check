import sqlite3
import logging, os

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self):
        self.db_path = '/home/myuser/data/db/dvla.db'
        return

    def init_db(self):
        if not os.path.exists(self.db_path):
            logger.warning(f"DB is not setup in {self.db_path}: Building!")

            conn = self._get_connection()
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
                    PlateId INTEGER,
                    FOREIGN KEY (CaptureId) REFERENCES Capture(CaptureId),
                    FOREIGN KEY (PlateId) REFERENCES Plate(PlateId)
                );
            ''')
            cursor.execute('''
                CREATE TABLE Plate (
                    PlateId INTEGER PRIMARY KEY,
                    Plate TEXT NOT NULL,
                    VehicleMake TEXT,
                    VehicleColour TEXT,
                    RevenueWeight INTEGER,
                    WheelPlan TEXT,
                    RefreshTimestamp TIMESTAMP
                );
            ''')
            conn.commit()
            conn.close()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn