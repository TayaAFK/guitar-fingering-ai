import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class GuitarVisionDetector:
    def __init__(self, model_path: str = 'data/hand_landmarker.task'):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.cached_neck_line = None

    def filter_fretboard_hand(self, detection_result):
        if not detection_result.hand_landmarks:
            return None

        for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
            if idx < len(detection_result.handedness):
                label = detection_result.handedness[idx][0].display_name
                if label == 'Left':
                    return hand_landmarks
                    
        return detection_result.hand_landmarks[0]

    def detect_neck_by_frets(self, frame, force_update=False):
        if self.cached_neck_line is not None and not force_update:
            return self.cached_neck_line

        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edges = cv2.Canny(blurred, 30, 100)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=int(width * 0.4), maxLineGap=30)
        
        best_line = None
        max_len = 0

        if lines is not None:
            for line in lines:
                coords = line.flatten() if hasattr(line, 'flatten') else np.array(line).flatten()
                if len(coords) >= 4:
                    x1, y1, x2, y2 = coords[:4]
                    length = np.hypot(x2 - x1, y2 - y1)
                    angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi
                    if abs(angle) < 35 and length > max_len:
                        max_len = length
                        best_line = (int(x1), int(y1), int(x2), int(y2))

        if best_line is not None:
            self.cached_neck_line = best_line
        elif self.cached_neck_line is None:
            self.cached_neck_line = (int(width * 0.1), int(height * 0.6), int(width * 0.9), int(height * 0.35))

        return self.cached_neck_line

    def project_to_uv(self, fingertip, neck_line):
        x, y = fingertip
        x1, y1, x2, y2 = neck_line
        vx, vy = x2 - x1, y2 - y1
        length_sq = vx**2 + vy**2
        if length_sq == 0:
            return 0.0, 0.0
        
        u = float((x - x1) * vx + (y - y1) * vy) / length_sq
        
        length = np.sqrt(length_sq)
        nx, ny = -vy / length, vx / length
        fretboard_width_px = 120.0
        v = float((x - x1) * nx + (y - y1) * ny) / fretboard_width_px + 0.5
        
        return round(max(0.0, min(1.0, u)), 4), round(max(0.0, min(1.0, v)), 4)