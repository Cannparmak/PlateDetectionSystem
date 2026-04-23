"""
YOLOv11s plaka tespit modeli egitimi.

Degisiklikler v1'den v2'ye:
  - yolo11n (nano) → yolo11s (small): daha iyi dogruluk
  - imgsz: 640 → 1280: kucuk nesne (plaka) icin kritik
  - epochs: 30 → 100 (erken durdurma ile)
  - optimizer: SGD → AdamW: daha kararlı yakınsama
  - batch: 16 → 8 (1280 imgsz icin bellek dengesi)
  - Zengin augmentation eklendi

Kullanim:
  python scripts/04_train_yolo.py              # Otomatik cihaz
  python scripts/04_train_yolo.py --device 0  # GPU
  python scripts/04_train_yolo.py --device cpu # CPU (zorunda kalinirsa)
  python scripts/04_train_yolo.py --batch 4   # Az GPU bellek icin
"""

from pathlib import Path
import argparse
import torch
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="YOLOv11s plaka tespit modeli egitimi (v2)")
    parser.add_argument("--device", default="auto", help="auto | cpu | 0 | 0,1")
    parser.add_argument("--batch", type=int, default=8, help="Batch boyutu (az VRAM icin 4'e dusurun)")
    parser.add_argument("--epochs", type=int, default=100, help="Maksimum epoch sayisi")
    parser.add_argument("--imgsz", type=int, default=1280, help="Goruntu boyutu")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/processed/yolo_plate_dataset_v2/dataset.yaml"),
        help="dataset.yaml yolu",
    )
    parser.add_argument("--name", default="plate_det_global_v1", help="Calisma adi")
    args = parser.parse_args()

    if not args.data.exists():
        raise FileNotFoundError(
            f"dataset.yaml bulunamadi: {args.data}\n"
            "Once 01, 02, 03 scriptlerini calistirin."
        )

    # Cihaz sec
    if args.device == "auto":
        device = 0 if torch.cuda.is_available() else "cpu"
    elif args.device.isdigit():
        device = int(args.device)
    else:
        device = args.device

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"[GPU] {gpu_name} ({gpu_mem:.1f} GB VRAM)")
        if gpu_mem < 6 and args.imgsz == 1280:
            print("[UYARI] 6GB'dan az VRAM. --batch 4 veya --imgsz 640 kullanmayi deneyin.")
    else:
        print("[INFO] GPU bulunamadi, CPU kullanilacak. Bu yavas olacak.")
        print("[IPUCU] Google Colab veya Kaggle uzerinde GPU ile egitimi deneyin.")

    print(f"[INFO] Egitim cihazi: {device}")
    print(f"[INFO] Model: yolo11s.pt | imgsz: {args.imgsz} | batch: {args.batch} | epochs: {args.epochs}")

    # YOLOv11s — nano yerine small variant
    model = YOLO("yolo11s.pt")

    model.train(
        data=str(args.data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,

        # Optimizer — AdamW SGD'den daha kararlı
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=5,

        # Erken durdurma — overfitting oncesi dur
        patience=20,

        # Augmentation — plaka tespiti icin optimize
        degrees=15,          # Acili park yerlerindeki araclar
        perspective=0.002,   # Kamera perspektif bozulmasi
        mosaic=1.0,          # Mozaik (kucuk nesne icin cok etkili)
        mixup=0.15,
        copy_paste=0.1,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        blur=0.01,           # Hizli arac / uzak mesafe
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        erasing=0.4,

        # Kayip agirliklar
        box=7.5,
        cls=0.5,
        dfl=1.5,

        # Cikti
        project="runs/detect",
        name=args.name,
        save_period=10,      # Her 10 epoch'ta checkpoint kaydet
        plots=True,
        verbose=True,
    )

    print("\n[OK] Egitim tamamlandi.")
    print(f"[OK] Sonuclar: runs/detect/{args.name}/")
    print(f"[OK] En iyi model: runs/detect/{args.name}/weights/best.pt")


if __name__ == "__main__":
    main()
