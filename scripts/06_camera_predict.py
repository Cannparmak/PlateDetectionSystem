"""
Kamera, video dosyasi veya tek goruntu ile plaka tespiti (YOLO).

Ornekler (proje kokunden, venv acik):
  python scripts/06_camera_predict.py --source 0
      -> varsayilan webcam (tablet ekranina tutarak da kullanabilirsin)

  python scripts/06_camera_predict.py --source "C:\\fotolar\\araba.jpg"
  python scripts/06_camera_predict.py --source "C:\\videolar\\test.mp4"

Tablet ekraninda foto gosterme: Webcam acikken tableti kameraya cevir;
ekstra kod gerekmez (giris yine webcam).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Proje kokunden calistir: python scripts/06_camera_predict.py
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultralytics import YOLO

from weights_utils import find_best_weights


def parse_source(s: str):
    """0, 1 -> webcam indeksi; digerleri dosya yolu."""
    s = s.strip()
    if s.isdigit():
        return int(s)
    p = Path(s)
    if not p.exists():
        raise FileNotFoundError(f"Kaynak bulunamadi: {s}")
    return str(p.resolve())


def main():
    parser = argparse.ArgumentParser(description="Kamera / video / goruntu ile YOLO tahmini")
    parser.add_argument(
        "--source",
        default="0",
        help='Webcam: 0 veya 1 | Dosya: .jpg .png .mp4 .avi tam yol',
    )
    parser.add_argument(
        "--model",
        default=None,
        help="best.pt yolu (verilmezse otomatik aranir)",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Guven esigi")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Onizleme penceresini kapat, sadece sonuc dosyalarini kaydet",
    )
    parser.add_argument("--device", default=None, help="auto icin bos birakin; veya 0, cpu")
    args = parser.parse_args()

    model_path = Path(args.model).resolve() if args.model else find_best_weights()
    if args.model and not model_path.exists():
        raise FileNotFoundError(model_path)

    print(f"[INFO] Model: {model_path}")
    src = parse_source(args.source)
    print(f"[INFO] Kaynak: {src}")

    show = not args.no_show  # varsayilan: pencere acik
    model = YOLO(str(model_path))

    predict_kw = dict(
        source=src,
        conf=args.conf,
        imgsz=args.imgsz,
        save=True,
        project="outputs/runs",
        name="camera_predict",
        show=show,
    )
    if args.device:
        predict_kw["device"] = args.device

    model.predict(**predict_kw)
    print("[OK] Bitti. Sonuclar genelde: runs/detect/outputs/runs/camera_predict veya outputs/runs altinda.")


if __name__ == "__main__":
    main()
