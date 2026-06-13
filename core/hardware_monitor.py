import psutil
import platform
from core.logger import app_logger

# Optional import for GPUtil
try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False

class HardwareMonitor:
    """
    Monitors system hardware (CPU, RAM, GPU) statistics.
    """
    
    @staticmethod
    def get_cpu_stats():
        """Returns CPU usage percentage and core count."""
        return {
            "percent": psutil.cpu_percent(interval=None),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True)
        }
        
    @staticmethod
    def get_ram_stats():
        """Returns RAM usage statistics in GB."""
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent
        }
        
    @staticmethod
    def get_gpu_stats():
        """Returns NVIDIA GPU statistics if available."""
        if not HAS_GPUTIL:
            return []
            
        try:
            gpus = GPUtil.getGPUs()
            gpu_list = []
            for gpu in gpus:
                gpu_list.append({
                    "id": gpu.id,
                    "name": gpu.name,
                    "load_percent": round(gpu.load * 100, 1),
                    "memory_total_mb": gpu.memoryTotal,
                    "memory_used_mb": gpu.memoryUsed,
                    "memory_percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 1) if gpu.memoryTotal > 0 else 0,
                    "temperature": gpu.temperature
                })
            return gpu_list
        except Exception as e:
            app_logger.error(f"Failed to get GPU stats: {e}")
            return []
            
    @staticmethod
    def get_system_info():
        """Returns static system information."""
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor()
        }
        
    @staticmethod
    def get_all_stats():
        """Retrieves a snapshot of all current hardware stats."""
        return {
            "cpu": HardwareMonitor.get_cpu_stats(),
            "ram": HardwareMonitor.get_ram_stats(),
            "gpu": HardwareMonitor.get_gpu_stats()
        }

if __name__ == "__main__":
    # Test initialization
    psutil.cpu_percent(interval=0.1)
    stats = HardwareMonitor.get_all_stats()
    print("Hardware Stats:", stats)
