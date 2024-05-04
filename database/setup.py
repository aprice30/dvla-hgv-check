import logging
import sqlite3
from sqlite3 import Error

logger = logging.getLogger(__name__)

class Setup:
    motion_event_table = """CREATE TABLE motion_event (
	event_id INTEGER PRIMARY KEY,
    recorded_at DATETIME NOT NULL,
	number_plate TEXT NOT NULL);"""

    def __init__(self, db_file: str):
        self.db_file = db_file

    def _createConnection(self) -> sqlite3.Connection:
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            logger.info("Created connection to File=%s Version=%s", self.db_file, sqlite3.version)
        except Error as e:
            logger.exception("Failed to connect to %s: %s", self.db_file, repr(e))
        
        return conn
   
    def _table_exists(self, conn: sqlite3.Connection, name: str) -> bool:
        try:
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [name]).fetchone()
            return result is not None
        except Error as e:
            logger.exception("Failed to check if table=%s exists: %s", name, repr(e))
        
        return False
        
    def _create_table(self, conn: sqlite3.Connection, name: str, sql: str):
        try:
            if self._table_exists(conn, name):
                logger.info("Skipping creating table=%s as it already exists", name)
            else:
                c = conn.cursor()
                c.execute(sql)
                logger.info("Created table=%s", name)
        except Error as e:
            logger.exception("Failed to create create table: %s", repr(e))

    def run(self):
        try:
            conn = self._createConnection()

            # Tables
            self._create_table(conn, "motion_event", self.motion_event_table)
        finally:
            if conn is not None:
                conn.close()