from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QFormLayout, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, 
                             QPushButton, QLabel, QHBoxLayout, QLineEdit)
from PyQt6.QtCore import Qt
from services.settings_manager import SettingsManager
from core.logger import app_logger

class SettingsPanel(QWidget):
    def __init__(self, theme_manager=None):
        super().__init__()
        self.settings = SettingsManager()
        self.theme_manager = theme_manager
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Build Tabs
        self._build_general_tab()
        self._build_ai_tab()
        self._build_analytics_tab()

        # Save Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setStyleSheet("background-color: #007acc; color: white; padding: 10px 20px; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _build_general_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["dark", "light"])
        layout.addRow("Theme:", self.cb_theme)

        self.sb_camera = QSpinBox()
        self.sb_camera.setRange(0, 10)
        layout.addRow("Camera Index:", self.sb_camera)

        self.sb_fps = QSpinBox()
        self.sb_fps.setRange(1, 120)
        layout.addRow("FPS Limit:", self.sb_fps)

        self.tabs.addTab(tab, "General")

    def _build_ai_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        self.cb_model = QComboBox()
        self.cb_model.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8n-seg.pt", "yolov8s-seg.pt"])
        layout.addRow("YOLO Model:", self.cb_model)

        self.sb_conf = QDoubleSpinBox()
        self.sb_conf.setRange(0.1, 1.0)
        self.sb_conf.setSingleStep(0.05)
        layout.addRow("Confidence Threshold:", self.sb_conf)

        self.chk_masks = QCheckBox("Enable Segmentation Masks (requires -seg model)")
        layout.addRow("Segmentation:", self.chk_masks)

        self.le_classes = QLineEdit()
        self.le_classes.setPlaceholderText("e.g. 0,1,2,3")
        self.le_classes.setToolTip("Comma-separated COCO class IDs (0=Person, 2=Car)")
        layout.addRow("Enabled Classes:", self.le_classes)

        self.tabs.addTab(tab, "AI Models")

    def _build_analytics_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        self.cb_speed_mode = QComboBox()
        self.cb_speed_mode.addItems(["relative", "real_world"])
        layout.addRow("Speed Mode:", self.cb_speed_mode)

        self.sb_ppm = QDoubleSpinBox()
        self.sb_ppm.setRange(0.1, 10000.0)
        self.sb_ppm.setDecimals(1)
        layout.addRow("Pixels per Meter:", self.sb_ppm)

        self.chk_trails = QCheckBox("Show Movement Trails")
        layout.addRow("Visuals:", self.chk_trails)

        self.sb_crowd_thresh = QSpinBox()
        self.sb_crowd_thresh.setRange(1, 100)
        layout.addRow("Crowd Threshold Limit:", self.sb_crowd_thresh)

        self.tabs.addTab(tab, "Analytics")

    def load_settings(self):
        # General
        self.cb_theme.setCurrentText(self.settings.get("theme", "dark"))
        self.sb_camera.setValue(int(self.settings.get("camera_index", 0)))
        self.sb_fps.setValue(int(self.settings.get("fps_limit", 30)))
        
        # AI
        self.cb_model.setCurrentText(self.settings.get("model_name", "yolov8n-seg.pt"))
        self.sb_conf.setValue(float(self.settings.get("confidence_threshold", 0.5)))
        self.chk_masks.setChecked(bool(self.settings.get("enable_segmentation_masks", True)))
        
        classes = self.settings.get("enabled_classes", [0, 1, 2, 3, 5, 7])
        self.le_classes.setText(",".join(map(str, classes)))

        # Analytics
        self.cb_speed_mode.setCurrentText(self.settings.get("speed_estimation_mode", "relative"))
        self.sb_ppm.setValue(float(self.settings.get("pixels_per_meter", 100.0)))
        self.chk_trails.setChecked(bool(self.settings.get("show_trails", True)))
        self.sb_crowd_thresh.setValue(int(self.settings.get("crowd_threshold", 3)))

    def save_settings(self):
        # General
        new_theme = self.cb_theme.currentText()
        if new_theme != self.settings.get("theme"):
            self.settings.set("theme", new_theme)
            if self.theme_manager:
                self.theme_manager.apply_theme(new_theme)
                
        self.settings.set("camera_index", self.sb_camera.value())
        self.settings.set("fps_limit", self.sb_fps.value())
        
        # AI
        self.settings.set("model_name", self.cb_model.currentText())
        self.settings.set("confidence_threshold", self.sb_conf.value())
        self.settings.set("enable_segmentation_masks", self.chk_masks.isChecked())
        
        # Parse classes
        class_str = self.le_classes.text()
        try:
            classes = [int(x.strip()) for x in class_str.split(",") if x.strip()]
            self.settings.set("enabled_classes", classes)
        except ValueError:
            app_logger.warning("Invalid class format. Using default.")
            
        # Analytics
        self.settings.set("speed_estimation_mode", self.cb_speed_mode.currentText())
        self.settings.set("pixels_per_meter", self.sb_ppm.value())
        self.settings.set("show_trails", self.chk_trails.isChecked())
        self.settings.set("crowd_threshold", self.sb_crowd_thresh.value())

        app_logger.info("Settings saved via UI.")
        
        # Need to restart VideoWorker or show toast for some settings to take effect
