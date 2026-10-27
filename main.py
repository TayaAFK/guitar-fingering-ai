import cv2
import numpy as np
from vision.processor import process_video

process_video("data/gravity-falls.mp4", "data/output_result.json", "data/output_annotated.mp4")

import json
with open("output_result.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    print("\nПример данных из JSON (двадцатый кадр):")
    print(json.dumps(data["frames"][20], indent=2, ensure_ascii=False))