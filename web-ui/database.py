import sqlite3

db_path = '/home/myuser/data/db/dvla.db'

def get_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn