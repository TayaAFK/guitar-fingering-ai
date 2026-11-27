from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from vision.neck import (Neck, fit_visible_frets, fret_conf_from_peaks, fret_from_u,
                         fret_peaks, neck_from_quad, string_from_v)

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = ROOT / "data" / "hand_landmarker.task"
DEFAULT_NECK_MODEL_PATH = ROOT / "models" / "neck.pt"      # веса YOLO-seg (результат train/train_yolo.py)
FINGER_TIPS = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}


def _dist_point_segment(p, a, b) -> float:
    ab = b - a
    t = float((p - a) @ ab) / max(float(ab @ ab), 1e-6)
    return float(np.linalg.norm(p - (a + min(max(t, 0.0), 1.0) * ab)))


class GuitarVisionDetector:
    def __init__(self, model_path=None, head_side: str = "left", thin_side=None,
                 max_hand_dist: float = 0.5, neck_hold: int = 4, min_tips_on_neck: int = 3,
                 neck_model_path=None, visible_frets: int = 12):
        """head_side: где головка грифа на кадре ('left' для MVP).
        thin_side: на какой стороне кадра тонкая струна №1 ('top' при головке слева
                   и виде «глазами гитариста»; поменять на 'bottom', если на видео наоборот).
        max_hand_dist: макс. расстояние центра руки до оси грифа в долях длины грифа.
        neck_hold: сколько неудачных обновлений подряд держим старый гриф."""
        model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not model_path.exists():
            raise FileNotFoundError(f"Нет модели {model_path}. Скачайте: {MODEL_URL}")
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.head_side = head_side
        # сторона тонкой струны выводится из положения головки (гитарист-правша):
        # головка слева -> тонкая сверху, головка справа -> снизу
        self.thin_side = thin_side or ("top" if head_side == "left" else "bottom")
        self.max_hand_dist, self.neck_hold = max_hand_dist, neck_hold
        self.min_tips_on_neck = min_tips_on_neck
        self.visible_frets = visible_frets   # сколько ладов видно между u=0 и u=1
        self.neck: Optional[Neck] = None
        self._misses = 0
        self.last_quad = None
        self._last_center = None           # центр зажимающей руки на прошлом выборе (для непрерывности)
        self._hand_on_neck = False         # была ли рука на грифе в прошлом кадре
        self._rejects = 0                  # сколько подряд новых контуров отброшено проверкой
        neck_model_path = Path(neck_model_path) if neck_model_path else DEFAULT_NECK_MODEL_PATH
        if not neck_model_path.exists():
            raise FileNotFoundError(f"Нет модели грифа {neck_model_path}. Обучите: python train/train_yolo.py")
        from vision.yolo_neck import YoloNeckDetector
        self.yolo = YoloNeckDetector(neck_model_path)

    def close(self):
        self.detector.close()

    # ---- гриф ----
    def estimate_visible_frets(self, frames_bgr) -> int:
        """Число ладов на весь ролик: голосование по кадрам-пробам. Кадры с рукой и шумные
        дают разброс, поэтому побеждает значение, которое чаще всего подтверждается подгонкой."""
        votes = []
        for frame in frames_bgr:
            det = self.yolo.detect(frame)
            if det is None:
                continue
            quad, yolo_conf = det
            neck = neck_from_quad(quad, self.head_side, conf=yolo_conf, visible_frets=self.visible_frets)
            if neck is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            n_fit, err = fit_visible_frets(fret_peaks(gray, neck), self.visible_frets)
            if err < 4.0:
                votes.append(n_fit)
        if not votes:
            return self.visible_frets
        return Counter(votes).most_common(1)[0][0]

    def _plausible(self, new: Neck, max_move: float = 0.1, max_len_change: float = 0.25,
                   max_width_change: float = 0.4) -> bool:
        """Новый гриф не должен резко сдвинуться, вытянуться или раздуться на одном конце
        относительно текущего (в долях длины грифа/относительной ширины)."""
        old = self.neck
        if old is None:
            return True
        L = max(old.length, 1e-6)
        move = max(np.linalg.norm(new.p0 - old.p0), np.linalg.norm(new.p1 - old.p1)) / L
        len_change = abs(new.length - old.length) / L
        w_change = max(abs(new.w0 - old.w0) / max(old.w0, 1.0), abs(new.w1 - old.w1) / max(old.w1, 1.0))
        return move <= max_move and len_change <= max_len_change and w_change <= max_width_change

    def update_neck(self, frame_bgr, force: bool = False) -> Optional[Neck]:
        if not force:
            return self.neck
        det = self.yolo.detect(frame_bgr)
        found = None
        self.last_quad = None
        if det is not None:
            quad, yolo_conf = det
            self.last_quad = quad
            found = neck_from_quad(quad, self.head_side, conf=yolo_conf, visible_frets=self.visible_frets)
        busy = self._hand_on_neck                         # рука на грифе: маска и лады менее надёжны
        if found is not None and self.neck is not None and not self._plausible(found, max_move=0.06 if busy else 0.1):
            self._rejects += 1
            if busy and self._rejects <= 1:
                return self.neck                          # рука на грифе, скачок может быть из-за неё: держим
            self.neck = None                              # без руки или повторный скачок (зум/камера): пересобираем
        if found is not None:
            self._rejects = 0
        if found is not None:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            peaks = fret_peaks(gray, found)
            found.visible_frets = self.visible_frets      # число ладов задано на весь ролик
            found.fret_conf = fret_conf_from_peaks(len(peaks))
            self.neck = self.neck.blended(found) if self.neck is not None else found
            self._misses = 0
        else:
            self._misses += 1
            if self._misses > self.neck_hold:
                self.neck = None                      # -> neck: false
            elif self.neck is not None:
                self.neck = replace(self.neck, conf=self.neck.conf * 0.7)
        return self.neck

    # ---- рука: ближайшая к грифу, а не по метке Left/Right ----
    def select_fretting_hand(self, result, neck: Neck, width: int, height: int):
        """Зажимающая рука = та, у которой больше кончиков пальцев лежит на грифе
        (минимум min_tips_on_neck), при равенстве — ближайшая к оси грифа.
        Если такой руки нет (например, видна только щипковая) -> None."""
        best = None
        for lm in result.hand_landmarks or []:
            pts = np.array([[p.x * width, p.y * height] for p in lm])
            center = pts.mean(axis=0)
            ratio = _dist_point_segment(center, neck.p0, neck.p1) / max(neck.length, 1e-6)
            inside = 0
            for i in FINGER_TIPS.values():
                u, v = neck.project(pts[i], self.thin_side)
                inside += int(-0.1 <= u <= 1.1 and -0.3 <= v <= 1.3)   # нижние струны выходят за край грифа
            if inside < self.min_tips_on_neck or ratio > self.max_hand_dist:
                continue
            jump = 0.0 if self._last_center is None else \
                float(np.linalg.norm(center - self._last_center)) / max(neck.length, 1e-6)
            key = (-inside, jump)
            if best is None or key < best[0]:
                best = (key, pts, ratio)
        if best is None:
            return None
        self._last_center = best[1].mean(axis=0)
        return best[1], best[2]

    # ---- один кадр ----
    def analyze_frame(self, frame_bgr, timestamp_ms: int, update_neck: bool):
        """-> (запись кадра без поля t, debug-данные для рисования)."""
        neck = self.update_neck(frame_bgr, force=update_neck)
        rec = {"neck": neck is not None, "hand": False, "conf": 0.0, "fingers": None}
        dbg = {"neck": neck, "tips": {}, "quad": self.last_quad}
        if neck is None:
            return rec, dbg                              # без грифа руку не выбрать

        h, w = frame_bgr.shape[:2]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        sel = self.select_fretting_hand(result, neck, w, h)
        self._hand_on_neck = sel is not None
        if sel is None:
            return rec, dbg
        pts, ratio = sel

        fingers, inside = {}, 0
        for name, idx in FINGER_TIPS.items():
            u, v = neck.project(pts[idx], self.thin_side)
            inside += int(-0.1 <= u <= 1.1 and -0.2 <= v <= 1.2)
            fingers[name] = {"fret_est": round(fret_from_u(u, neck.visible_frets), 2),
                             "string_est": round(string_from_v(v), 2)}
            dbg["tips"][name] = (pts[idx], fingers[name])

        hand_factor = 1.0 - 0.5 * ratio / self.max_hand_dist
        inside_factor = 0.5 + 0.5 * inside / len(FINGER_TIPS)
        rec.update(hand=True, fingers=fingers,
                   conf=round(neck.conf * neck.fret_conf * hand_factor * inside_factor, 2))
        return rec, dbg
