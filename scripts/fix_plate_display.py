"""
Mevcut veritabanındaki plate_display değerlerini to_display() ile düzeltir.

Yapılan değişiklik:
    - plate_number → boşluksuz normalize form (dokunulmaz)
    - plate_display → boşluklu görüntü formatı (güncellenir)

Çalıştırma:
    python scripts/fix_plate_display.py
"""

import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "otopark.db"

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.postprocess.text_cleaner import PlateCleaner

cleaner = PlateCleaner()


def run() -> None:
    import sqlite3

    if not DB_PATH.exists():
        print(f"HATA: {DB_PATH} bulunamadi.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        "SELECT id, plate_number, plate_display FROM vehicles ORDER BY id"
    ).fetchall()

    fixed = []
    for vid, plate_number, plate_display in rows:
        # plate_number'dan boşluk varsa temizle (bozuk giriş güvencesi)
        clean_number = cleaner.clean(plate_number)
        expected_display = cleaner.to_display(clean_number)

        number_changed = clean_number != plate_number
        display_changed = expected_display != plate_display

        if number_changed or display_changed:
            fixed.append((vid, plate_number, clean_number, plate_display, expected_display))

    if not fixed:
        print("Tum plate_display degerleri zaten dogru. Degisiklik yapilmadi.")
        conn.close()
        return

    print(f"{len(fixed)} kayit guncelleniyor:\n")
    for vid, old_num, new_num, old_disp, new_disp in fixed:
        if old_num != new_num:
            print(f"  id={vid}  plate_number: {old_num!r} -> {new_num!r}")
        print(f"  id={vid}  plate_display: {old_disp!r} -> {new_disp!r}")

    confirm = input("\nOnayliyor musunuz? (e/h): ").strip().lower()
    if confirm != "e":
        print("Iptal edildi.")
        conn.close()
        return

    for vid, old_num, new_num, old_disp, new_disp in fixed:
        conn.execute(
            "UPDATE vehicles SET plate_number=?, plate_display=? WHERE id=?",
            (new_num, new_disp, vid),
        )
    conn.commit()
    conn.close()
    print(f"\n[OK] {len(fixed)} kayit guncellendi.")


if __name__ == "__main__":
    run()
