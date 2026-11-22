import csv, os

DATA = "data"
ok = True

with open(os.path.join(DATA, "meta.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row.get("пригодна", "").strip().lower() not in ("да", "yes", "1"):
            continue
        v = os.path.join(DATA, "videos", row["имя файла"])
        m = os.path.join(DATA, "midi", row["имя эталонного MIDI"])
        for p in (v, m):
            if not os.path.exists(p):
                print("НЕТ:", p)
                ok = False

print("Все пригодные пары на месте" if ok else "Есть пропуски")