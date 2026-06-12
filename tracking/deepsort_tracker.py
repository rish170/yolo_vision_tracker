from deep_sort_realtime.deepsort_tracker import DeepSort
from core.logger import app_logger
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class TrackedObject:
    track_id: int
    bbox: Tuple[float, float, float, float] # [left, top, right, bottom]
    class_name: str
    confidence: float
    # We will let the trajectory manager handle the deep history, 
    # but keep a small trail for immediate UI rendering
    ui_trail: List[Tuple[int, int]] = None 
    mask_polygon: Optional[List[Tuple[int, int]]] = None

class DeepSORTTracker:
    """
    Wrapper for deep_sort_realtime for object tracking across frames.
    """
    def __init__(self, max_age=30, n_init=3, nn_budget=100):
        app_logger.info("Initializing DeepSORT tracker...")
        self.max_age = max_age
        self.n_init = n_init
        self.tracker = DeepSort(
            max_age=max_age, 
            n_init=n_init, 
            nn_budget=nn_budget,
            override_track_class=None,
            embedder="mobilenet", 
            half=True, 
            bgr=True
        )
        # Store recent trails for UI: {track_id: [(x, y), ...]}
        self.trails = {}
        self.max_trail_length = 30

    def update(self, detections, frame) -> List[TrackedObject]:
        """
        Updates the tracker with new detections.
        detections: List of DetectionResult from YOLODetector.
        frame: The current BGR frame.
        """
        # DeepSORT expects: [([left,top,w,h], confidence, detection_class)]
        bbs = []
        # We need a mapping to associate masks back to the tracks if needed
        det_mapping = {}

        for i, det in enumerate(detections):
            # Convert xyxy to ltwh
            l, t, r, b = det.bbox
            w = r - l
            h = b - t
            bbs.append(([l, t, w, h], det.confidence, det.class_name))
            det_mapping[i] = det # Store for mask recovery

        try:
            # Note: DeepSORT might filter out some detections, so the returned tracks
            # might not map 1:1 to input detections immediately.
            tracks = self.tracker.update_tracks(bbs, frame=frame)
        except Exception as e:
            app_logger.error(f"DeepSORT update error: {e}")
            return []

        tracked_objects = []

        for track in tracks:
            if not track.is_confirmed():
                continue

            try:
                track_id = int(track.track_id)
            except ValueError:
                track_id = hash(track.track_id) % 10000
            ltrb = track.to_ltrb() # left, top, right, bottom
            class_name = track.get_det_class()
            conf = track.get_det_conf()
            
            if conf is None:
                conf = 0.0

            # Calculate center point for trail
            center_x = int((ltrb[0] + ltrb[2]) / 2)
            center_y = int((ltrb[1] + ltrb[3]) / 2)

            # Update UI trail
            if track_id not in self.trails:
                self.trails[track_id] = []
            self.trails[track_id].append((center_x, center_y))
            
            if len(self.trails[track_id]) > self.max_trail_length:
                self.trails[track_id].pop(0)

            # Attempt to map back to original detection for the segmentation mask
            # This is a naive spatial match since DeepSORT doesn't return the original index easily
            best_mask = None
            best_iou = 0.0
            
            for det in detections:
                if det.class_name == class_name and det.mask_polygon is not None:
                    # Very rough IoU / center distance check could go here
                    # For simplicity in Phase 1, we map if centers are close
                    d_l, d_t, d_r, d_b = det.bbox
                    d_cx = (d_l + d_r) / 2
                    d_cy = (d_t + d_b) / 2
                    dist = ((center_x - d_cx)**2 + (center_y - d_cy)**2)**0.5
                    if dist < max((ltrb[2]-ltrb[0]), (ltrb[3]-ltrb[1])) * 0.5: # within box bounds
                        best_mask = det.mask_polygon
                        break

            tracked_objects.append(TrackedObject(
                track_id=track_id,
                bbox=(ltrb[0], ltrb[1], ltrb[2], ltrb[3]),
                class_name=class_name,
                confidence=conf,
                ui_trail=list(self.trails[track_id]),
                mask_polygon=best_mask
            ))

        return tracked_objects

    def reset(self):
        """Resets the tracker state (e.g., when switching video sources)."""
        app_logger.info("Resetting tracker state.")
        self.tracker.tracker.tracks = []
        self.trails.clear()
