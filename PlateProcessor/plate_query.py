import logging
from collections import namedtuple
from PlateProcessor.storage import Storage

OrientationCount = namedtuple('OrientationCount', ['Up', 'Down'])

class PlateQuery:
    def __init__(self):
        self.db = Storage()
        return
    
    # Return the current daily plate count in both directions
    def get_daily_plate_count(self) -> OrientationCount:
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Orientation, COUNT(*)
            FROM VehicleResult
            JOIN Capture ON Capture.CaptureId = VehicleResult.CaptureId
            GROUP BY VehicleResult.Orientation
            HAVING DATE(Capture.Timestamp) = DATE('now', 'localtime')
        ''')

        up = 0
        down = 0
        for row in cursor.fetchall():
            orientation = row[0]  # First column: Orientation
            count = row[1]  # Second column: Count

            if orientation == "Rear":
                down += count
            else:
                up += count

        conn.commit()
        conn.close()

        return OrientationCount(Up=up, Down=down)
    
    def get_latest_plates(self, count: int):
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT TIME(Capture.Timestamp), Plate.Plate, Plate.TypeApproval, Plate.VehicleMake, Plate.RevenueWeight from VehicleResult
            JOIN Capture ON Capture.CaptureId = VehicleResult.CaptureId
            JOIN Plate ON Plate.Plate = VehicleResult.DvlaPlate
            ORDER BY Capture.Timestamp DESC
            LIMIT ?
            ''', (count,))
        rows = cursor.fetchall()

        conn.commit()
        conn.close()
        return rows