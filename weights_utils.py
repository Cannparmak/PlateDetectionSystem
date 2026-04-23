"""Egitim ciktisinda best.pt dosyasini olasi yollarda arar."""

from pathlib import Path


def find_best_weights() -> Path:
    """Ultralytics bazen project/name'i ic ice yazar; olasi yollar."""
    candidates = [
        Path("outputs/runs/plate_det_v1/weights/best.pt"),
        Path("runs/detect/outputs/runs/plate_det_v1/weights/best.pt"),
        Path("runs/detect/plate_det_v1/weights/best.pt"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError(
        "best.pt bulunamadi. Once 04_train_yolo.py ile egitim yapin veya --model ile yol verin."
    )
