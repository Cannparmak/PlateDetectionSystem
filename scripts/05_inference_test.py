import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultralytics import YOLO

from weights_utils import find_best_weights


def main():
    model_path = find_best_weights()
    test_images = Path("data/processed/yolo_plate_dataset/images/test")
    out_dir = "outputs/runs/predict_v1"

    print(f"[INFO] Model: {model_path}")
    if not test_images.exists():
        raise FileNotFoundError(f"Test klasoru bulunamadi: {test_images}")

    model = YOLO(str(model_path))
    model.predict(
        source=str(test_images),
        save=True,
        project="outputs/runs",
        name="predict_v1",
        conf=0.25,
    )
    print(f"[OK] Inference tamamlandi -> {out_dir}")


if __name__ == "__main__":
    main()
