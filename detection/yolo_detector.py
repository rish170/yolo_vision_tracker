import time
import numpy as np
from ultralytics import YOLO
from dataclasses import dataclass
from typing import List, Tuple, Optional
from core.logger import app_logger

@dataclass
class DetectionResult:
    bbox: Tuple[float, float, float, float] # [left, top, right, bottom]
    confidence: float
    class_id: int
    class_name: str
    mask: Optional[np.ndarray] = None # Binary mask if using segmentation
    mask_polygon: Optional[List[Tuple[int, int]]] = None # Polygon points

class YOLODetector:
    """
    Wrapper for Ultralytics YOLOv8 for detection and segmentation.
    """
    def __init__(self, model_name="yolov8n-seg.pt"):
        self.model_name = model_name
        self.model = None
        self.is_segmentation = "-seg" in model_name
        self.load_model(model_name)

    def load_model(self, model_name):
        app_logger.info(f"Loading YOLO model: {model_name}")
        self.model_name = model_name
        self.is_segmentation = "-seg" in model_name
        try:
            self.model = YOLO(model_name)
            app_logger.info("Model loaded successfully.")
        except Exception as e:
            app_logger.error(f"Failed to load model {model_name}: {e}")

    def detect(self, frame, conf_threshold=0.5, enabled_classes=None):
        """
        Runs inference on a single frame.
        enabled_classes: List of class IDs to keep. If None, keep all.
        """
        if self.model is None:
            return []

        results = self.model.predict(source=frame, conf=conf_threshold, verbose=False, stream=False)
        detections = []

        for result in results:
            boxes = result.boxes
            masks = result.masks if self.is_segmentation else None

            if boxes is None:
                continue

            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                if enabled_classes is not None and cls_id not in enabled_classes:
                    continue

                conf = boxes.conf[i].item()
                # YOLO returns [x_center, y_center, width, height] by default, 
                # but we can get xyxy
                xyxy = boxes.xyxy[i].cpu().numpy()
                bbox = (xyxy[0], xyxy[1], xyxy[2], xyxy[3])
                class_name = self.model.names[cls_id]

                det = DetectionResult(
                    bbox=bbox,
                    confidence=conf,
                    class_id=cls_id,
                    class_name=class_name
                )

                # Process masks if available
                if masks is not None and masks.data is not None:
                    # Accessing the specific mask for this bounding box
                    # Masks are in xy format (polygons)
                    if i < len(masks.xy):
                        polygon = masks.xy[i]
                        det.mask_polygon = [(int(p[0]), int(p[1])) for p in polygon]

                detections.append(det)

        return detections

    def benchmark(self, frame_shape=(640, 640, 3)):
        """Runs a simulated benchmark to estimate FPS and latency."""
        app_logger.info(f"Running benchmark for {self.model_name}...")
        if self.model is None:
            return {"error": "Model not loaded"}

        dummy_frame = np.zeros(frame_shape, dtype=np.uint8)
        
        # Warmup
        for _ in range(3):
            self.model.predict(dummy_frame, verbose=False)

        # Test
        iterations = 10
        start_time = time.time()
        for _ in range(iterations):
            self.model.predict(dummy_frame, verbose=False)
        end_time = time.time()

        avg_time = (end_time - start_time) / iterations
        est_fps = 1.0 / avg_time if avg_time > 0 else 0

        result = {
            "model_name": self.model_name,
            "avg_inference_time_ms": round(avg_time * 1000, 2),
            "estimated_fps": round(est_fps, 1),
            "device": self.model.device.type
        }
        app_logger.info(f"Benchmark result: {result}")
        return result
