import sqlite3
import os
from PyQt6.QtCore import QMutex, QMutexLocker
from core.logger import app_logger

class DatabaseManager:
    """
    Handles SQLite database connections, schema creation, and threaded operations.
    """
    
    _instance = None
    _mutex = QMutex()
    
    def __new__(cls, db_path="database/visiontrack.db"):
        with QMutexLocker(cls._mutex):
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._init(db_path)
            return cls._instance

    def _init(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self):
        """Returns a new connection for thread-safe operations."""
        # SQLite handles concurrent reads, but writes should ideally use WAL mode
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_schema(self):
        """Initializes the database schema (V2)."""
        app_logger.info("Initializing database schema...")
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Table: sessions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        start_time TEXT,
                        end_time TEXT,
                        profile_used TEXT,
                        is_completed BOOLEAN
                    )
                """)
                
                # Table: object_trajectories
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS object_trajectories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        track_id INTEGER,
                        class_name TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        dwell_time REAL,
                        max_speed REAL,
                        path_data TEXT
                    )
                """)
                
                # Table: events
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        timestamp TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        message TEXT,
                        snapshot_path TEXT
                    )
                """)
                
                # Table: multi_rois
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS multi_rois (
                        roi_id TEXT PRIMARY KEY,
                        name TEXT,
                        color TEXT,
                        polygon_points TEXT,
                        is_active BOOLEAN
                    )
                """)
                
                conn.commit()
                app_logger.info("Database schema initialized successfully.")
        except Exception as e:
            app_logger.error(f"Failed to initialize database schema: {e}")

    def execute_query(self, query, params=(), commit=False):
        """Executes a single query and returns results."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                if commit:
                    conn.commit()
                    return cursor.lastrowid
                else:
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            app_logger.error(f"Database query error: {e}")
            return None

if __name__ == "__main__":
    db = DatabaseManager()
    print("DB initialized at:", db.db_path)
