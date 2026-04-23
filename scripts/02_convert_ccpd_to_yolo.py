"""
CCPD goruntularini YOLO label formatina cevirir.

CCPD dosya adi formatindan bounding box koordinatlarini cikarir ve
YOLO normalize formatina donusturur: class_id cx cy w h

CCPD dosya adi ornegi:
  ccpd_base_025834830316-91_92-308&516_419&547-...jpg
  Kisim [2] (indeks 2, '-' ile ayrilmis): "308&516_419&547"
  Bu: sol_ust_x & sol_ust_y _ sag_alt_x & sag_alt_y

Kullanim:
  python scripts/02_convert_ccpd_to_yolo.py
  python scripts/02_convert_ccpd_to_yolo.py --images data/interim/ccpd_sample_v2/images
                                              --labels data/interim/ccpd_sample_v2/labels
"""

from pathlib import Path
import argparse
import cv2


def parse_bbox_from_filename(filename: str) -> tuple[int, int, int, int]:
    """
    CCPD dosya adindan bounding box koordinatlarini cikarir.
    Dosya adi kategori oneki iceriyorsa (orn: ccpd_base_XXXX.jpg),
    CCPD bolumunu bulmak icin '-' ayracini kullanir.
    """
    stem = Path(filename).stem

    # Kategori oneki varsa kaldir (ornk: "ccpd_base_" veya "ccpd_blur_")
    # Gercek CCPD bolumu '-' karakterleri iceriyor
    dash_count = stem.count("-")
    if dash_count < 2:
        # Ek onekle basliyor olabilir, sonra gercek CCPD kismi geliyor
        # "ccpd_base_00205459770115-90_85-352&516_448&547-..." formatinda
        # Ilk '-' den baslayarak CCPD ana bolumunu al
        first_dash = stem.find("-")
        if first_dash == -1:
            raise ValueError(f"CCPD formatinda '-' bulunamadi: {filename}")
        stem = stem[first_dash + 1 :]  # Onekin sonrasini al

    parts = stem.split("-")
    if len(parts) < 3:
        raise ValueError(f"CCPD dosya adi formati gecersiz ({len(parts)} bolum): {filename}")

    bbox_part = parts[2]  # "352&516_448&547"
    p1, p2 = bbox_part.split("_")
    x1, y1 = map(int, p1.split("&"))
    x2, y2 = map(int, p2.split("&"))

    x_min, x_max = sorted((x1, x2))
    y_min, y_max = sorted((y1, y2))
    return x_min, y_min, x_max, y_max


def to_yolo_bbox(
    x1: int, y1: int, x2: int, y2: int, img_w: int, img_h: int
) -> tuple[float, float, float, float]:
    xc = ((x1 + x2) / 2.0) / img_w
    yc = ((y1 + y2) / 2.0) / img_h
    bw = (x2 - x1) / img_w
    bh = (y2 - y1) / img_h
    # Koordinatlari [0,1] araligina kes (floating point hatalarini onler)
    xc = max(0.0, min(1.0, xc))
    yc = max(0.0, min(1.0, yc))
    bw = max(0.001, min(1.0, bw))
    bh = max(0.001, min(1.0, bh))
    return xc, yc, bw, bh


def main():
    parser = argparse.ArgumentParser(
        description="CCPD goruntuleri YOLO label formatina cevirir."
    )
    parser.add_argument(
        "--images",
        type=Path,
        default=Path("data/interim/ccpd_sample_v2/images"),
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path("data/interim/ccpd_sample_v2/labels"),
    )
    args = parser.parse_args()

    args.labels.mkdir(parents=True, exist_ok=True)

    image_paths = sorted(
        p for p in args.images.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not image_paths:
        print(f"[UYARI] Gorsel bulunamadi: {args.images}")
        print("[IPUCU] Once 01_prepare_ccpd_sample.py calistir.")
        return

    converted = 0
    skipped = 0
    errors = []

    for img_path in image_paths:
        try:
            x1, y1, x2, y2 = parse_bbox_from_filename(img_path.name)
            img = cv2.imread(str(img_path))
            if img is None:
                skipped += 1
                errors.append(f"Okunamadi: {img_path.name}")
                continue
            h, w = img.shape[:2]
            xc, yc, bw, bh = to_yolo_bbox(x1, y1, x2, y2, w, h)
            label_line = f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n"
            (args.labels / f"{img_path.stem}.txt").write_text(label_line, encoding="utf-8")
            converted += 1
        except Exception as e:
            skipped += 1
            errors.append(f"{img_path.name}: {e}")

    print(f"\n[OK] Donusen: {converted} | Atlanan: {skipped}")
    if errors[:10]:
        print("\n[HATALAR] (ilk 10):")
        for err in errors[:10]:
            print(f"  {err}")


if __name__ == "__main__":
    main()
