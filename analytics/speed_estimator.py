import math
import time
from typing import Dict, Tuple, List
from core.logger import app_logger

class SpeedEstimator:
    """
    Estimates object speed based on pixel displacement or real-world calibration.
    Maintains a history of object positions to calculate velocity over time.
    """
    def __init__(self, mode="relative", pixels_per_meter=100.0):
        self.mode = mode # 'relative' or 'real_world'
        self.pixels_per_meter = pixels_per_meter
        self.history: Dict[int, List[Tuple[float, float, float]]] = {} # track_id -> [(x, y, timestamp)]
        self.max_history_len = 10 # Frames to keep for smoothing

    def set_calibration(self, pixels_per_meter: float):
        """Sets the calibration ratio and switches to real-world mode."""
        self.pixels_per_meter = pixels_per_meter
        self.mode = "real_world"
        app_logger.info(f"SpeedEstimator calibrated: {pixels_per_meter} px/m")

    def update(self, track_id: int, center_x: float, center_y: float) -> dict:
        """
        Updates the position history and calculates current speed.
        Returns a dictionary with speed values.
        """
        current_time = time.time()
        
        if track_id not in self.history:
            self.history[track_id] = []
            
        history = self.history[track_id]
        history.append((center_x, center_y, current_time))
        
        if len(history) > self.max_history_len:
            history.pop(0)
            
        if len(history) < 2:
            return {"value": 0.0, "unit": "px/s", "mode": self.mode}

        # Calculate speed using the oldest and newest point in the smoothed history
        p1 = history[0]
        p2 = history[-1]
        
        dt = p2[2] - p1[2]
        if dt <= 0:
            return {"value": 0.0, "unit": "px/s", "mode": self.mode}
            
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        pixel_distance = math.sqrt(dx**2 + dy**2)
        
        pixels_per_second = pixel_distance / dt

        if self.mode == "relative":
            return {
                "value": round(pixels_per_second, 1), 
                "unit": "px/s", 
                "mode": "relative"
            }
        else:
            # Convert to meters per second
            meters_per_second = pixels_per_second / self.pixels_per_meter
            km_per_hour = meters_per_second * 3.6
            return {
                "value": round(km_per_hour, 1), 
                "unit": "km/h", 
                "mode": "real_world",
                "mps": round(meters_per_second, 2)
            }

    def cleanup_lost_tracks(self, active_track_ids: List[int]):
        """Removes history for tracks that are no longer active to prevent memory leaks."""
        keys_to_remove = [tid for tid in self.history.keys() if tid not in active_track_ids]
        for tid in keys_to_remove:
            del self.history[tid]
