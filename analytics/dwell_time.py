import time
from typing import Dict, List
from core.logger import app_logger

class DwellTimeCalculator:
    """
    Calculates how long tracked objects have been visible in the frame.
    """
    def __init__(self):
        # track_id -> first_seen_timestamp
        self.first_seen: Dict[int, float] = {}
        # track_id -> total_seconds_visible
        self.dwell_times: Dict[int, float] = {}

    def update(self, active_track_ids: List[int]) -> Dict[int, float]:
        """
        Updates the dwell times based on currently active tracks.
        Returns a dictionary of track_id to total dwell time in seconds.
        """
        current_time = time.time()
        
        # Update active tracks
        for tid in active_track_ids:
            if tid not in self.first_seen:
                self.first_seen[tid] = current_time
            
            self.dwell_times[tid] = current_time - self.first_seen[tid]
            
        # Clean up lost tracks
        lost_keys = [tid for tid in self.first_seen.keys() if tid not in active_track_ids]
        for tid in lost_keys:
            # We don't delete immediately if we want to store it to DB,
            # but for this module, it tracks active ones.
            # In Phase 2, Event Logger or Trajectory Manager will persist this to DB
            # before it's deleted here.
            pass
            # del self.first_seen[tid]
            # del self.dwell_times[tid]
            
        return {tid: self.dwell_times[tid] for tid in active_track_ids}
        
    def cleanup_lost_tracks(self, active_track_ids: List[int]):
        """Explicitly cleanup tracks that are confirmed lost and stored to DB."""
        lost_keys = [tid for tid in self.first_seen.keys() if tid not in active_track_ids]
        for tid in lost_keys:
            del self.first_seen[tid]
            del self.dwell_times[tid]
