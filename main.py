import sys
from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtGui import QPixmap, QColor, QFont
from PyQt6.QtCore import Qt, QTimer
from core.logger import app_logger
from core.dependency_checker import DependencyChecker
from database.db_manager import DatabaseManager
from services.theme_manager import ThemeManager
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 1. Show Splash Screen
    # Create a simple synthetic splash pixmap since we don't have an image asset yet
    splash_pix = QPixmap(600, 300)
    splash_pix.fill(QColor(10, 10, 15))
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.showMessage("VisionTrack-AI\nInitializing...", Qt.AlignmentFlag.AlignCenter, QColor.fromRgb(255, 255, 255))
    
    font = QFont("Segoe UI", 16, QFont.Weight.Bold)
    splash.setFont(font)
    splash.show()
    app.processEvents()
    
    try:
        # 2. Run Startup Validations
        splash.showMessage("Checking dependencies...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, QColor.fromRgb(255, 255, 255))
        app.processEvents()
        
        deps = DependencyChecker.run_all_checks()
        if not deps["packages_ok"]:
            app_logger.critical("Missing required packages. Exiting.")
            sys.exit(1)
            
        # 3. Initialize Database
        splash.showMessage("Initializing database...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, QColor.fromRgb(255, 255, 255))
        app.processEvents()
        db = DatabaseManager() # Initializes schema
        
        # 4. Setup Theme
        splash.showMessage("Loading UI...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, QColor.fromRgb(255, 255, 255))
        app.processEvents()
        theme_manager = ThemeManager(app)
        theme_manager.apply_theme()
        
        # 5. Launch Main Window
        window = MainWindow(theme_manager)
        window.show()
        splash.finish(window)
        
        app_logger.info("Application started successfully.")
        sys.exit(app.exec())
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        app_logger.critical(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
