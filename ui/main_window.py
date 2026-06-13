from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QStackedWidget, QFrame)
from PyQt6.QtCore import Qt, pyqtSlot
from ui.video_widget import VideoWidget
from ui.perf_monitor_panel import PerfMonitorPanel
from ui.widgets.multi_roi_editor import ROIOverlay, MultiROIEditor
from ui.widgets.settings_panel import SettingsPanel
from ui.widgets.events_log_panel import EventsLogPanel
from services.theme_manager import ThemeManager
from services.video_worker import VideoWorker
from core.logger import app_logger

class MainWindow(QMainWindow):
    def __init__(self, theme_manager: ThemeManager):
        super().__init__()
        self.theme_manager = theme_manager
        self.setWindowTitle("VisionTrack-AI")
        self.setMinimumSize(1200, 800)
        
        # Setup UI
        self._init_ui()
        
        # Setup Services
        self.video_worker = VideoWorker()
        self.video_worker.frame_ready.connect(self.video_widget.update_frame)
        self.video_worker.error_occurred.connect(self._handle_video_error)
        
        # Start webcam after a short delay so the GUI can finish loading and rendering
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self.video_worker.start_video(0))

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # Title
        title = QLabel("VisionTrack-AI")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        sidebar_layout.addWidget(title)
        
        # Nav Buttons
        self.btn_live = QPushButton("Live Detection")
        self.btn_events = QPushButton("Events")
        self.btn_settings = QPushButton("Settings")
        self.btn_theme = QPushButton("Toggle Theme")
        
        sidebar_layout.addWidget(self.btn_live)
        sidebar_layout.addWidget(self.btn_events)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_theme)
        
        # 2. Main Content Area (Stack)
        self.content_stack = QStackedWidget()
        
        # Page 0: Live Video
        self.live_page = QWidget()
        live_layout = QHBoxLayout(self.live_page)
        live_layout.setContentsMargins(10, 10, 10, 10)
        
        # Video Area
        video_area = QWidget()
        video_layout = QVBoxLayout(video_area)
        video_layout.setContentsMargins(0,0,0,0)
        
        self.video_widget = VideoWidget()
        # Create ROI Overlay and place it on top of the video widget
        self.roi_overlay = ROIOverlay(self.video_widget)
        self.video_widget.resizeEvent = lambda e: self.roi_overlay.resize(self.video_widget.size())
        
        video_layout.addWidget(self.video_widget)
        
        # Analytics Area
        analytics_area = QVBoxLayout()
        self.perf_panel = PerfMonitorPanel()
        self.roi_editor = MultiROIEditor(self.roi_overlay)
        analytics_area.addWidget(self.perf_panel)
        analytics_area.addWidget(self.roi_editor)
        
        live_layout.addWidget(video_area, stretch=3)
        live_layout.addLayout(analytics_area, stretch=1)
        
        self.content_stack.addWidget(self.live_page)
        
        # Page 1: Events
        self.events_page = EventsLogPanel()
        self.content_stack.addWidget(self.events_page)
        
        # Page 2: Settings
        self.settings_page = SettingsPanel(self.theme_manager)
        self.content_stack.addWidget(self.settings_page)
        
        # Add to main layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack)
        
        # Connect signals
        self.btn_theme.clicked.connect(self.theme_manager.toggle_theme)
        self.btn_live.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        self.btn_events.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        self.btn_settings.clicked.connect(lambda: self.content_stack.setCurrentIndex(2))

    @pyqtSlot(str)
    def _handle_video_error(self, msg):
        app_logger.error(f"Video Error: {msg}")
        # In Phase 3, we will show a Toast notification here

    def closeEvent(self, event):
        """Cleanly shut down threads."""
        app_logger.info("Shutting down application...")
        if self.video_worker:
            self.video_worker.stop()
        event.accept()
