"""
CCPD2019 veri setinden stratified ornek toplama.

Her alt kategoriden orantili ornek alarak 25,000 goruntu seti olusturur.
Bu yaklasim tek kategoriden cok fazla ornek almak yerine cesitliligi garanti eder.

Alt kategoriler ve ozellikleri:
  ccpd_base     : Normal kosullar (ana veri)
  ccpd_blur     : Bulanik goruntular (hizli arac, odak sorunu)
  ccpd_challenge: Zorlu kosullar (parlama, rotasyon, vs.)
  ccpd_db       : Karanlik / cok parlak
  ccpd_fn       : Cok yakin / cok uzak mesafe
  ccpd_np       : Standart disi plakalar
  ccpd_rotate   : Dondurulen plakalar
  ccpd_tilt     : Egilmis plakalar (perspektif)
  ccpd_weather  : Hava kosullari (yagmur, sis, kar)

Kullanim:
  python scripts/01_prepare_ccpd_sample.py
  python scripts/01_prepare_ccpd_sample.py --total 30000
"""

from pathlib import Path
import argparse
import random
import shutil


# Her kategoriden alinacak MAKSIMUM goruntu sayisi
# Toplam hedef ~25,000 goruntu (kesintisiz cesitlilik)
CATEGORY_QUOTAS = {
    "ccpd_base":      10000,   # Normal kosullar - en buyuk pay
    "ccpd_challenge": 5000,    # Zorlu kosullar - kritik
    "ccpd_tilt":      3000,    # Egilmis plakalar
    "ccpd_blur":      2500,    # Bulanik
    "ccpd_fn":        2000,    # Yakin/uzak
    "ccpd_db":        1000,    # Karanlik/parlak
    "ccpd_rotate":    1000,    # Dondurulen
    "ccpd_weather":   500,     # Hava kosullari
    "ccpd_np":        300,     # Standart disi (az ornek)
}


def collect_images(directory: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png"}
    return [p for p in directory.iterdir() if p.suffix.lower() in exts]


def main():
    parser = argparse.ArgumentParser(
        description="CCPD2019 veri setinden stratified ornek toplama."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/raw/ccpd/CCPD2019"),
        help="CCPD2019 ana klasoru (alt kategoriler icinde)",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("data/interim/ccpd_sample_v2/images"),
        help="Ornek gorsel hedef klasoru",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=25000,
        help="Hedef toplam goruntu sayisi",
    )
    parser.add_argument("--seed", type=int, default=42, help="Rastgelelik tohumu")
    args = parser.parse_args()

    if not args.source.exists():
        raise FileNotFoundError(f"CCPD2019 kaynak klasoru bulunamadi: {args.source}")

    args.dest.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)

    # Hedef toplam sayisina gore kotlari olcekle
    total_quota = sum(CATEGORY_QUOTAS.values())
    scale = args.total / total_quota

    total_copied = 0
    category_stats = {}

    for category, quota in CATEGORY_QUOTAS.items():
        cat_dir = args.source / category
        if not cat_dir.exists():
            print(f"[UYARI] Kategori klasoru bulunamadi, atlandı: {cat_dir}")
            continue

        images = collect_images(cat_dir)
        if not images:
            print(f"[UYARI] Kategori bos, atlandı: {category}")
            continue

        # Olceklenmis kota (min: mevcut goruntu sayisi)
        scaled_quota = min(int(quota * scale), len(images))
        selected = random.sample(images, scaled_quota)

        for img in selected:
            # Kategori oneki ekle (isim catismalarini onler)
            dest_name = f"{category}_{img.name}"
            shutil.copy2(img, args.dest / dest_name)

        category_stats[category] = scaled_quota
        total_copied += scaled_quota
        print(f"  [{category:20s}] {scaled_quota:5d} goruntu alindi (mevcut: {len(images):6d})")

    print(f"\n[OK] Toplam {total_copied} goruntu kopyalandi -> {args.dest}")
    print("\nKategori dagilimi:")
    for cat, count in category_stats.items():
        bar = "#" * (count // 250)
        print(f"  {cat:20s}: {bar} {count}")


if __name__ == "__main__":
    main()
