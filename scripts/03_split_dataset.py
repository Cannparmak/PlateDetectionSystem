"""
Goruntu-label ciftlerini train/val/test olarak ayirir.

Oranlar: %80 train, %10 val, %10 test
Cikti: data/processed/yolo_plate_dataset_v2/

Kullanim:
  python scripts/03_split_dataset.py
  python scripts/03_split_dataset.py --images data/interim/ccpd_sample_v2/images
                                      --labels data/interim/ccpd_sample_v2/labels
                                      --out    data/processed/yolo_plate_dataset_v2
"""

from pathlib import Path
import argparse
import random
import shutil


def ensure_dirs(base: Path) -> None:
    for split in ("train", "val", "test"):
        (base / "images" / split).mkdir(parents=True, exist_ok=True)
        (base / "labels" / split).mkdir(parents=True, exist_ok=True)


def write_dataset_yaml(base: Path, nc: int = 1, names: list[str] = None) -> None:
    if names is None:
        names = ["plate"]
    yaml_content = (
        f"path: {base.resolve().as_posix()}\n"
        f"train: images/train\n"
        f"val:   images/val\n"
        f"test:  images/test\n"
        f"\nnc: {nc}\n"
        f"names:\n"
    )
    for i, name in enumerate(names):
        yaml_content += f"  {i}: {name}\n"
    (base / "dataset.yaml").write_text(yaml_content, encoding="utf-8")
    print(f"[OK] dataset.yaml olusturuldu: {base / 'dataset.yaml'}")


def main():
    parser = argparse.ArgumentParser(
        description="Goruntu-label ciftlerini train/val/test olarak ayirir."
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
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/yolo_plate_dataset_v2"),
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.80, help="Train orani (varsayilan: 0.80)"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.10, help="Validasyon orani (varsayilan: 0.10)"
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.images.exists():
        raise FileNotFoundError(f"Goruntu klasoru bulunamadi: {args.images}")
    if not args.labels.exists():
        raise FileNotFoundError(f"Label klasoru bulunamadi: {args.labels}")

    # Test oranini hesapla
    test_ratio = 1.0 - args.train_ratio - args.val_ratio
    if test_ratio < 0:
        raise ValueError("train_ratio + val_ratio toplamı 1.0'ı gecemez.")

    ensure_dirs(args.out)
    random.seed(args.seed)

    # Hem goruntusu hem labeli olan ciftleri topla
    image_paths = sorted(
        p for p in args.images.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    pairs = []
    missing_labels = 0
    for img in image_paths:
        lbl = args.labels / f"{img.stem}.txt"
        if lbl.exists():
            pairs.append((img, lbl))
        else:
            missing_labels += 1

    if missing_labels > 0:
        print(f"[UYARI] {missing_labels} goruntu icin label bulunamadi, atlandı.")

    if not pairs:
        print("[HATA] Gecerli goruntu-label cifti bulunamadi. Once script 01 ve 02'yi calistir.")
        return

    random.shuffle(pairs)
    n = len(pairs)
    n_train = int(n * args.train_ratio)
    n_val = int(n * args.val_ratio)
    # Kalan hepsi test'e gider (yuvarlama hatasini onler)

    splits = {
        "train": pairs[:n_train],
        "val": pairs[n_train : n_train + n_val],
        "test": pairs[n_train + n_val :],
    }

    for split_name, split_pairs in splits.items():
        for img, lbl in split_pairs:
            shutil.copy2(img, args.out / "images" / split_name / img.name)
            shutil.copy2(lbl, args.out / "labels" / split_name / lbl.name)

    # dataset.yaml olustur
    write_dataset_yaml(args.out)

    print(
        f"\n[OK] Toplam: {n} cifti ayrildi\n"
        f"     train: {len(splits['train'])} ({len(splits['train'])/n*100:.1f}%)\n"
        f"     val:   {len(splits['val'])} ({len(splits['val'])/n*100:.1f}%)\n"
        f"     test:  {len(splits['test'])} ({len(splits['test'])/n*100:.1f}%)\n"
        f"     Cikti: {args.out}"
    )


if __name__ == "__main__":
    main()
