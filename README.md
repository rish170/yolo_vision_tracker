# VisionTrack-AI

An enterprise-grade, real-time object detection and tracking desktop application. Built with PyQt6, YOLOv8 (Segmentation), and DeepSORT, this software provides professional surveillance analytics including Multi-ROI intrusion detection, crowd counting, speed estimation, and dwell-time calculation.

---

## 🌟 Key Features
- **Real-Time AI Pipeline**: Processes video feeds with YOLOv8 (Segmentation) and DeepSORT for seamless object tracking across frames.
- **Hardware Acceleration**: Deep integration with PyTorch and CUDA for maximum performance on NVIDIA GPUs (e.g., RTX 3050), with automatic fallback to CPU.
- **Intelligent Analytics**:
  - **Speed Estimation**: Calculates relative (px/s) or real-world (km/h, mph) velocity.
  - **Dwell Time**: Tracks exactly how long objects remain in the frame.
- **Alert & Rule Engine**: Configurable thresholds (e.g., Crowd Counting) and custom polygonal tripwires/Regions of Interest (ROIs).
- **SQLite Database**: Persistently logs system events, alerts, ROI configurations, and object trajectories.
- **Enterprise UI**: Sleek, high-performance GUI built with PyQt6 featuring live hardware monitoring (CPU/GPU/RAM), dynamic settings panels, event logs, and multiple dark/light themes.

---

## 💻 Hardware Requirements
To run the AI models at a smooth frame rate, a dedicated GPU is highly recommended:
- **GPU**: NVIDIA Graphics Card with CUDA support (Tested on NVIDIA GeForce RTX 3050 Laptop GPU).
- **RAM**: Minimum 8GB (16GB recommended).
- **OS**: Windows 10/11 (Linux and macOS supported with minor path modifications).
- **CPU**: Modern multi-core processor (required if running in CPU-fallback mode).

---

## 🚀 Installation & Setup Guide

To implement and run this software on another system, follow these steps exactly:

### 1. Install Python
Ensure **Python 3.12.x** is installed on your system. 
- During the Windows installation, ensure you check the box that says **"Add Python to PATH"**.

### 2. Create a Virtual Environment (venv)
A virtual environment isolates the project's dependencies from the rest of your system.
Open your terminal (PowerShell or Command Prompt), navigate to the project directory, and run:
```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment
Before installing packages or running the app, you must activate the environment:
**Windows (PowerShell):**
```powershell
.\venv\Scripts\activate
```
*(You should see `(venv)` appear at the start of your terminal line).*

### 4. Install Dependencies
With the environment activated, install all required packages using pip:
```powershell
pip install -r requirements.txt
```
> **Note on PyTorch & CUDA**: The `requirements.txt` is configured to download PyTorch with `cu118` (CUDA 11.8) support to ensure proper NVIDIA GPU integration. 

### 5. Windows Security / Antivirus Exclusion (CRITICAL FOR GPU)
Windows Defender or third-party antivirus software sometimes blocks heavily optimized math libraries (specifically `c10_cuda.dll` inside PyTorch) from loading. 
- If the application crashes on startup or fails to load CUDA, **add the project folder (or the `venv` folder) to your Antivirus Exclusions list**.

### 6. Run the Application
Finally, launch the app:
```powershell
python main.py
```

---

## 📂 Folder Structure

The project is strictly modular to support enterprise scalability:

```text
yolo_vision_tracker/
│
├── main.py                          # Entry point; initializes the UI and core services.
├── requirements.txt                 # Project dependencies.
├── README.md                        # This documentation file.
│
├── core/
│   ├── dependency_checker.py        # Verifies CUDA, packages, and downloads missing models on startup.
│   ├── hardware_monitor.py          # Uses psutil/GPUtil to read live CPU/GPU/RAM usage.
│   ├── logger.py                    # Manages file-based rotating logs.
│   └── session_recovery.py          # Handles unexpected crashes and session state.
│
├── analytics/
│   ├── alert_engine.py              # Evaluates ROIs and thresholds, triggering DB events.
│   ├── dwell_time.py                # Calculates object presence duration.
│   └── speed_estimator.py           # Smooths frame-to-frame displacement for velocity.
│
├── database/
│   ├── db_manager.py                # Thread-safe SQLite manager creating schema/tables.
│   └── visiontrack.db               # (Generated) The active SQLite database.
│
├── detection/
│   └── yolo_detector.py             # Wrapper for Ultralytics YOLOv8 inference.
│
├── tracking/
│   └── deepsort_tracker.py          # Handles ID assignment across sequential frames.
│
├── services/
│   ├── event_logger.py              # Bridges the Alert Engine and the Database.
│   ├── settings_manager.py          # Thread-safe JSON configuration persistence.
│   ├── theme_manager.py             # Generates and applies QSS stylesheets.
│   └── video_worker.py              # The Core QThread! Runs the OpenCV -> YOLO -> DeepSORT loop.
│
├── ui/
│   ├── main_window.py               # The primary PyQt6 shell and routing logic.
│   ├── video_widget.py              # Renders the live frame, HUD, trails, and bounding boxes.
│   ├── perf_monitor_panel.py        # Real-time hardware graphs.
│   └── widgets/
│       ├── events_log_panel.py      # Queries the DB to display historical alerts.
│       ├── settings_panel.py        # Configuration UI for AI, general, and analytics settings.
│       └── multi_roi_editor.py      # UI for drawing and managing transparent polygons.
│
└── config/
    └── settings.json                # (Generated) User preferences saved from the UI.
```

---

## ⚙️ How It Works (System Workflow)

1. **Initialization (`main.py`)**: 
   The app checks for CUDA hardware. It then initializes the SQLite database, loads saved user preferences, and launches the PyQt6 GUI.
2. **The Processing Thread (`VideoWorker`)**:
   Because AI inference is heavy, it runs on a separate background thread (`QThread`) so the UI never freezes.
   - **Capture**: OpenCV grabs a frame from the webcam (or IP stream).
   - **Detect**: The frame is passed to `YOLODetector`, which returns bounding boxes, segmentation masks, and class names (e.g., "Person", "Car").
   - **Track**: `DeepSORTTracker` analyzes the boxes against previous frames to assign a persistent ID (e.g., Person #1, Person #2).
   - **Analyze**: `SpeedEstimator` and `DwellTimeCalculator` measure object metrics. `AlertEngine` checks if any bounding boxes overlap user-drawn ROIs, or if crowd limits are exceeded.
   - **Log**: Events and trajectories are written to SQLite using `DatabaseManager`.
3. **The Rendering Thread (`VideoWidget`)**:
   The processed frame, along with all tracking data, is sent back to the main GUI thread. The `VideoWidget` uses `QPainter` to draw the video image, bounding boxes, transparent masks, movement trails, and the HUD on your screen at 30-60 FPS.

---

## 📚 Terminology & Settings Glossary

### General
- **Camera Index**: The numeric ID assigned by Windows/Linux to your connected cameras. `0` is typically your default built-in webcam. If you plug in a secondary USB camera, it will likely be `1`.
- **FPS Limit**: The maximum Frames Per Second the application will attempt to process. Lowering this (e.g., to 30) can drastically reduce GPU/CPU heat and power consumption if you don't need 60+ FPS processing.

### AI Models
- **YOLO Model**: The specific neural network weights used. Standard models (`yolov8n.pt`) draw bounding boxes. Segmentation models (`yolov8n-seg.pt`) are slightly heavier but map the exact outline of objects.
- **Confidence Threshold**: A decimal value (e.g., `0.50`). The AI must be at least 50% sure it is looking at an object before it tracks it. Higher values reduce "ghost" detections but might miss obscured objects.
- **Segmentation Masks**: When enabled alongside a `-seg` model, the app renders a translucent, colored polygon perfectly hugging the detected object.
- **Enabled Classes**: A comma-separated list of COCO dataset IDs. It tells the AI which objects to care about. Common IDs: `0` (Person), `1` (Bicycle), `2` (Car), `3` (Motorcycle), `5` (Bus), `7` (Truck).

### Analytics
- **Speed Mode**: How velocity is reported. 
  - *Relative*: Outputs purely in pixels-per-second (`px/s`). Works instantly without calibration.
  - *Real-world*: Attempts to convert pixel displacement into `km/h` using the calibration ratio below.
- **Pixels per Meter**: A real-world calibration constant. If an object moves across 100 pixels on your screen, and you know that physical space is exactly 1 meter wide, your ratio is `100`. This is required for accurate km/h estimation.
- **Visuals (Show Movement Trails)**: Toggles the fading colored lines drawn behind moving objects that visualize their recent path.
- **Crowd Threshold Limit**: The maximum number of specific objects (e.g., people) allowed in the camera frame simultaneously. If the active count exceeds this number, the Alert Engine triggers a `WARNING` or `CRITICAL` event and logs it to the database.
