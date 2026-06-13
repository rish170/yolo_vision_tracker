from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QColorDialog, QInputDialog, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from database.db_manager import DatabaseManager
import uuid
import json

class ROIOverlay(QWidget):
    """
    Transparent widget placed over the video feed to handle drawing ROIs.
    """
    roi_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.rois = {} # roi_id -> {"name": str, "color": QColor, "points": [QPointF], "active": bool}
        self.drawing_points = []
        self.is_drawing = False
        self.drawing_color = QColor(255, 0, 0)
        self.drawing_name = ""

    def start_drawing(self, name, color):
        self.is_drawing = True
        self.drawing_points = []
        self.drawing_color = color
        self.drawing_name = name
        self.setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event):
        if self.is_drawing:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drawing_points.append(event.position())
                self.update()
            elif event.button() == Qt.MouseButton.RightButton and len(self.drawing_points) > 2:
                # Finish drawing
                roi_id = str(uuid.uuid4())
                self.rois[roi_id] = {
                    "name": self.drawing_name,
                    "color": self.drawing_color,
                    "points": list(self.drawing_points),
                    "active": True
                }
                self.cancel_drawing()
                self.roi_updated.emit()
                
    def cancel_drawing(self):
        self.is_drawing = False
        self.drawing_points = []
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        
    def keyPressEvent(self, event):
        if self.is_drawing and event.key() == Qt.Key.Key_Escape:
            self.cancel_drawing()

    def mouseMoveEvent(self, event):
        if self.is_drawing and len(self.drawing_points) > 0:
            # We could draw a live line to the cursor here
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw completed ROIs
        for roi_id, roi in self.rois.items():
            if not roi["active"]:
                continue
                
            poly = QPolygonF(roi["points"])
            
            fill_color = QColor(roi["color"])
            fill_color.setAlpha(50)
            painter.setBrush(QBrush(fill_color))
            
            pen = QPen(roi["color"], 2)
            painter.setPen(pen)
            
            painter.drawPolygon(poly)
            
            # Draw name
            painter.setPen(QColor(255, 255, 255))
            if roi["points"]:
                painter.drawText(roi["points"][0], roi["name"])

        # Draw active drawing
        if self.is_drawing and len(self.drawing_points) > 0:
            pen = QPen(self.drawing_color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            if len(self.drawing_points) == 1:
                painter.drawPoint(self.drawing_points[0])
            else:
                poly = QPolygonF(self.drawing_points)
                painter.drawPolyline(poly)


class MultiROIEditor(QWidget):
    """
    Control panel for managing multiple ROIs.
    """
    def __init__(self, overlay: ROIOverlay):
        super().__init__()
        self.overlay = overlay
        self.overlay.roi_updated.connect(self.refresh_list)
        self.db = DatabaseManager()
        self._init_ui()
        self.load_from_db()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel("<b>Region of Interest (ROI)</b><br>Draw boundary zones or tripwires to trigger alerts when objects enter them.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.btn_add = QPushButton("Draw New ROI")
        self.btn_add.clicked.connect(self.add_roi)
        layout.addWidget(self.btn_add)
        
        self.help_label = QLabel("<i>Left-click to add points.<br>Right-click to finish shape.<br>Press Esc to cancel.</i>")
        self.help_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.help_label.hide()
        layout.addWidget(self.help_label)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_roi)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

    def add_roi(self):
        name, ok = QInputDialog.getText(self, "New ROI", "Enter ROI Name (e.g., 'Restricted Zone'):")
        if ok and name:
            color = QColorDialog.getColor()
            if color.isValid():
                self.overlay.start_drawing(name, color)
                self.overlay.setFocus() # Ensure Esc key works
                self.help_label.show()

    def refresh_list(self):
        self.list_widget.clear()
        for roi_id, roi in self.overlay.rois.items():
            item = QListWidgetItem(f"{roi['name']}")
            item.setData(Qt.ItemDataRole.UserRole, roi_id)
            self.list_widget.addItem(item)
        self.save_to_db()
        self.help_label.hide()

    def delete_roi(self):
        current = self.list_widget.currentItem()
        if current:
            roi_id = current.data(Qt.ItemDataRole.UserRole)
            if roi_id in self.overlay.rois:
                del self.overlay.rois[roi_id]
                self.db.execute_query("DELETE FROM multi_rois WHERE roi_id=?", (roi_id,), commit=True)
                self.refresh_list()
                self.overlay.update()

    def save_to_db(self):
        for roi_id, roi in self.overlay.rois.items():
            pts = [{"x": p.x(), "y": p.y()} for p in roi["points"]]
            query = "INSERT OR REPLACE INTO multi_rois (roi_id, name, color, polygon_points, is_active) VALUES (?, ?, ?, ?, ?)"
            self.db.execute_query(query, (roi_id, roi["name"], roi["color"].name(), json.dumps(pts), roi["active"]), commit=True)

    def load_from_db(self):
        rows = self.db.execute_query("SELECT * FROM multi_rois")
        if rows:
            for row in rows:
                pts_data = json.loads(row["polygon_points"])
                points = [QPointF(p["x"], p["y"]) for p in pts_data]
                self.overlay.rois[row["roi_id"]] = {
                    "name": row["name"],
                    "color": QColor(row["color"]),
                    "points": points,
                    "active": bool(row["is_active"])
                }
            self.refresh_list()
            self.overlay.update()
