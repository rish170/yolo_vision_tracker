import cv2
import time
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from detection.yolo_detector import YOLODetector
from tracking.deepsort_tracker import DeepSORTTracker
from services.settings_manager import SettingsManager
from core.logger import app_logger
from core.session_recovery import SessionRecoveryManager
from analytics.speed_estimator import SpeedEstimator
from analytics.dwell_time import DwellTimeCalculator
from analytics.alert_engine import AlertEngine
from services.event_logger import EventLogger
from database.db_manager import DatabaseManager
import json

class VideoWorker(QThread):
    """
    Background thread for video processing (capture -> detect -> track -> analyze).
    """
    frame_ready = pyqtSignal(dict) # Emits {frame, tracks, fps, model_name, analytics}
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()
        self.db = DatabaseManager()
        self._is_running = False
        self._is_paused = False
        self._mutex = QMutex()
        
        self.source = 0 # Default webcam
        self.capture = None
        self.detector = None
        self.tracker = None
        
        # Performance state
        self.fps_filter = 0.0

    def start_video(self, source):
        """Starts processing a new video source."""
        with QMutexLocker(self._mutex):
            self.source = source
            self._is_running = True
            self._is_paused = False
        self.start()

    def stop(self):
        with QMutexLocker(self._mutex):
            self._is_running = False
        self.wait()

    def set_paused(self, paused: bool):
        with QMutexLocker(self._mutex):
            self._is_paused = paused

    def run(self):
        app_logger.info(f"VideoWorker started for source: {self.source}")
        
        # Session & Analytics Init
        session_manager = SessionRecoveryManager()
        session_id = session_manager.start_new_session()
        event_logger = EventLogger(session_id)
        alert_engine = AlertEngine(event_logger)
        
        mode = self.settings.get("speed_estimation_mode", "relative")
        ppm = self.settings.get("pixels_per_meter", 100.0)
        speed_estimator = SpeedEstimator(mode=mode, pixels_per_meter=ppm)
        dwell_calc = DwellTimeCalculator()
        
        # Load active ROIs
        rois = {}
        rows = self.db.execute_query("SELECT * FROM multi_rois WHERE is_active=1")
        if rows:
            for r in rows:
                pts = json.loads(r["polygon_points"])
                # We need simple tuples for the alert engine
                from PyQt6.QtCore import QPointF
                points = [QPointF(p["x"], p["y"]) for p in pts]
                rois[r["roi_id"]] = {"name": r["name"], "points": points, "active": True}

        # Load dummy rules for Phase 2 demonstration
        alert_engine.load_rules([{
            "id": "rule_person_count",
            "type": "count_threshold",
            "class": "person",
            "threshold": 3,
            "severity": "WARNING",
            "message": "Crowd threshold exceeded: {count} persons detected."
        }])

        # Initialize OpenCV Capture
        app_logger.info("Initializing webcam...")
        self.error_occurred.emit("Connecting to webcam...")
        
        # On Windows, DirectShow backend (CAP_DSHOW) often prevents hanging
        import sys
        if sys.platform.startswith('win'):
            self.capture = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        else:
            self.capture = cv2.VideoCapture(self.source)
            
        if not self.capture.isOpened():
            self.error_occurred.emit(f"Failed to open video source: {self.source}")
            return

        # Initialize AI Models
        app_logger.info("Loading AI Models...")
        self.error_occurred.emit("Loading AI models (This may take a few seconds on CPU)...")
        
        model_name = self.settings.get("model_name", "yolov8n-seg.pt")
        self.detector = YOLODetector(model_name)
        self.tracker = DeepSORTTracker()
        
        self.error_occurred.emit("System Ready")

        prev_time = time.time()
        last_db_flush = time.time()

        while True:
            with QMutexLocker(self._mutex):
                if not self._is_running:
                    break
                is_paused = self._is_paused

            if is_paused:
                time.sleep(0.1)
                continue

            ret, frame = self.capture.read()
            if not ret:
                app_logger.info("End of video stream.")
                break

            curr_time = time.time()

            # 1. Detect
            conf_thresh = self.settings.get("confidence_threshold", 0.5)
            enabled_classes = self.settings.get("enabled_classes")
            detections = self.detector.detect(frame, conf_thresh, enabled_classes)

            # 2. Track
            tracked_objects = self.tracker.update(detections, frame)
            
            # 3. Analytics (Dwell & Speed)
            # Update Speed Estimator settings dynamically
            speed_estimator.mode = self.settings.get("speed_estimation_mode", "relative")
            speed_estimator.pixels_per_meter = self.settings.get("pixels_per_meter", 100.0)
            
            active_ids = [t.track_id for t in tracked_objects]
            dwell_times = dwell_calc.update(active_ids)
            
            speeds = {}
            for t in tracked_objects:
                l, top, r, b = t.bbox
                cx = (l + r) / 2
                cy = (top + b) / 2
                speeds[t.track_id] = speed_estimator.update(t.track_id, cx, cy)
                
                # Trajectory DB flush (Phase 3 prep)
                if curr_time - last_db_flush > 1.0:
                    self.db.execute_query(
                        "INSERT INTO object_trajectories (session_id, track_id, class_name, start_time, max_speed) VALUES (?, ?, ?, ?, ?)",
                        (session_id, t.track_id, t.class_name, datetime.now().isoformat(), speeds[t.track_id]["value"])
                    )

            if curr_time - last_db_flush > 1.0:
                last_db_flush = curr_time

            speed_estimator.cleanup_lost_tracks(active_ids)
            dwell_calc.cleanup_lost_tracks(active_ids)
            
            # 4. Alert Engine
            # Update dynamic rules
            crowd_thresh = self.settings.get("crowd_threshold", 3)
            for rule in alert_engine.rules:
                if rule["id"] == "rule_person_count":
                    rule["threshold"] = crowd_thresh
                    
            alert_engine.evaluate(tracked_objects, rois, curr_time)

            # 5. FPS Calculation
            dt = curr_time - prev_time
            prev_time = curr_time
            inst_fps = 1.0 / dt if dt > 0 else 0
            self.fps_filter = (self.fps_filter * 0.9) + (inst_fps * 0.1)

            # 6. Emit results
            analytics_data = {"dwell": dwell_times, "speed": speeds}
            frame_data = {
                "frame": frame,
                "tracks": tracked_objects,
                "fps": self.fps_filter,
                "model_name": self.detector.model_name,
                "analytics": analytics_data
            }
            self.frame_ready.emit(frame_data)

            fps_limit = self.settings.get("fps_limit", 0)
            if fps_limit > 0:
                target_dt = 1.0 / fps_limit
                elapsed = time.time() - curr_time
                if elapsed < target_dt:
                    time.sleep(target_dt - elapsed)

        if self.capture:
            self.capture.release()
        session_manager.complete_session()
        app_logger.info("VideoWorker stopped.")
