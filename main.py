"""Запуск: python main.py data/clip.mp4 --annotated data/clip_annotated.mp4"""
import argparse
import json
from pathlib import Path

from vision.processor import analyze_video

ROOT = Path(__file__).resolve().parent
OUTPUT_JSON = ROOT / "data" / "output_result.json"   # ОДИН путь и для записи, и для чтения


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", default=str(ROOT / "data" / "gravity-falls.mp4"))
    ap.add_argument("--fps-step", type=int, default=2)
    ap.add_argument("--annotated", default=None, help="путь для видео с разметкой (по умолчанию не пишется)")
    ap.add_argument("--head-side", default="left", choices=["left", "right"])
    ap.add_argument("--frets", type=int, default=12, help="сколько ладов видно между u=0 и u=1 (12 по ТЗ; ~20 если в рамке весь гриф)")
    ap.add_argument("--thin-side", default=None, choices=["top", "bottom"], help="по умолчанию выводится из --head-side")
    args = ap.parse_args()

    result = analyze_video(args.video, fps_step=args.fps_step, annotated_path=args.annotated,
                           head_side=args.head_side, thin_side=args.thin_side, visible_frets=args.frets)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    data = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))   # читаем тот же файл, что записали
    n = len(data["frames"]) or 1
    print(f"{data['video']}: кадров {len(data['frames'])}, "
          f"гриф найден {100 * sum(f['neck'] for f in data['frames']) / n:.0f}%, "
          f"рука {100 * sum(f['hand'] for f in data['frames']) / n:.0f}% -> {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
