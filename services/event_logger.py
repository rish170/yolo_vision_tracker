from datetime import datetime
from database.db_manager import DatabaseManager
from core.logger import app_logger

class EventLogger:
    """
    Logs significant tracking and system events to the SQLite database.
    Supports severity levels: INFO, WARNING, CRITICAL.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db = DatabaseManager()

    def log_event(self, severity: str, event_type: str, message: str, snapshot_path: str = None):
        """
        Logs an event to the database.
        severity: "INFO", "WARNING", "CRITICAL"
        """
        timestamp = datetime.now().isoformat()
        
        query = """
            INSERT INTO events (session_id, timestamp, severity, event_type, message, snapshot_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (self.session_id, timestamp, severity, event_type, message, snapshot_path)
        
        try:
            # We use commit=True to persist immediately, 
            # WAL mode handles concurrent writes well.
            self.db.execute_query(query, params, commit=True)
            
            # Also pipe to file logger
            log_msg = f"[{event_type}] {message}"
            if severity == "CRITICAL":
                app_logger.critical(log_msg)
            elif severity == "WARNING":
                app_logger.warning(log_msg)
            else:
                app_logger.info(log_msg)
                
        except Exception as e:
            app_logger.error(f"Failed to log event to DB: {e}")
