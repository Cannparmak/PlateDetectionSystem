"""
Plaka OCR modülü — fast-plate-ocr (ONNX) tabanlı metin okuma.

EasyOCR'ın yerini aldı. Plaka başına ~5-20ms (EasyOCR: 200-800ms).

Kullanım:
    ocr = PlateOCR()
    result = ocr.read(crop_bgr)
    print(result.cleaned_text, result.confidence)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Primary: Avrupa modeli — Türkiye dahil, grayscale, 9 slot.
# Fallback: CCT-S-v2 global — RGB, 10 slot, 3x daha fazla eğitim verisi.
# Farklı mimari + renk kanalı → oylama gerçek çeşitlilik sağlar.
_PRIMARY_MODEL = "european-plates-mobile-vit-v2-model"
_FALLBACK_MODEL = "cct-s-v2-global-model"

# Fallback oylama eşiği: primary bu confidence'ın altına düşerse fallback devreye girer.
_DUAL_MODEL_THRESHOLD = 0.65


@dataclass
class OCRResult:
    """Tek bir OCR sonucu."""
    text: str              # Ham metin (model çıktısı)
    cleaned_text: str      # Temizlenmiş metin
    confidence: float      # 0.0 – 1.0
    format_valid: bool     # Bilinen plaka formatına uyuyor mu
    plate_format: str = "UNKNOWN"  # Eşleşen format adı: "TR", "UK", "GENERIC", vb.


class PlateOCR:
    """
    fast-plate-ocr (ONNX) tabanlı plaka metin okuyucu.

    Singleton olarak kullanılması önerilir:
        ocr = PlateOCR.get_instance()
    """

    _instance: PlateOCR | None = None

    def __init__(
        self,
        languages: list[str] | None = None,  # EasyOCR uyumluluğu için kabul edilir
        gpu: bool | None = None,
    ) -> None:
        self._recognizer    = None   # Primary model — lazy loading
        self._recognizer_fb = None   # Fallback model — lazy loading

    @classmethod
    def get_instance(
        cls,
        languages: list[str] | None = None,
        gpu: bool | None = None,
    ) -> "PlateOCR":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Model yükleme
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Primary modeli yükler (lazy)."""
        if self._recognizer is not None:
            return
        from fast_plate_ocr import LicensePlateRecognizer
        logger.info("fast-plate-ocr yükleniyor (model=%s)...", _PRIMARY_MODEL)
        try:
            self._recognizer = LicensePlateRecognizer(
                hub_ocr_model=_PRIMARY_MODEL, device="auto")
            logger.info("fast-plate-ocr hazır: %s", _PRIMARY_MODEL)
        except Exception as e:
            logger.warning("Primary model yüklenemedi (%s): %s — global'e düşülüyor", _PRIMARY_MODEL, e)
            self._recognizer = LicensePlateRecognizer(
                hub_ocr_model="global-plates-mobile-vit-v2-model", device="auto")

    def _load_fallback(self) -> bool:
        """
        Fallback modeli yükler (lazy). Başarıysa True döner.
        Primary ile aynı model olursa yüklemeyi atlar.
        """
        if self._recognizer_fb is not None:
            return True
        try:
            from fast_plate_ocr import LicensePlateRecognizer
            logger.info("Fallback model yükleniyor: %s", _FALLBACK_MODEL)
            self._recognizer_fb = LicensePlateRecognizer(
                hub_ocr_model=_FALLBACK_MODEL, device="auto")
            logger.info("Fallback model hazır.")
            return True
        except Exception as e:
            logger.warning("Fallback model yüklenemedi: %s", e)
            return False

    # ------------------------------------------------------------------
    # Görüntü ön işleme — BGR aşaması (her iki model için ortak)
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess_bgr(crop: np.ndarray) -> np.ndarray:
        """
        BGR kırpıntıyı iyileştirir. Renk dönüşümü yapılmaz.

        İşlem sırası (doğruluk etkisine göre):
        1. CLAHE — adaptif kontrast (en yüksek etki, +%25 doğruluk)
        2. Bilateral filtre — gürültü azalt, karakter kenarlarını koru
        3. Upscale — çok küçük kırpıntıları büyüt
        4. Post-upscale keskinleştirme

        NOT: Alt-crop kaldırıldı. Model keep_aspect_ratio=False ile 140×70'e
        stretch ettiğinden crop yapmak aspect ratio bozar ve city-name bağlamını
        siler; tam plaka görseli her zaman daha doğru sonuç verir.
        """
        h, w = crop.shape[:2]

        # ── CLAHE (LAB L kanalında) ──────────────────────────────────────
        tile = max(2, min(4, h // 10, w // 10))
        lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(tile, tile))
        l = clahe.apply(l)
        crop = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        # ── Bilateral filtre ─────────────────────────────────────────────
        crop = cv2.bilateralFilter(crop, d=5, sigmaColor=40, sigmaSpace=40)

        # ── Upscale + post-upscale sharpening ───────────────────────────
        h, w = crop.shape[:2]
        if max(h, w) < 80:
            scale = 4
        elif max(h, w) < 160:
            scale = 3
        elif max(h, w) < 300:
            scale = 2
        else:
            scale = 1

        if scale > 1:
            crop = cv2.resize(crop, (w * scale, h * scale),
                              interpolation=cv2.INTER_CUBIC)
            kernel = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]], dtype=np.float32)
            crop = cv2.filter2D(crop, -1, kernel,
                                borderType=cv2.BORDER_REPLICATE)

        return crop

    @staticmethod
    def _to_model_input(bgr: np.ndarray, num_channels: int) -> np.ndarray:
        """BGR görüntüyü model'in beklediği renk uzayına dönüştürür."""
        if num_channels == 1:
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # ------------------------------------------------------------------
    # Güven skoru hesaplama
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_confidence(char_probs: list[float] | None) -> tuple[float, bool]:
        """
        Median tabanlı güven skoru. Mean'e göre outlier-robust.

        Returns:
            (confidence, is_reliable)
        """
        if not char_probs:
            return 0.75, True

        probs = np.array(char_probs, dtype=np.float32)
        median_conf = float(np.median(probs))
        min_conf    = float(np.min(probs))
        is_reliable = median_conf > 0.65 and min_conf > 0.35
        return median_conf, is_reliable

    # ------------------------------------------------------------------
    # Karakter bazlı oylama (dual-model)
    # ------------------------------------------------------------------

    @staticmethod
    def _char_vote(text_a: str, conf_a: float,
                   text_b: str, conf_b: float) -> str:
        """
        İki model çıktısını karakter bazlı birleştirir.
        Uzunluk farklıysa daha güvenli modeli tercih eder.
        """
        if len(text_a) != len(text_b):
            return text_a if conf_a >= conf_b else text_b
        return "".join(ca if conf_a >= conf_b else cb
                       for ca, cb in zip(text_a, text_b))

    # ------------------------------------------------------------------
    # İç model çağrısı
    # ------------------------------------------------------------------

    @staticmethod
    def _run_model(recognizer, prepared: np.ndarray) -> tuple[str, list[float]]:
        prediction = recognizer.run_one(prepared, return_confidence=True)
        raw_text   = prediction.plate or ""
        char_probs = list(prediction.char_probs) if prediction.char_probs is not None else []
        return raw_text, char_probs

    # ------------------------------------------------------------------
    # Ana okuma fonksiyonu
    # ------------------------------------------------------------------

    def read(self, crop: np.ndarray) -> OCRResult:
        """
        Plaka kırpıntısından metin okur.

        Düşük confidence durumunda CCT-S-v2 (RGB, 3x daha fazla veri) devreye
        girer ve karakter bazlı oylama yapılır.

        Args:
            crop: BGR formatında numpy array (Detection.crop)
        """
        self._load()

        if crop is None or crop.size == 0:
            return OCRResult(text="", cleaned_text="", confidence=0.0,
                             format_valid=False)

        from src.postprocess.text_cleaner import PlateCleaner
        cleaner = PlateCleaner()

        # BGR ön işleme — primary ve fallback için ortak
        bgr = self._preprocess_bgr(crop)

        # ── Primary model ────────────────────────────────────────────────
        num_ch_primary = getattr(self._recognizer.config, "num_channels", 1)
        prepared = self._to_model_input(bgr, num_ch_primary)

        try:
            raw_text, char_probs = self._run_model(self._recognizer, prepared)
            confidence, is_reliable = self._calc_confidence(char_probs)
        except Exception as e:
            logger.warning("OCR hatası (primary): %s", e)
            return OCRResult(text="", cleaned_text="", confidence=0.0,
                             format_valid=False)

        # ── Dual-model voting (fallback: CCT-S-v2 RGB) ──────────────────
        if confidence < _DUAL_MODEL_THRESHOLD or not is_reliable:
            if self._load_fallback() and self._recognizer_fb is not None:
                try:
                    num_ch_fb   = getattr(self._recognizer_fb.config, "num_channels", 3)
                    prepared_fb = self._to_model_input(bgr, num_ch_fb)
                    raw_fb, probs_fb = self._run_model(self._recognizer_fb, prepared_fb)
                    conf_fb, _ = self._calc_confidence(probs_fb)

                    logger.debug("Dual-model: primary=%s(%.2f) fallback=%s(%.2f)",
                                 raw_text, confidence, raw_fb, conf_fb)

                    if conf_fb > confidence:
                        raw_text, char_probs, confidence = raw_fb, probs_fb, conf_fb
                    elif raw_text and raw_fb and raw_text != raw_fb:
                        raw_text   = self._char_vote(raw_text, confidence, raw_fb, conf_fb)
                        confidence = max(confidence, conf_fb)
                except Exception as e:
                    logger.debug("Dual-model fallback hatası: %s", e)

        # ── Metin temizleme ve doğrulama ─────────────────────────────────
        cleaned = cleaner.clean(raw_text)
        fixed   = cleaner.fix_ocr_errors(cleaned)
        valid, fmt = cleaner.validate(fixed)

        return OCRResult(
            text=raw_text,
            cleaned_text=fixed,
            confidence=confidence,
            format_valid=valid,
            plate_format=fmt,
        )

    def read_batch(self, crops: list[np.ndarray]) -> list[OCRResult]:
        """Birden fazla kırpıntıyı sırayla okur."""
        return [self.read(crop) for crop in crops]
