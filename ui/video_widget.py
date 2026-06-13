import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QImage, QPainter, QPixmap, QColor, QPen, QPolygonF, QBrush
from PyQt6.QtCore import Qt, QRectF, QPointF
from tracking.deepsort_tracker import TrackedObject
from services.settings_manager import SettingsManager
from core.logger import app_logger

class VideoWidget(QWidget):
    """
    Custom widget to display the video feed and draw overlays (bounding boxes, trails, masks).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.tracked_objects = []
        self.fps = 0.0
        self.model_name = ""
        self.resolution = (0, 0)
        self.settings = SettingsManager()
        self.draw_trails = self.settings.get("show_trails", True)

    def update_frame(self, frame_data):
        """
        Updates the frame and overlays.
        frame_data: dict containing 'frame' (BGR numpy array), 'tracks', 'fps', etc.
        """
        frame = frame_data.get("frame")
        if frame is None:
            return

        self.tracked_objects = frame_data.get("tracks", [])
        self.fps = frame_data.get("fps", 0.0)
        self.model_name = frame_data.get("model_name", "")
        self.resolution = (frame.shape[1], frame.shape[0])
        self.analytics = frame_data.get("analytics", {"dwell": {}, "speed": {}})
        self.draw_trails = self.settings.get("show_trails", True)

        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        # We need to copy to prevent memory corruption if numpy reuses the buffer
        self.image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        
        self.update() # Trigger paintEvent

    def paintEvent(self, event):
        """Handles drawing the image and all overlays."""
        if self.image is None:
            # Draw placeholder
            painter = QPainter(self)
            painter.setBrush(QColor(20, 20, 25))
            painter.drawRect(self.rect())
            painter.setPen(QColor(100, 100, 110))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Video Feed")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Scale image to fit widget while maintaining aspect ratio
        rect = self.rect()
        scaled_img = self.image.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        # Center the image
        x_offset = int((rect.width() - scaled_img.width()) / 2)
        y_offset = int((rect.height() - scaled_img.height()) / 2)
        
        painter.drawImage(x_offset, y_offset, scaled_img)

        # Scale factors for drawing overlays
        scale_x = scaled_img.width() / self.resolution[0] if self.resolution[0] > 0 else 1.0
        scale_y = scaled_img.height() / self.resolution[1] if self.resolution[1] > 0 else 1.0

        # 2. Draw Object Overlays
        for track in self.tracked_objects:
            self._draw_track(painter, track, x_offset, y_offset, scale_x, scale_y)

        # 3. Draw HUD (FPS, Model, Resolution)
        self._draw_hud(painter, rect)

    def _draw_track(self, painter: QPainter, track: TrackedObject, ox: int, oy: int, sx: float, sy: float):
        l, t, r, b = track.bbox
        
        # Scale coordinates
        x = ox + int(l * sx)
        y = oy + int(t * sy)
        w = int((r - l) * sx)
        h = int((b - t) * sy)

        # Color based on class or ID (using a simple hash for color variety)
        hue = (track.track_id * 37) % 360
        color = QColor.fromHsv(hue, 200, 250)

        # Draw Mask Polygon (Segmentation)
        if track.mask_polygon:
            poly = QPolygonF()
            for px, py in track.mask_polygon:
                poly.append(QPointF(ox + px * sx, oy + py * sy))
            
            mask_color = QColor(color)
            mask_color.setAlpha(80) # Semi-transparent
            painter.setBrush(QBrush(mask_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(poly)

        # Draw Bounding Box
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(x, y, w, h)

        # Get analytics
        dwell_s = self.analytics.get("dwell", {}).get(track.track_id, 0)
        speed_info = self.analytics.get("speed", {}).get(track.track_id, {"value": 0, "unit": ""})
        
        # Draw Label Background
        label_text = f"ID:{track.track_id} {track.class_name} {int(track.confidence*100)}% | {int(dwell_s)}s | {speed_info['value']} {speed_info['unit']}"
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(label_text)
        text_height = font_metrics.height()
        
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        # Rounded background for label
        painter.drawRoundedRect(x, y - text_height - 4, text_width + 8, text_height + 4, 4, 4)

        # Draw Label Text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(x + 4, y - 4, label_text)

        # Draw Trail
        if self.draw_trails and track.ui_trail and len(track.ui_trail) > 1:
            for i in range(1, len(track.ui_trail)):
                p1 = track.ui_trail[i-1]
                p2 = track.ui_trail[i]
                
                # Fading effect
                alpha = int(255 * (i / len(track.ui_trail)))
                trail_color = QColor(color)
                trail_color.setAlpha(alpha)
                
                painter.setPen(QPen(trail_color, 2))
                painter.drawLine(
                    int(ox + p1[0] * sx), int(oy + p1[1] * sy),
                    int(ox + p2[0] * sx), int(oy + p2[1] * sy)
                )

    def _draw_hud(self, painter: QPainter, rect):
        """Draws top-left info overlay."""
        painter.setPen(QColor(255, 255, 255))
        
        # Semi-transparent background
        hud_rect = QRectF(10, 10, 200, 70)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(hud_rect, 6, 6)
        
        # Text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(20, 30, f"FPS: {self.fps:.1f}")
        painter.drawText(20, 50, f"Model: {self.model_name}")
        painter.drawText(20, 70, f"Res: {self.resolution[0]}x{self.resolution[1]}")
