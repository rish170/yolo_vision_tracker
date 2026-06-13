import json
import os
from PyQt6.QtCore import QMutex, QMutexLocker, QRecursiveMutex
from core.logger import app_logger

class SettingsManager:
    """
    Manages application settings with JSON persistence.
    Thread-safe implementation.
    """
    
    _instance = None
    _mutex = QRecursiveMutex()
    
    DEFAULT_SETTINGS = {
        "theme": "dark",
        "model_name": "yolov8n-seg.pt",  # Default to segmentation model
        "confidence_threshold": 0.5,
        "camera_index": 0,
        "fps_limit": 30,
        "recording_format": "mp4",
        "storage_path": "exports",
        "enable_segmentation_masks": True,
        "show_trails": True,
        "speed_estimation_mode": "relative", # 'relative' or 'real_world'
        "pixels_per_meter": 100.0,
        "enabled_classes": [0, 1, 2, 3, 5, 7], # COCO ids for person, bicycle, car, motorcycle, bus, truck
        "crowd_threshold": 3
    }

    def __new__(cls, config_path="config/settings.json"):
        with QMutexLocker(cls._mutex):
            if cls._instance is None:
                cls._instance = super(SettingsManager, cls).__new__(cls)
                cls._instance._init(config_path)
            return cls._instance

    def _init(self, config_path):
        self.config_path = config_path
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Loads settings from JSON file."""
        with QMutexLocker(self._mutex):
            if not os.path.exists(self.config_path):
                self._save_internal()
                return

            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    # Update defaults with loaded values
                    for k, v in data.items():
                        if k in self.settings:
                            self.settings[k] = v
                app_logger.info(f"Settings loaded from {self.config_path}")
            except Exception as e:
                app_logger.error(f"Failed to load settings: {e}")

    def _save_internal(self):
        """Internal save method without lock (lock must be held)."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            app_logger.error(f"Failed to save settings: {e}")

    def save(self):
        """Saves current settings to JSON file."""
        with QMutexLocker(self._mutex):
            self._save_internal()
            app_logger.info("Settings saved.")

    def get(self, key, default=None):
        """Gets a setting value."""
        with QMutexLocker(self._mutex):
            return self.settings.get(key, default)

    def set(self, key, value):
        """Sets a setting value and saves."""
        with QMutexLocker(self._mutex):
            if key in self.settings and self.settings[key] == value:
                return # No change
            self.settings[key] = value
            self._save_internal()
            
    def get_all(self):
        """Returns a copy of all settings."""
        with QMutexLocker(self._mutex):
            return self.settings.copy()
