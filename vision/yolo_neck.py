"""Детектор грифа на YOLO-seg (Ultralytics). Возвращает четырёхугольник углов грифа по маске."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np


def quad_from_contour(contour: np.ndarray) -> np.ndarray:
    """Контур маски -> 4 угла трапеции. Ось грифа — главная компонента точек маски; угол —
    точка контура, самая дальняя в одном из диагональных направлений (±ось ± поперечная).
    В отличие от minAreaRect сохраняет сужение концов грифа, которое даёт перспектива."""
    pts = contour.reshape(-1, 2).astype(float)
    rel = pts - pts.mean(axis=0)
    w, v = np.linalg.eigh(np.cov(rel.T))
    a = v[:, int(np.argmax(w))]
    n = np.array([-a[1], a[0]])
    return np.array([pts[int(np.argmax(rel @ (sa * a + sn * n)))]
                     for sa, sn in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


class YoloNeckDetector:
    def __init__(self, model_path, conf: float = 0.3, imgsz: int = 640, device=None):
        from ultralytics import YOLO          # импорт здесь, чтобы без YOLO проект тоже запускался
        self.model = YOLO(str(Path(model_path)))
        if self.model.task != "segment":
            raise ValueError(f"{model_path} — не сегментационная модель (task={self.model.task}). "
                             "Обучите её через train/train_yolo.py.")
        self.conf, self.imgsz, self.device = conf, imgsz, device

    def detect(self, frame_bgr) -> Optional[Tuple[np.ndarray, float]]:
        """-> ((4 угла (x, y) в пикселях кадра, по контуру), conf) для самой уверенной маски или None."""
        res = self.model.predict(frame_bgr, imgsz=self.imgsz, conf=self.conf,
                                 device=self.device, verbose=False)[0]
        if res.masks is None or len(res.masks) == 0:
            return None
        confs = res.boxes.conf.cpu().numpy()
        i = int(confs.argmax())
        contour = np.asarray(res.masks.xy[i], dtype=np.float32)   # полигон уже в координатах исходного кадра
        if len(contour) < 4:
            return None
        return quad_from_contour(contour), float(confs[i])
