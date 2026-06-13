from typing import List, Dict, Any
from tracking.deepsort_tracker import TrackedObject
from services.event_logger import EventLogger
from core.logger import app_logger

class AlertEngine:
    """
    Evaluates tracked objects and ROIs against user-defined rules.
    Triggers events when conditions are met.
    """
    def __init__(self, event_logger: EventLogger):
        self.event_logger = event_logger
        self.rules = [] # List of rule definitions (dicts)
        
        # State tracking to avoid spamming alerts
        # rule_id -> {track_id: last_trigger_time}
        self.trigger_history = {} 

    def load_rules(self, rules: List[Dict]):
        """
        Loads alert rules.
        Example rule: 
        {
            "id": "rule_1",
            "type": "roi_intrusion",
            "roi_id": "some_uuid",
            "classes": ["person", "car"],
            "severity": "CRITICAL",
            "message": "{class_name} entered {roi_name}"
        }
        """
        self.rules = rules
        for r in self.rules:
            if r["id"] not in self.trigger_history:
                self.trigger_history[r["id"]] = {}
        app_logger.info(f"Loaded {len(self.rules)} alert rules.")

    def evaluate(self, tracks: List[TrackedObject], rois: Dict[str, Any], current_time: float):
        """
        Evaluates current frame data against rules.
        """
        for rule in self.rules:
            rule_id = rule["id"]
            
            if rule["type"] == "roi_intrusion":
                self._eval_roi_intrusion(rule, tracks, rois, current_time)
            elif rule["type"] == "count_threshold":
                self._eval_count_threshold(rule, tracks, current_time)

    def _eval_roi_intrusion(self, rule, tracks, rois, current_time):
        roi_id = rule.get("roi_id")
        if roi_id not in rois:
            return
            
        roi = rois[roi_id]
        if not roi["active"]:
            return
            
        import matplotlib.path as mpltPath
        # Build matplotlib path for point-in-polygon check
        poly_points = [(p.x(), p.y()) for p in roi["points"]]
        if len(poly_points) < 3:
            return
            
        path = mpltPath.Path(poly_points)
        
        for track in tracks:
            if rule.get("classes") and track.class_name not in rule["classes"]:
                continue
                
            l, t, r, b = track.bbox
            bbox_path = mpltPath.Path([(l, t), (r, t), (r, b), (l, b)])
            is_inside = path.intersects_path(bbox_path)
            
            if is_inside:
                # Check cooldown (e.g. alert once every 10 seconds per object)
                last_trigger = self.trigger_history[rule["id"]].get(track.track_id, 0)
                if current_time - last_trigger > 10.0: # 10s cooldown
                    msg = rule["message"].format(class_name=track.class_name, roi_name=roi["name"])
                    self.event_logger.log_event(rule["severity"], "ROI_INTRUSION", msg)
                    self.trigger_history[rule["id"]][track.track_id] = current_time

    def _eval_count_threshold(self, rule, tracks, current_time):
        target_class = rule.get("class", "person")
        threshold = rule.get("threshold", 10)
        
        count = sum(1 for t in tracks if t.class_name == target_class)
        
        if count >= threshold:
            last_trigger = self.trigger_history[rule["id"]].get("global", 0)
            if current_time - last_trigger > 30.0: # 30s cooldown for global counts
                msg = rule["message"].format(count=count)
                self.event_logger.log_event(rule["severity"], "COUNT_THRESHOLD", msg)
                self.trigger_history[rule["id"]]["global"] = current_time
