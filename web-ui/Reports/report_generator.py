import sqlite3
from datetime import datetime, timedelta
from PlateProcessor.storage import Storage

def generate_weekly_report():
    # Define the date range for the current week
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday

    # Connect to the database
    db = Storage()
    conn = db._get_connection()

    cursor = conn.cursor()
    cursor.execute('''
        SELECT Capture.Timestamp, Plate.Plate, Plate.VehicleMake, Plate.RevenueWeight
        FROM VehicleResult
        JOIN Capture ON Capture.CaptureId = VehicleResult.CaptureId
        JOIN Plate ON Plate.Plate = VehicleResult.DvlaPlate
        WHERE Plate.RevenueWeight >= 7500
        AND Capture.Timestamp BETWEEN ? AND ?
        ORDER BY Capture.Timestamp DESC;
    ''', (start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')))
    rows = cursor.fetchall()

    # Process and generate the report
    report = "Weekly Report\n\n"
    for row in rows:
        report += f"Timestamp: {row[0]}, Plate: {row[1]}, Type Approval: {row[2]}, Make: {row[3]}, Weight: {row[4]}\n"

    # Save or send the report (e.g., save to a file, email, etc.)
    with open('weekly_report.txt', 'w') as f:
        f.write(report)

    conn.close()
