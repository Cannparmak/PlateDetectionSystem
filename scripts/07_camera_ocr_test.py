"""
Canlı kamera + plaka tespit + OCR test scripti.

Webcam açar, her karede YOLO ile plaka bulur, EasyOCR ile okur,
ekranda hem bounding box hem plaka metni gösterir.

Kullanım:
  python scripts/07_camera_ocr_test.py                      # varsayılan webcam
  python scripts/07_camera_ocr_test.py --source 1           # 2. kamera
  python scripts/07_camera_ocr_test.py --source resim.jpg   # tek görüntü
  python scripts/07_camera_ocr_test.py --source video.mp4   # video dosyası

Tuşlar:
  q       → çıkış
  s       → ekran görüntüsü + crop kaydet (outputs/ocr_test_screenshots/)
  SPACE   → duraklat / devam et
  d       → debug modu: crop'ları sürekli kaydet (OCR analizi için)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Proje kökünü Python path'e ekle
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import cv2
import numpy as np

from src.detection.detector import PlateDetector
from src.ocr.reader import PlateOCR
from src.postprocess.text_cleaner import PlateCleaner


# ------------------------------------------------------------------
# Yardımcı: Türkçe karakter sorunu olan sistemler için font
# ------------------------------------------------------------------
def put_text(img, text, pos, scale=0.7, color=(0, 255, 100), thickness=2):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


# ------------------------------------------------------------------
# Ana işleme döngüsü
# ------------------------------------------------------------------
def process_frame(
    frame: np.ndarray,
    detector: PlateDetector,
    ocr: PlateOCR,
    cleaner: PlateCleaner,
    last_ocr_time: float,
    ocr_interval: float,
    last_ocr_results: list,
) -> tuple[np.ndarray, list, float]:
    """
    Tek kareyi işler. OCR her karede değil, ocr_interval saniyede bir çalışır
    (EasyOCR yavaş olduğu için FPS düşmemesi için).

    Returns: (annotated_frame, ocr_results, updated_last_ocr_time)
    """
    detections = detector.detect(frame)
    now = time.time()

    # OCR — interval dolmuşsa çalıştır
    if detections and (now - last_ocr_time) >= ocr_interval:
        last_ocr_results = []
        for det in detections:
            result = ocr.read(det.crop)
            last_ocr_results.append({
                "bbox": det.bbox,
                "conf_det": det.confidence,
                "text": result.cleaned_text,
                "raw": result.text,
                "conf_ocr": result.confidence,
                "valid": result.format_valid,
                "crop": det.crop,  # debug için sakla
            })
        last_ocr_time = now

        if last_ocr_results:
            texts = [r["text"] for r in last_ocr_results if r["text"]]
            raws  = [r["raw"] for r in last_ocr_results if r["raw"]]
            if texts:
                print(f"[PLAKA] temiz={' | '.join(texts)}  ham={' | '.join(raws)}")
            elif raws:
                print(f"[PLAKA] (format gecersiz) ham={' | '.join(raws)}")

    # Çizim
    output = frame.copy()
    for r in last_ocr_results:
        x1, y1, x2, y2 = r["bbox"]
        color = (0, 255, 0) if r["valid"] else (0, 165, 255)

        # Bounding box
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

        # Tespit güveni
        det_label = f"det:{r['conf_det']:.2f}"
        put_text(output, det_label, (x1, max(y1 - 8, 12)), scale=0.55, color=color)

        # OCR metni
        if r["text"]:
            ocr_label = f"{r['text']}  ocr:{r['conf_ocr']:.2f}"
            put_text(output, ocr_label, (x1, y2 + 22), scale=0.65, color=(0, 220, 255))
        elif r["raw"]:
            put_text(output, f"[{r['raw']}]", (x1, y2 + 22), scale=0.55, color=(80, 80, 255))

    # Detections var ama OCR result henüz yok
    if detections and not last_ocr_results:
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Bilgi satırı (sol üst)
    put_text(output, f"Tespit: {len(detections)}", (10, 28), color=(200, 200, 200))
    if last_ocr_results:
        last_text = last_ocr_results[0]["text"] or last_ocr_results[0]["raw"] or "-"
        put_text(output, f"Son: {last_text}", (10, 58), color=(0, 220, 255))

    put_text(output, "Q:cikis  S:kaydet  SPACE:duraklat", (10, output.shape[0] - 10),
             scale=0.45, color=(180, 180, 180))

    return output, last_ocr_results, last_ocr_time


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Canlı kamera + plaka OCR test")
    parser.add_argument("--source", default="0",
                        help="Webcam indeksi (0/1) veya dosya yolu")
    parser.add_argument("--model", default="models/plate_det_global_v1_best.pt",
                        help="YOLO model yolu")
    parser.add_argument("--conf", type=float, default=0.35,
                        help="YOLO güven eşiği")
    parser.add_argument("--ocr-interval", type=float, default=0.5,
                        help="OCR aralığı (saniye) — düşürürsen daha sık okur ama FPS düşer")
    parser.add_argument("--device", default="auto",
                        help="auto | cpu | 0")
    args = parser.parse_args()

    model_path = str((_ROOT / args.model).resolve())
    if not Path(model_path).exists():
        print(f"HATA: Model bulunamadı: {model_path}")
        sys.exit(1)

    # Kaynak
    source_str = args.source.strip()
    if source_str.isdigit():
        source = int(source_str)
    else:
        source = str((_ROOT / source_str).resolve()) if not Path(source_str).is_absolute() else source_str

    print(f"[INFO] Model yükleniyor: {model_path}")
    detector = PlateDetector(model_path, conf=args.conf, device=args.device)

    print("[INFO] EasyOCR yükleniyor (ilk seferde model indirme yapabilir, bekle)...")
    ocr = PlateOCR(languages=["tr", "en", "de", "fr"])
    ocr._load()  # Warmup — hemen yükle

    cleaner = PlateCleaner()

    print(f"[INFO] Kamera/kaynak açılıyor: {source}")
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"HATA: Kaynak açılamadı: {source}")
        sys.exit(1)

    # Çıktı klasörü
    screenshot_dir = _ROOT / "outputs" / "ocr_test_screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    print("[HAZIR] Kamera açık. Q:çıkış | S:kaydet | SPACE:duraklat")
    print("-" * 50)

    last_ocr_time = 0.0
    last_ocr_results: list = []
    paused = False
    frame_count = 0
    debug_mode = False
    debug_crop_count = 0

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] Görüntü bitti veya kamera kapandı.")
                break

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord(" "):
            paused = not paused
            status = "DURAKLADI" if paused else "DEVAM"
            print(f"[{status}]")
            continue
        elif key == ord("d"):
            debug_mode = not debug_mode
            print(f"[DEBUG] {'AÇIK — crop\'lar kaydediliyor' if debug_mode else 'KAPALI'}")
        elif key == ord("s"):
            ts = int(time.time())
            out_path = screenshot_dir / f"ocr_test_{ts}.jpg"
            cv2.imwrite(str(out_path), display_frame if "display_frame" in dir() else frame)
            # Crop'ları da kaydet
            for i, r in enumerate(last_ocr_results):
                if "crop" in r:
                    crop_path = screenshot_dir / f"crop_{ts}_{i}_{r['text'] or 'empty'}.jpg"
                    cv2.imwrite(str(crop_path), r["crop"])
            print(f"[KAYIT] {out_path}")

        if paused:
            cv2.imshow("PlateDetectionSystem — OCR Test (Q:cikis)", display_frame if "display_frame" in dir() else frame)
            continue

        display_frame, last_ocr_results, last_ocr_time = process_frame(
            frame, detector, ocr, cleaner,
            last_ocr_time, args.ocr_interval, last_ocr_results,
        )

        frame_count += 1
        cv2.imshow("PlateDetectionSystem — OCR Test (Q:cikis)", display_frame)

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[BITTI] {frame_count} kare işlendi.")


if __name__ == "__main__":
    main()
