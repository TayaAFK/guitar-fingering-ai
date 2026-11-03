import pytest
import pretty_midi
import numpy as np
from eval import evaluate

def create_dummy_midi(filename, shift_seconds=0.0, pitch=60):
    """Создает тестовый MIDI с одной нотой."""
    pm = pretty_midi.PrettyMIDI()
    # Используем акустическую гитару (program 24)
    instrument = pretty_midi.Instrument(program=24)
    note = pretty_midi.Note(
        velocity=100, pitch=pitch, 
        start=1.0 + shift_seconds, end=2.0 + shift_seconds
    )
    instrument.notes.append(note)
    pm.instruments.append(instrument)
    pm.write(filename)

def test_perfect_match(tmp_path):
    """Тест 1: Эталон против самого себя -> F1 = 1.0"""
    ref_file = str(tmp_path / "ref.mid")
    create_dummy_midi(ref_file)
    
    p, r, f1, _ = evaluate(ref_file, ref_file)
    assert np.isclose(f1, 1.0), f"F1 должен быть 1.0, получен {f1}"

def test_shifted_time(tmp_path):
    """Тест 2: Сдвиг на 1 секунду -> F1 = 0.0 (так как допуск 50мс)"""
    ref_file = str(tmp_path / "ref.mid")
    est_file = str(tmp_path / "est.mid")
    create_dummy_midi(ref_file, shift_seconds=0.0)
    create_dummy_midi(est_file, shift_seconds=1.0)
    
    p, r, f1, _ = evaluate(ref_file, est_file)
    assert np.isclose(f1, 0.0), f"F1 должен быть 0.0, получен {f1}"