import csv
import os
import time
import requests
import pretty_midi

API = "http://127.0.0.1:8000"
DATA = "data"

def get_midi_notes(midi_path):
    """Извлекает ноты (время и высоту тона) из MIDI файла."""
    try:
        pm = pretty_midi.PrettyMIDI(midi_path)
        return set((round(note.start, 1), note.pitch) for inst in pm.instruments for note in inst.notes)
    except Exception as e:
        print(f"  Ошибка чтения {midi_path}: {e}")
        return set()

def evaluate(pred_notes, true_notes):
    """Считает precision, recall, f1."""
    if not pred_notes or not true_notes:
        return 0.0, 0.0, 0.0
    tp = len(pred_notes.intersection(true_notes))
    precision = tp / len(pred_notes) if pred_notes else 0.0
    recall = tp / len(true_notes) if true_notes else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return round(precision, 3), round(recall, 3), round(f1, 3)

def process_video(video_path, midi_path):
    start_time = time.time()
    
    with open(video_path, "rb") as f:
        files = {"file": (os.path.basename(video_path), f, "video/mp4")}
        r = requests.post(f"{API}/upload", files=files)
    r.raise_for_status()
    task_id = r.json()["task_id"]
    
    while True:
        r = requests.get(f"{API}/status/{task_id}")
        r.raise_for_status()
        status = r.json().get("status", "").lower()
        if status in ["done", "completed", "success", "failed", "error"]:
            break
        time.sleep(1)
    
    r = requests.get(f"{API}/result/{task_id}")
    r.raise_for_status()
    
    temp_pred_midi = "data/temp_pred.mid"
    with open(temp_pred_midi, "wb") as f:
        f.write(r.content)
    
    proc_time = round(time.time() - start_time, 2)
    
    pred_notes = get_midi_notes(temp_pred_midi)
    true_notes = get_midi_notes(midi_path)
    precision, recall, f1 = evaluate(pred_notes, true_notes)
    
    if os.path.exists(temp_pred_midi):
        os.remove(temp_pred_midi)
        
    return precision, recall, f1, proc_time

def main():
    results = []
    with open(os.path.join(DATA, "meta.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("пригодна", "").strip().lower() not in ("да", "yes", "1"):
                continue
            
            video_name = row["имя файла"]
            midi_name = row["имя эталонного MIDI"]
            
            print(f"Обработка {video_name}...")
            p, r, f1, t = process_video(os.path.join(DATA, "videos", video_name), os.path.join(DATA, "midi", midi_name))
            
            results.append({
                "видео": video_name,
                "precision": p,
                "recall": r,
                "F1": f1,
                "время обработки, с": t
            })
    
    with open(os.path.join(DATA, "baseline.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["видео", "precision", "recall", "F1", "время обработки, с"])
        writer.writeheader()
        writer.writerows(results)
    
    print("\nТаблица сохранена в data/baseline.csv")

if __name__ == "__main__":
    main()