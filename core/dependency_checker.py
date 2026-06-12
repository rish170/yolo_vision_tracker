import importlib.util
import sys
from core.logger import app_logger

class DependencyChecker:
    """
    Checks for required dependencies and hardware capabilities on startup.
    """
    
    REQUIRED_PACKAGES = [
        "PyQt6", "cv2", "ultralytics", "deep_sort_realtime", 
        "numpy", "torch", "torchvision", "psutil", "GPUtil", 
        "pandas", "openpyxl", "reportlab"
    ]
    
    @staticmethod
    def check_packages():
        """Verifies that all required pip packages are installed."""
        missing = []
        for pkg in DependencyChecker.REQUIRED_PACKAGES:
            # Note: OpenCV is imported as cv2
            try:
                if importlib.util.find_spec(pkg) is None:
                    missing.append(pkg)
            except Exception as e:
                app_logger.error(f"Error checking package {pkg}: {e}")
                missing.append(pkg)
                
        if missing:
            app_logger.error(f"Missing required packages: {', '.join(missing)}")
            return False, missing
            
        app_logger.info("All required packages are installed.")
        return True, []

    @staticmethod
    def check_cuda():
        """Checks if CUDA is available via PyTorch."""
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                app_logger.info(f"CUDA is available. Device: {device_name}")
                return True, device_name
            else:
                app_logger.warning("CUDA is NOT available. Falling back to CPU.")
                return False, "CPU"
        except ImportError:
            app_logger.error("PyTorch is not installed. Cannot check CUDA.")
            return False, "Unknown"

    @staticmethod
    def run_all_checks():
        """Runs all startup checks."""
        packages_ok, missing = DependencyChecker.check_packages()
        cuda_ok, device = DependencyChecker.check_cuda()
        
        return {
            "packages_ok": packages_ok,
            "missing_packages": missing,
            "cuda_ok": cuda_ok,
            "device": device
        }

if __name__ == "__main__":
    results = DependencyChecker.run_all_checks()
    print("Startup Checks:", results)
