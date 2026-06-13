import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from core.logger import app_logger
from services.settings_manager import SettingsManager

class ThemeManager(QObject):
    """
    Manages loading and applying QSS stylesheets for Light and Dark modes.
    """
    theme_changed = pyqtSignal(str) # Emits the new theme name

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.settings = SettingsManager()
        self.current_theme = self.settings.get("theme", "dark")
        
        # Ensure style directories exist
        os.makedirs("styles", exist_ok=True)
        self._ensure_default_styles()

    def _ensure_default_styles(self):
        """Creates basic QSS files if they don't exist."""
        dark_path = "styles/dark_theme.qss"
        light_path = "styles/light_theme.qss"

        # Always overwrite to ensure updates propagate
        with open(dark_path, "w") as f:
                f.write("""
/* Dark Theme V1 (AntiGravity Grey) */
QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: 'Segoe UI', Inter, sans-serif;
    font-size: 14px;
}
QMainWindow {
    background-color: #1e1e1e;
}
QPushButton {
    background-color: #333333;
    border: 1px solid #454545;
    border-radius: 6px;
    padding: 8px 16px;
    color: #cccccc;
}
QPushButton:hover {
    background-color: #007acc;
    border: 1px solid #0098ff;
    color: white;
}
QLabel {
    background: transparent;
}
/* Sidebars and Panels */
#Sidebar, #AnalyticsPanel {
    background-color: #252526;
    border-right: 1px solid #333333;
    border-left: 1px solid #333333;
}
/* Cards */
.StatCard {
    background-color: #2d2d2d;
    border: 1px solid #3e3e42;
    border-radius: 8px;
}
""")

        # Always overwrite to ensure updates propagate
        with open(light_path, "w") as f:
                f.write("""
/* Light Theme V1 */
QWidget {
    background-color: #ffffff;
    color: #1e293b;
    font-family: 'Segoe UI', Inter, sans-serif;
    font-size: 14px;
}
QMainWindow {
    background-color: #f8fafc;
}
QPushButton {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 16px;
    color: #0f172a;
}
QPushButton:hover {
    background-color: #3b82f6;
    color: white;
    border: 1px solid #2563eb;
}
QLabel {
    background: transparent;
}
/* Sidebars and Panels */
#Sidebar, #AnalyticsPanel {
    background-color: rgba(241, 245, 249, 0.8);
    border-right: 1px solid #e2e8f0;
    border-left: 1px solid #e2e8f0;
}
/* Cards */
.StatCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
""")

    def apply_theme(self, theme_name: str = None):
        """Applies the specified theme. If None, applies the saved theme."""
        if theme_name is None:
            theme_name = self.current_theme

        path = f"styles/{theme_name}_theme.qss"
        try:
            with open(path, "r") as f:
                self.app.setStyleSheet(f.read())
            
            self.current_theme = theme_name
            self.settings.set("theme", theme_name)
            self.theme_changed.emit(theme_name)
            app_logger.info(f"Applied theme: {theme_name}")
        except Exception as e:
            app_logger.error(f"Failed to apply theme {theme_name}: {e}")

    def toggle_theme(self):
        """Switches between dark and light themes."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)
