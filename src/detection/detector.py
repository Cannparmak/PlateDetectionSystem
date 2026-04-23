"""
Plaka tespit modülü — YOLOv11s tabanlı bounding box tespiti.

Kullanım:
    detector = PlateDetector("models/plate_det_global_v1_best.pt")
    detections = detector.detect(frame)
    for det in detections:
        print(det.bbox, det.confidence)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Tek bir plaka tespiti."""
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 (piksel)
    confidence: float
    crop: np.ndarray                 # Kırpılmış plaka bölgesi (BGR)


class PlateDetector:
    """
    YOLOv11s tabanlı plaka dedektörü.

    Singleton olarak kullanılması önerilir:
        detector = PlateDetector.get_instance("models/plate_det_global_v1_best.pt")
    """

    _instance: PlateDetector | None = None

    def __init__(self, model_path: str, conf: float = 0.35, device: str = "auto", imgsz: int = 640):
        self._model_path = model_path
        self._conf = conf
        self._device = device
        self._imgsz = imgsz
        self._model = None  # Lazy loading

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls, model_path: str, conf: float = 0.35, device: str = "auto", imgsz: int = 640) -> "PlateDetector":
        if cls._instance is None:
            cls._instance = cls(model_path, conf, device, imgsz)
        return cls._instance

    # ------------------------------------------------------------------
    # Model yükleme
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._model is not None:
            return

        if not Path(self._model_path).exists():
            raise FileNotFoundError(f"Model bulunamadı: {self._model_path}")

        from ultralytics import YOLO
        import torch

        if self._device == "auto":
            device = 0 if torch.cuda.is_available() else "cpu"
        elif str(self._device).isdigit():
            device = int(self._device)
        else:
            device = self._device

        logger.info("Model yükleniyor: %s (device=%s)", self._model_path, device)
        self._model = YOLO(self._model_path)
        self._device_resolved = device
        logger.info("Model yüklendi.")

    def warmup(self) -> None:
        """Startup'ta çağır — ilk inference gecikmesini önler."""
        self._load()
        dummy = np.zeros((self._imgsz, self._imgsz, 3), dtype=np.uint8)
        self._model.predict(dummy, device=self._device_resolved, conf=self._conf, imgsz=self._imgsz, verbose=False)
        logger.info("Model warmup tamamlandı (imgsz=%d).", self._imgsz)

    # ------------------------------------------------------------------
    # Tespit
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> list[Detection]:
        """
        NumPy BGR görüntüsünden plaka tespiti yapar.

        Args:
            image: BGR formatında numpy array (cv2.imread çıktısı gibi)

        Returns:
            Detection listesi (confidence'a göre azalan sırada)
        """
        self._load()

        results = self._model.predict(
            image,
            device=self._device_resolved,
            conf=self._conf,
            imgsz=self._imgsz,
            verbose=False,
        )

        detections: list[Detection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])

                # Görüntü sınırlarına kırp
                h, w = image.shape[:2]
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(w, x2)
                y2 = min(h, y2)

                crop = image[y1:y2, x1:x2].copy()
                detections.append(Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=confidence,
                    crop=crop,
                ))

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections

    def detect_file(self, path: str) -> list[Detection]:
        """Dosya yolundan plaka tespiti yapar."""
        image = cv2.imread(path)
        if image is None:
            raise ValueError(f"Görüntü okunamadı: {path}")
        return self.detect(image)

    def draw_detections(self, image: np.ndarray, detections: list[Detection]) -> np.ndarray:
        """
        Tespit edilen plakaları görüntü üzerine çizer.

        Returns:
            Annotated görüntü (orijinal kopyalanır)
        """
        output = image.copy()
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            label = f"plate {det.confidence:.2f}"
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                output, label,
                (x1, max(y1 - 6, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 255, 0), 2,
            )
        return output
