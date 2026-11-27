"""Геометрия грифа: модель, проекция точки в (лад, струна), построение грифа по четырёхугольнику.

Четырёхугольник (углы грифа) приходит от YOLO-seg (см. yolo_neck.py). Точки переводятся в
выпрямленный прямоугольник грифа гомографией (учитывает перспективу камеры), в нём лады и струны
лежат по формуле. Модуль не зависит от YOLO.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Optional

import cv2
import numpy as np

NUM_STRINGS = 6
RECT_W, RECT_H = 480, 64                                   # размер выпрямленного грифа
_RECT = np.float32([[0, 0], [RECT_W, 0], [RECT_W, RECT_H], [0, RECT_H]])


# ---------- формулы ----------
def _k(visible_frets: float) -> float:
    return 1.0 - 2.0 ** (-visible_frets / 12.0)


def fret_from_u(u: float, visible_frets: float = 12) -> float:
    """u in [0,1]: 0 = порожек, 1 = конец видимой части грифа, на котором visible_frets ладов.

    Положение лада n от порожка: d = L * (1 - 2^(-n/12)). Если видимая часть = N ладов,
    то u = (1 - 2^(-n/12)) / (1 - 2^(-N/12))  =>  n = -12 * log2(1 - u * (1 - 2^(-N/12))).
    """
    u = min(max(u, 0.0), 1.0)
    return max(0.0, -12.0 * math.log2(1.0 - u * _k(visible_frets)))


def u_from_fret(n, visible_frets: float = 12):
    """Обратная функция: где на оси (u) лежит лад n (число или массив)."""
    return (1.0 - 2.0 ** (-np.asarray(n, dtype=float) / 12.0)) / _k(visible_frets)


def string_from_v(v_thin: float) -> float:
    """v_thin in [0,1]: 0 = край у тонкой струны. Грифу делим на 6 равных полос.
    Центр струны i (1..6) = (i - 0.5) / 6, поэтому целое значение = центр струны."""
    s = v_thin * NUM_STRINGS + 0.5
    return min(max(s, 1.0), float(NUM_STRINGS))


def fret_conf_from_peaks(peaks: int) -> float:
    """Чем больше вертикальных «ладовых» контуров найдено, тем выше доверие к ладу."""
    if peaks < 4:
        return 0.25  # ладов не видно -> низкий conf
    return 0.6 + 0.4 * min(1.0, (peaks - 4) / 4.0)


# ---------- модель грифа ----------
@dataclass
class Neck:
    p0: np.ndarray        # середина порожка (u = 0)
    p1: np.ndarray        # середина дальнего конца (u = 1, лад visible_frets)
    w0: float             # ширина грифа у порожка, пиксели
    w1: float             # ширина грифа у дальнего конца, пиксели
    conf: float           # уверенность в самой линии грифа
    fret_conf: float = 1.0  # насколько видны лады
    visible_frets: int = 12  # сколько ладов умещается между u=0 и u=1

    @property
    def length(self) -> float:
        return float(np.hypot(*(self.p1 - self.p0)))

    def corners(self) -> np.ndarray:
        """Углы в порядке: порожек-верх, дальний-верх, дальний-низ, порожек-низ (как _RECT)."""
        d = self.p1 - self.p0
        n = np.array([-d[1], d[0]]) / max(self.length, 1e-6)
        if n[1] < 0:
            n = -n                                         # нормаль всегда вниз по изображению
        return np.array([self.p0 - n * self.w0 / 2, self.p1 - n * self.w1 / 2,
                         self.p1 + n * self.w1 / 2, self.p0 + n * self.w0 / 2], dtype=np.float32)

    def rect_matrix(self) -> np.ndarray:
        """Гомография: пиксели кадра -> выпрямленный гриф (RECT_W x RECT_H)."""
        return cv2.getPerspectiveTransform(self.corners(), _RECT)

    def to_rect(self, pts) -> np.ndarray:
        pts = np.asarray(pts, dtype=np.float32).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(pts, self.rect_matrix()).reshape(-1, 2)

    def from_rect(self, pts) -> np.ndarray:
        pts = np.asarray(pts, dtype=np.float32).reshape(-1, 1, 2)
        inv = cv2.getPerspectiveTransform(_RECT, self.corners())
        return cv2.perspectiveTransform(pts, inv).reshape(-1, 2)

    def project(self, pt, thin_side: str = "top"):
        """Точка в пикселях -> (u, v_thin) БЕЗ клампа.
        u: вдоль грифа (0 порожек, 1 дальний конец), учитывает перспективу.
        v_thin: поперёк (0 = край с тонкой струной, 1 = край с толстой)."""
        x, y = self.to_rect(np.asarray(pt, dtype=float).reshape(1, 2))[0]
        u = float(x) / RECT_W
        v_down = float(y) / RECT_H
        v_thin = v_down if thin_side == "top" else 1.0 - v_down
        return u, v_thin

    def string_lines(self, thin_side: str = "top"):
        """6 линий струн (для визуализации). Индекс 0 = струна №1 (тонкая)."""
        out = []
        for i in range(1, NUM_STRINGS + 1):
            v_thin = (i - 0.5) / NUM_STRINGS
            v_down = v_thin if thin_side == "top" else 1.0 - v_thin
            y = RECT_H * v_down
            out.append(tuple(self.from_rect([(0, y), (RECT_W, y)])))
        return out

    def fret_lines(self):
        """Линии ладов (для визуализации): [(n, (a, b))], n = 1..visible_frets."""
        out = []
        for n in range(1, self.visible_frets + 1):
            x = RECT_W * float(u_from_fret(n, self.visible_frets))
            out.append((n, tuple(self.from_rect([(x, 0), (x, RECT_H)]))))
        return out

    def blended(self, new: "Neck", alpha: float = 0.5) -> "Neck":
        """Сглаживание между обновлениями (EMA), чтобы линия не дрожала."""
        return replace(new,
                       p0=self.p0 * (1 - alpha) + new.p0 * alpha,
                       p1=self.p1 * (1 - alpha) + new.p1 * alpha,
                       w0=self.w0 * (1 - alpha) + new.w0 * alpha,
                       w1=self.w1 * (1 - alpha) + new.w1 * alpha)


# ---------- построение грифа из четырёхугольника ----------
def neck_from_quad(quad, head_side: str = "left", conf: float = 1.0,
                   visible_frets: int = 12) -> Optional[Neck]:
    """quad: 4 угла (x, y) в пикселях, по контуру (порядок циклический).

    Два коротких противоположных ребра — концы грифа (порожек и дальний конец),
    два длинных — края грифа. Порожек — тот конец, что ближе к головке грифа
    (head_side). Возвращает None, если четырёхугольник не похож на гриф."""
    q = np.asarray(quad, dtype=float).reshape(4, 2)
    edges = [((q[i] + q[(i + 1) % 4]) / 2, float(np.linalg.norm(q[i] - q[(i + 1) % 4])))
             for i in range(4)]
    ends = edges[0::2] if edges[0][1] + edges[2][1] < edges[1][1] + edges[3][1] else edges[1::2]
    direction = np.array([-1.0, 0.0]) if head_side == "left" else np.array([1.0, 0.0])
    (m_a, w_a), (m_b, w_b) = sorted(ends, key=lambda e: -float(e[0] @ direction))
    neck = Neck(p0=m_a, p1=m_b, w0=max(w_a, 1.0), w1=max(w_b, 1.0),
                conf=float(conf), visible_frets=visible_frets)
    if neck.length < 2.0 * max(neck.w0, neck.w1):    # слишком короткий/толстый -> не гриф
        return None
    return neck


# ---------- лады на выпрямленном грифе ----------
def fret_peaks(gray: np.ndarray, neck: Neck, min_gap: int = 10) -> np.ndarray:
    """x-координаты вертикальных штрихов ладов в выпрямленном грифе."""
    warped = cv2.warpPerspective(gray, neck.rect_matrix(), (RECT_W, RECT_H))
    prof = np.abs(cv2.Sobel(warped, cv2.CV_32F, 1, 0, ksize=3)).mean(axis=0)
    prof = np.convolve(prof, np.ones(5) / 5, mode="same")
    thr = max(prof.mean() + 0.5 * prof.std(), 30.0)   # абсолютный минимум: на плоском фоне пиков нет
    peaks, last = [], -100
    for i in range(1, len(prof) - 1):
        if prof[i] > thr and prof[i] >= prof[i - 1] and prof[i] > prof[i + 1] and i - last >= min_gap:
            peaks.append(float(i))
            last = i
    return np.array(peaks)


def fit_visible_frets(peaks: np.ndarray, default: int, n_min: int = 5, n_max: int = 24) -> tuple[int, float]:
    """Подбирает, сколько ладов умещается в выпрямленном грифе, по найденным проволокам.
    Ошибка двусторонняя: штраф и за найденные проволоки без лада, и за лады без проволоки.
    Возвращает (N, ошибка). Мало проволок -> (default, inf)."""
    if len(peaks) < 4:
        return default, math.inf
    best_n, best_err = default, math.inf
    for n_frets in range(n_min, n_max + 1):
        pred = RECT_W * u_from_fret(np.arange(1, n_frets + 1), n_frets)
        d = np.minimum(np.abs(peaks[:, None] - pred[None, :]), 6.0)
        err = 0.5 * float(d.min(axis=1).mean() + d.min(axis=0).mean())
        if err < best_err:
            best_n, best_err = n_frets, err
    return best_n, best_err
