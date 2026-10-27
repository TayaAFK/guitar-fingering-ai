import json
import cv2
import mediapipe as mp
from vision.detector import GuitarVisionDetector

def process_video(video_path: str, output_json_path: str, output_video_path: str = "output_annotated.mp4") -> None:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Ошибка: не удалось открыть файл {video_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    detector = GuitarVisionDetector()
    json_data = {
        "video_name": video_path.split("/")[-1],
        "fps": fps,
        "frames": []
    }

    frame_count = 0
    last_timestamp_ms = -1

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        timestamp_ms = int((frame_count - 1) * 1000.0 / fps)
        if timestamp_ms <= last_timestamp_ms:
            timestamp_ms = last_timestamp_ms + 1
        last_timestamp_ms = timestamp_ms

        force_update = (frame_count % 15 == 0)
        neck_line = detector.detect_neck_by_frets(frame, force_update=force_update)

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = detector.detector.detect_for_video(mp_image, timestamp_ms)

        best_hand = detector.filter_fretboard_hand(detection_result)

        hand_detected = False
        fingers_dict = {}

        if best_hand is not None:
            hand_detected = True
            tip_indices = {
                "index_tip": 8,
                "middle_tip": 12,
                "ring_tip": 16,
                "pinky_tip": 20
            }
            
            for name, idx in tip_indices.items():
                lm = best_hand[idx]
                px, py = int(lm.x * width), int(lm.y * height)
                u, v = detector.project_to_uv((px, py), neck_line)
                fingers_dict[name] = {"u": u, "v": v}

                cv2.circle(frame, (px, py), 6, (255, 0, 0), -1)
                cv2.putText(frame, name.split("_")[0], (px + 5, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        cv2.line(frame, (neck_line[0], neck_line[1]), (neck_line[2], neck_line[3]), (0, 255, 0), 3)

        out.write(frame)

        json_data["frames"].append({
            "frame_id": frame_count,
            "timestamp_ms": timestamp_ms,
            "neck_detected": True,
            "hand_detected": hand_detected,
            "fingers": fingers_dict if hand_detected else None
        })

    cap.release()
    out.release()

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"Обработка завершена. JSON сохранен в {output_json_path}, видео в {output_video_path}")