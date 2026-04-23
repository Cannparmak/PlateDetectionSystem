"""
Birleşik plaka tespit pipeline'ı.

YOLO detection + EasyOCR + metin temizleme adımlarını tek çatı altında birleştirir.

Kullanım:
    pipeline = PlateDetectionPipeline.get_instance(model_path="models/plate_det_global_v1_best.pt")
    result = pipeline.process_frame(frame_bgr)
    print(result.plate_texts)
"""

from __future__ import annotations

import base64
import logging
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PlateInfo:
    """Tek bir plaka için tüm tespit ve OCR bilgileri."""
    bbox: tuple[int, int, int, int]   # x1, y1, x2, y2
    plate_text: str                    # Temizlenmiş plaka metni
    raw_text: str                      # Ham OCR çıktısı
    confidence_det: float              # YOLO güven skoru
    confidence_ocr: float              # OCR güven skoru
    format_valid: bool                 # Plaka formatı geçerli mi
    plate_format: str                  # Eşleşen format: "TR", "UK", "GENERIC", vb.
    crop_b64: str                      # Base64 JPEG (API / WebSocket için)


@dataclass
class PipelineResult:
    """Bir kare için tüm pipeline çıktıları."""
    annotated_image_b64: str           # Annotated frame, Base64 JPEG
    plates: list[PlateInfo] = field(default_factory=list)
    processing_ms: float = 0.0
    plate_texts: list[str] = field(default_factory=list)  # Sadece temizlenmiş metinler


class PlateDetectionPipeline:
    """
    Tespit + OCR + temizleme pipeline'ı.

    Singleton olarak kullanılması önerilir — model yüklemelerini tekrarlamaz.
    """

    _instance: PlateDetectionPipeline | None = None

    # YOLO-only karelerde annotation tekrar üretilmez — son kare yeniden kullanılır
    _last_annotated_b64: str = ""

    def __init__(
        self,
        model_path: str,
        conf: float = 0.35,
        device: str = "auto",
        languages: list[str] | None = None,
        ocr_gpu: bool | None = None,
    ):
        from src.detection.detector import PlateDetector
        from src.ocr.reader import PlateOCR
        from src.postprocess.text_cleaner import PlateCleaner

        self._detector = PlateDetector(model_path, conf=conf, device=device)
        self._ocr = PlateOCR(languages=languages, gpu=ocr_gpu)
        self._cleaner = PlateCleaner()

    @classmethod
    def get_instance(
        cls,
        model_path: str,
        conf: float = 0.35,
        device: str = "auto",
        languages: list[str] | None = None,
        ocr_gpu: bool | None = None,
    ) -> "PlateDetectionPipeline":
        if cls._instance is None:
            cls._instance = cls(model_path, conf, device, languages, ocr_gpu)
        return cls._instance

    # ------------------------------------------------------------------
    # Warmup
    # ------------------------------------------------------------------

    def warmup(self) -> None:
        """Startup event'te çağır — tüm modelleri önceden yükler."""
        logger.info("Pipeline warmup başlıyor...")
        self._detector.warmup()
        self._ocr._load()
        logger.info("Pipeline hazır.")

    # ------------------------------------------------------------------
    # İşleme
    # ------------------------------------------------------------------

    def process_frame(self, frame: np.ndarray, run_ocr: bool = True) -> PipelineResult:
        """
        Kamera karesi veya görüntüsünü işler.

        Args:
            frame: BGR numpy array
            run_ocr: False ise OCR atlanır — sadece YOLO tespiti yapılır (FPS modu)

        Returns:
            PipelineResult
        """
        return self._run(frame, run_ocr=run_ocr)

    def process_image(self, image: np.ndarray) -> PipelineResult:
        """process_frame ile aynı, dosyadan okunan görüntüler için alias."""
        return self._run(image, run_ocr=True)

    def _run(self, image: np.ndarray, run_ocr: bool = True) -> PipelineResult:
        t0 = time.perf_counter()

        # YOLO verimliliği için max 640px'e resize (aspect ratio korunur)
        h, w = image.shape[:2]
        if max(h, w) > 640:
            scale = 640.0 / max(h, w)
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)

        detections = self._detector.detect(image)

        plates: list[PlateInfo] = []
        for det in detections:
            if run_ocr:
                # Crop → Base64 (sadece OCR karesinde encode et)
                _, buf = cv2.imencode(".jpg", det.crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
                crop_b64 = base64.b64encode(buf).decode("utf-8")

                ocr_result    = self._ocr.read(det.crop)
                plate_text    = ocr_result.cleaned_text
                raw_text      = ocr_result.text
                confidence_ocr = ocr_result.confidence
                format_valid  = ocr_result.format_valid
                plate_format  = ocr_result.plate_format
            else:
                crop_b64      = ""
                plate_text    = ""
                raw_text      = ""
                confidence_ocr = 0.0
                format_valid  = False
                plate_format  = "UNKNOWN"

            plates.append(PlateInfo(
                bbox=det.bbox,
                plate_text=plate_text,
                raw_text=raw_text,
                confidence_det=det.confidence,
                confidence_ocr=confidence_ocr,
                format_valid=format_valid,
                plate_format=plate_format,
                crop_b64=crop_b64,
            ))

        # Annotated görüntü: YOLO-only karelerde son kareyi yeniden kullan —
        # draw_detections + imencode pahalı, her kare tekrarlanmasına gerek yok.
        if run_ocr or not self._last_annotated_b64:
            annotated = self._detector.draw_detections(image, detections)
            for p in plates:
                x1, y1, x2, y2 = p.bbox
                label = p.plate_text or "?"
                cv2.putText(
                    annotated, label,
                    (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 200, 255), 2,
                )
            _, ann_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self._last_annotated_b64 = base64.b64encode(ann_buf).decode("utf-8")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug("Pipeline: %d plaka, %.1f ms (ocr=%s)", len(plates), elapsed_ms, run_ocr)

        return PipelineResult(
            annotated_image_b64=self._last_annotated_b64,
            plates=plates,
            processing_ms=round(elapsed_ms, 1),
            plate_texts=[p.plate_text for p in plates if p.plate_text],
        )
