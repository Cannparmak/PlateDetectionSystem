"""
Colab icin dataset'i zip'ler.

Cikti: outputs/yolo_plate_dataset_v2.zip (~1.6 GB)
Bu dosyayi Google Drive'a yukleyip Colab notebook ile egitim yapabilirsin.

Kullanim:
  python scripts/05_zip_for_colab.py
"""

import zipfile
import os
from pathlib import Path


def main():
    dataset_dir = Path("data/processed/yolo_plate_dataset_v2")
    output_zip = Path("outputs/yolo_plate_dataset_v2.zip")

    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset bulunamadi: {dataset_dir}\nOnce script 01-03'u calistir.")

    output_zip.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Zip olusturuluyor: {output_zip}")
    print(f"[INFO] Kaynak: {dataset_dir}")

    file_count = 0
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
        for file_path in sorted(dataset_dir.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(dataset_dir.parent)
                zf.write(file_path, arcname)
                file_count += 1
                if file_count % 2000 == 0:
                    size_mb = output_zip.stat().st_size / 1024**2
                    print(f"  {file_count} dosya islendi... ({size_mb:.0f} MB)")

    final_size = output_zip.stat().st_size / 1024**3
    print(f"\n[OK] Zip tamamlandi!")
    print(f"     Dosya: {output_zip.resolve()}")
    print(f"     Boyut: {final_size:.2f} GB")
    print(f"     Dosya sayisi: {file_count}")
    print("\n[SONRAKI ADIM]")
    print("  1. outputs/yolo_plate_dataset_v2.zip dosyasini Google Drive'a yukle")
    print("  2. Google Colab'i ac: https://colab.research.google.com")
    print("  3. docs/colab_egitim.ipynb notebook'unu yukle")
    print("  4. Calistir!")


if __name__ == "__main__":
    main()
