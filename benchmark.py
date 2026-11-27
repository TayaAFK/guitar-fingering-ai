"""Замер времени + визуализация + JSON:
python benchmark.py clip1.mp4 clip2.mp4 [--fps-step 2] [--head-side right] [--thin-side bottom]"""
import argparse
import json
import time
from pathlib import Path

import cv2

from vision.processor import analyze_video

ap = argparse.ArgumentParser()
ap.add_argument("videos", nargs="+")
ap.add_argument("--fps-step", type=int, default=2)
ap.add_argument("--head-side", default="left", choices=["left", "right"])
ap.add_argument("--frets", type=int, default=12, help="сколько ладов видно между u=0 и u=1 (12 по ТЗ; ~20 если в рамке весь гриф)")
ap.add_argument("--thin-side", default=None, choices=["top", "bottom"], help="по умолчанию выводится из --head-side")
args = ap.parse_args()

for v in args.videos:
    cap = cv2.VideoCapture(v)
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30.0)
    cap.release()
    out_video = Path("data") / f"{Path(v).stem}_annotated.mp4"
    out_json = Path("data") / f"{Path(v).stem}_result.json"
    t0 = time.perf_counter()
    res = analyze_video(v, fps_step=args.fps_step, annotated_path=str(out_video),
                        head_side=args.head_side, thin_side=args.thin_side, visible_frets=args.frets)
    dt = time.perf_counter() - t0
    out_json.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    n = len(res["frames"]) or 1
    print(f"{Path(v).name}: видео {dur:.1f} c, обработка {dt:.1f} c (x{dt / max(dur, 1e-6):.2f} от длины), "
          f"кадров {len(res['frames'])}, гриф {sum(f['neck'] for f in res['frames']) / n:.0%}, "
          f"рука {sum(f['hand'] for f in res['frames']) / n:.0%}\n  видео: {out_video}\n  json:  {out_json}")
