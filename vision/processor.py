from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from vision.detector import GuitarVisionDetector


def _resize(frame, max_width: int):
    h, w = frame.shape[:2]
    if w <= max_width:
        return frame
    return cv2.resize(frame, (max_width, int(round(h * max_width / w))), interpolation=cv2.INTER_AREA)


def _sample_frames(cap, n: int, max_width: int) -> list:
    """n равномерных кадров по всему ролику (для голосования по числу ладов)."""
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        return []
    frames = []
    for idx in np.linspace(0, total - 1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(_resize(frame, max_width))
    return frames


def _pt(p):
    return int(round(p[0])), int(round(p[1]))


def _draw(frame, rec, dbg, t, thin_side):
    neck = dbg["neck"]
    if dbg.get("quad") is not None:                                # маска YOLO -> четырёхугольник
        cv2.polylines(frame, [np.round(dbg["quad"]).astype(np.int32)], True, (255, 128, 0), 1)
    if neck is not None:
        for n, (a, b) in neck.fret_lines():                        # где модель считает лады
            cv2.line(frame, _pt(a), _pt(b), (255, 255, 0), 1)
            if n % 2 == 1 or n == neck.visible_frets:
                cv2.putText(frame, str(n), (_pt(a)[0], _pt(a)[1] - 4), cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (255, 255, 0), 1)
        cv2.polylines(frame, [neck.corners().astype(np.int32)], True, (0, 255, 0), 2)
        for i, (a, b) in enumerate(neck.string_lines(thin_side), start=1):
            cv2.line(frame, _pt(a), _pt(b), (0, 215, 255) if i == 1 else (0, 140, 255), 1)
            cv2.putText(frame, str(i), _pt(b), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 215, 255), 1)
        cv2.circle(frame, _pt(neck.p0), 6, (0, 0, 255), -1)       # u = 0 (порожек)
        cv2.putText(frame, "u=0", _pt(neck.p0), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.circle(frame, _pt(neck.p1), 6, (255, 0, 255), -1)     # u = 1 (12-й лад)
        cv2.putText(frame, "u=1", _pt(neck.p1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    for name, (p, f) in dbg["tips"].items():
        cv2.circle(frame, _pt(p), 5, (255, 0, 0), -1)
        cv2.putText(frame, f"{name[0]} f{f['fret_est']} s{f['string_est']}",
                    (int(p[0]) + 6, int(p[1]) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    # панель с данными кадра (то, что попадёт в JSON)
    lines = [f"t={t:.2f}  neck={str(rec['neck']).lower()}  hand={str(rec['hand']).lower()}  conf={rec['conf']}"
             + (f"  frets={neck.visible_frets}" if neck is not None else "")]
    if rec["fingers"]:
        for name, f in rec["fingers"].items():
            lines.append(f"{name:<6} fret_est={f['fret_est']:<6} string_est={f['string_est']}")
    else:
        lines.append("fingers: null")
    panel = frame.copy()
    cv2.rectangle(panel, (0, 0), (430, 8 + 20 * len(lines)), (0, 0, 0), -1)
    cv2.addWeighted(panel, 0.6, frame, 0.4, 0, frame)
    for k, text in enumerate(lines):
        cv2.putText(frame, text, (8, 20 + 20 * k), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)


def analyze_video(path, fps_step: int = 2, annotated_path: Optional[str] = None, *,
                  model_path=None, head_side: str = "left", thin_side: Optional[str] = None,
                  max_width: int = 960, neck_model_path=None, visible_frets: int = 12) -> dict:
    """Возвращает {"video": ..., "fps": ..., "frames": [...]} по контракту 2.3.

    Каждый кадр: {"t", "neck", "hand", "conf", "fingers": {index|middle|ring|pinky:
    {"fret_est", "string_est"}}}. Нет грифа/руки -> флаг false, fingers = null.
    Видео с разметкой пишется только если задан annotated_path.
    fps_step: обрабатывать каждый N-й кадр. "fps" в ответе — fps исходного видео.
    """
    if fps_step < 1:
        raise ValueError("fps_step должен быть >= 1")
    path = Path(path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Не удалось открыть видео: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    detector = GuitarVisionDetector(model_path, head_side=head_side, thin_side=thin_side,
                                    neck_model_path=neck_model_path, visible_frets=visible_frets)
    neck_every = max(1, round(0.5 * fps / fps_step))   # искать гриф примерно раз в 0.5 с
    result = {"video": Path(path).name, "fps": round(fps, 3), "frames": []}
    probes = _sample_frames(cap, 30, max_width)
    if probes:
        detector.visible_frets = detector.estimate_visible_frets(probes)
        print(f"[vision] ладов на грифе (по всему ролику): {detector.visible_frets}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    writer = None
    idx, processed = -1, 0
    try:
        while cap.grab():                               # grab() пропускает ненужные кадры дёшево
            idx += 1
            if idx % fps_step:
                continue
            ok, frame = cap.retrieve()
            if not ok:
                break
            frame = _resize(frame, max_width)
            ts_ms = int(round(idx * 1000.0 / fps))      # строго возрастает -> требование MediaPipe
            rec, dbg = detector.analyze_frame(frame, ts_ms, update_neck=(processed % neck_every == 0))
            t = round(idx / fps, 2)
            result["frames"].append({"t": t, **rec})

            if annotated_path:
                if writer is None:
                    Path(annotated_path).parent.mkdir(parents=True, exist_ok=True)
                    h, w = frame.shape[:2]
                    writer = cv2.VideoWriter(str(annotated_path), cv2.VideoWriter_fourcc(*"mp4v"),
                                             fps / fps_step, (w, h))
                _draw(frame, rec, dbg, t, detector.thin_side)
                writer.write(frame)
            processed += 1
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        detector.close()
    return result


def process_video(video_path, output_json_path, output_video_path=None, fps_step: int = 2, **kw) -> dict:
    """Обёртка для обратной совместимости: analyze_video + запись JSON (папка создаётся сама)."""
    result = analyze_video(video_path, fps_step=fps_step, annotated_path=output_video_path, **kw)
    out = Path(output_json_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
