from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt
from core.hardware_monitor import HardwareMonitor

class PerfMonitorPanel(QWidget):
    """
    Panel to display real-time hardware statistics (CPU, GPU, RAM).
    """
    def __init__(self):
        super().__init__()
        self._init_ui()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000) # Update every 1 second

    def _init_ui(self):
        self.setObjectName("AnalyticsPanel")
        self.setFixedWidth(250)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("Hardware Monitor")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.lbl_cpu = QLabel("CPU: --%")
        self.lbl_ram = QLabel("RAM: -- / -- GB")
        self.lbl_gpu = QLabel("GPU: Not Available")
        
        # Style like a StatCard
        for lbl in [self.lbl_cpu, self.lbl_ram, self.lbl_gpu]:
            lbl.setProperty("class", "StatCard")
            lbl.setStyleSheet("padding: 10px;")
            layout.addWidget(lbl)

    def update_stats(self):
        stats = HardwareMonitor.get_all_stats()
        
        cpu = stats.get("cpu", {})
        self.lbl_cpu.setText(f"CPU: {cpu.get('percent', 0)}% ({cpu.get('cores_physical', 0)} Cores)")
        
        ram = stats.get("ram", {})
        self.lbl_ram.setText(f"RAM: {ram.get('used_gb', 0)} / {ram.get('total_gb', 0)} GB ({ram.get('percent', 0)}%)")
        
        gpu_list = stats.get("gpu", [])
        if gpu_list:
            gpu = gpu_list[0] # Just show the first GPU for now
            self.lbl_gpu.setText(f"GPU: {gpu.get('name', 'Unknown')}\nLoad: {gpu.get('load_percent', 0)}%\nVRAM: {gpu.get('memory_percent', 0)}% ({gpu.get('temperature', 0)}°C)")
        else:
            self.lbl_gpu.setText("GPU: Not Detected/Supported")
