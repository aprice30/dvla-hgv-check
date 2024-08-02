import logging
import database

logger = logging.getLogger(__name__)

def get_plate_results(plate: str):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Capture.Timestamp, Capture.Filename, VehicleResult.DwellTime, VehicleResult.Orientation
        FROM VehicleResult
        JOIN Plate ON Plate.Plate = VehicleResult.DvlaPlate
        JOIN Capture ON Capture.CaptureId = VehicleResult.CaptureId
        WHERE Plate.Plate = ?
        ORDER BY Capture.Timestamp DESC
        ''', (plate,))
    rows = cursor.fetchall()

    conn.commit()
    conn.close()
    return rows