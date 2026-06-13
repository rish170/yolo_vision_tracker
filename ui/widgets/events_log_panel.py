from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QHBoxLayout, QPushButton, QComboBox, QLabel)
from PyQt6.QtCore import Qt, QTimer
from database.db_manager import DatabaseManager
from core.logger import app_logger

class EventsLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self._init_ui()
        self.load_events()
        
        # Auto-refresh timer (every 5 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_events)
        self.timer.start(5000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header Area
        header_layout = QHBoxLayout()
        title = QLabel("System Events & Alerts")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.cb_filter = QComboBox()
        self.cb_filter.addItems(["ALL", "INFO", "WARNING", "CRITICAL"])
        self.cb_filter.currentTextChanged.connect(self.load_events)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.cb_filter)
        
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.load_events)
        header_layout.addWidget(self.btn_refresh)
        
        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Severity", "Type", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_events(self):
        try:
            severity_filter = self.cb_filter.currentText()
            
            if severity_filter == "ALL":
                query = "SELECT timestamp, severity, event_type, message FROM events ORDER BY id DESC LIMIT 100"
                params = ()
            else:
                query = "SELECT timestamp, severity, event_type, message FROM events WHERE severity = ? ORDER BY id DESC LIMIT 100"
                params = (severity_filter,)
                
            rows = self.db.execute_query(query, params)
            
            self.table.setRowCount(0)
            if rows:
                for row_idx, row_data in enumerate(rows):
                    self.table.insertRow(row_idx)
                    
                    # Colors based on severity
                    severity = row_data["severity"]
                    color = None
                    if severity == "CRITICAL":
                        color = Qt.GlobalColor.red
                    elif severity == "WARNING":
                        color = Qt.GlobalColor.yellow
                        
                    for col_idx, key in enumerate(["timestamp", "severity", "event_type", "message"]):
                        item = QTableWidgetItem(str(row_data[key]))
                        if color:
                            item.setForeground(color)
                        self.table.setItem(row_idx, col_idx, item)
                        
        except Exception as e:
            app_logger.error(f"Failed to load events: {e}")
