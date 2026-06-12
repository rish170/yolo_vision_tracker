import json
import os
import uuid
from datetime import datetime
from database.db_manager import DatabaseManager
from core.logger import app_logger

class SessionRecoveryManager:
    """
    Manages session lifecycle and crash recovery.
    Periodically saves current session state.
    """
    def __init__(self):
        self.db = DatabaseManager()
        self.session_id = None
        
    def check_for_crashed_session(self):
        """Checks if the last session was abruptly terminated."""
        query = "SELECT * FROM sessions WHERE is_completed = 0 ORDER BY start_time DESC LIMIT 1"
        res = self.db.execute_query(query)
        if res:
            return res[0]
        return None
        
    def start_new_session(self, profile_name="default"):
        """Starts a new session and logs it to the DB."""
        self.session_id = str(uuid.uuid4())
        start_time = datetime.now().isoformat()
        
        query = """
            INSERT INTO sessions (session_id, start_time, profile_used, is_completed)
            VALUES (?, ?, ?, 0)
        """
        self.db.execute_query(query, (self.session_id, start_time, profile_name), commit=True)
        app_logger.info(f"Started new session: {self.session_id}")
        return self.session_id
        
    def complete_session(self):
        """Marks the current session as safely completed."""
        if not self.session_id:
            return
            
        end_time = datetime.now().isoformat()
        query = "UPDATE sessions SET end_time = ?, is_completed = 1 WHERE session_id = ?"
        self.db.execute_query(query, (end_time, self.session_id), commit=True)
        app_logger.info(f"Completed session: {self.session_id}")
        self.session_id = None
