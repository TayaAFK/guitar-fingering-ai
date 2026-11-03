import argparse
import mir_eval
import numpy as np
import librosa
import pretty_midi

def load_midi_notes(midi_path):
    """Загружает ноты из MIDI: возвращает onset_times (сек) и midi_pitches."""
    pm = pretty_midi.PrettyMIDI(midi_path)
    onsets = []
    pitches = []
    for instrument in pm.instruments:
        for note in instrument.notes:
            onsets.append(note.start)
            pitches.append(note.pitch)
            
    if not onsets:
        return np.array([]), np.array([])
        
    onsets = np.array(onsets)
    pitches = np.array(pitches)
    sorted_idx = np.argsort(onsets)
    return onsets[sorted_idx], pitches[sorted_idx]

def evaluate(ref_path, est_path):
    """Сравнивает два MIDI файла и возвращает precision, recall, f1."""
    ref_onsets, ref_pitches = load_midi_notes(ref_path)
    est_onsets, est_pitches = load_midi_notes(est_path)

    # Переводим MIDI-ноты (например, 60) в частоты в Гц (261.6)
    ref_freqs = librosa.midi_to_hz(ref_pitches)
    est_freqs = librosa.midi_to_hz(est_pitches)

        # mir_eval требует двумерный массив (start, end)
    # Так как offset_ratio=None, end может быть любым (просто start + 0.1)
    ref_intervals = np.column_stack((ref_onsets, ref_onsets + 0.1))
    est_intervals = np.column_stack((est_onsets, est_onsets + 0.1))

    # Теперь передаем правильные интервалы
    scores = mir_eval.transcription.precision_recall_f1_overlap(
        ref_intervals, ref_freqs, 
        est_intervals, est_freqs, 
        onset_tolerance=0.05, 
        pitch_tolerance=0.5, 
        offset_ratio=None # длительности не сравниваем
    )
    return scores

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Оценка MIDI")
    parser.add_argument("--ref", required=True, help="Путь к эталонному MIDI")
    parser.add_argument("--est", required=True, help="Путь к проверяемому MIDI")
    args = parser.parse_args()

    p, r, f1, _ = evaluate(args.ref, args.est)
    
    print(f"Precision: {p:.4f}")
    print(f"Recall:    {r:.4f}")
    print(f"F1-score:  {f1:.4f}")