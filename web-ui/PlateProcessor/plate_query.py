import logging
from PlateProcessor.storage import Storage
import database

class PlateQuery:
    def __init__(self):
        return
    
    def get_direction_plate_count(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN VehicleResult.Orientation = 'Forward' THEN 'Up'
                    WHEN VehicleResult.Orientation = 'Rear' THEN 'Down'
                    ELSE 'Unknown'
                END AS OrientationDirection,
                COUNT(CASE WHEN DATE(Capture.Timestamp) = DATE('now', 'localtime') THEN 1 END) AS count_today,
                COUNT(CASE WHEN strftime('%W', Capture.Timestamp) = strftime('%W', 'now', 'localtime') THEN 1 END) AS count_this_week,
                COUNT(CASE WHEN strftime('%m', Capture.Timestamp) = strftime('%m', 'now', 'localtime') THEN 1 END) AS count_this_month,
                COUNT(CASE WHEN strftime('%Y', Capture.Timestamp) = strftime('%Y', 'now', 'localtime') THEN 1 END) AS count_this_year
            FROM 
                VehicleResult
            JOIN 
                Capture ON Capture.CaptureId = VehicleResult.CaptureId
            GROUP BY 
                VehicleResult.Orientation
        ''')

        rows = cursor.fetchall()
        conn.commit()
        conn.close()
        return rows
    
    def get_latest_plates(self, count: int):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Capture.Timestamp, Plate.Plate, Plate.TypeApproval, Plate.VehicleMake, Plate.RevenueWeight from VehicleResult
            JOIN Capture ON Capture.CaptureId = VehicleResult.CaptureId
            JOIN Plate ON Plate.Plate = VehicleResult.DvlaPlate
            ORDER BY Capture.Timestamp DESC
            LIMIT ?
            ''', (count,))
        rows = cursor.fetchall()

        conn.commit()
        conn.close()
        return rows
    
    def get_plates_by_weight(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                CASE
                    WHEN Plate.RevenueWeight < 3500 THEN '< 3.5t'
                    WHEN Plate.RevenueWeight BETWEEN 3500 AND 7499 THEN '3.5t - 7.5t'
                    WHEN Plate.RevenueWeight BETWEEN 7500 AND 17999 THEN '7.5t - 18t'
                    WHEN Plate.RevenueWeight BETWEEN 18000 AND 31999 THEN '18t - 32t'
                    ELSE '32t+'
                END AS WeightRange,
                SUM(CASE WHEN DATE(Capture.Timestamp) = DATE('now', 'localtime') THEN 1 ELSE 0 END) AS TodayCount,
                SUM(CASE WHEN strftime('%Y-%W', Capture.Timestamp) = strftime('%Y-%W', 'now') THEN 1 ELSE 0 END) AS WeekCount,
                SUM(CASE WHEN strftime('%Y-%m', Capture.Timestamp) = strftime('%Y-%m', 'now') THEN 1 ELSE 0 END) AS MonthCount,
                SUM(CASE WHEN strftime('%Y', Capture.Timestamp) = strftime('%Y', 'now') THEN 1 ELSE 0 END) AS YearCount
            FROM VehicleResult
            JOIN Capture ON Capture.CaptureId = VehicleResult.CaptureId
            JOIN Plate ON Plate.Plate = VehicleResult.DvlaPlate
            GROUP BY WeightRange
            ORDER BY WeightRange;
            ''')
        rows = cursor.fetchall()

        conn.commit()
        conn.close()
        return rows