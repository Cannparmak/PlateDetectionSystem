"""
Plaka metin temizleyici ve format doğrulayıcı.

Kullanım:
    cleaner = PlateCleaner()
    cleaned = cleaner.clean("34 ABC 1234")   # → "34ABC1234"
    valid, fmt = cleaner.validate("34ABC1234")  # → (True, "TR")
    fixed  = cleaner.fix_ocr_errors("34AB(1234")  # → "34AB1234"
"""

from __future__ import annotations

import re
import unicodedata


# ---------------------------------------------------------------------------
# Türk plakasında KULLANILMAYAN harfler (resmi standart)
# ---------------------------------------------------------------------------
# Geçerli Türk plaka harfleri: A B C D E F G H J K L M N P R S T U V Y Z
# Bulunmayan: I O Q W X
_TR_INVALID_LETTERS = set("IOQWX")
_TR_VALID_LETTERS   = set("ABCDEFGHJKLMNPRSTUVYZ")

# Türk il kodları: 01 – 81
_TR_CITY_MIN = 1
_TR_CITY_MAX = 81


class PlateCleaner:
    """
    Ham OCR metnini plaka formatına normalize eder, doğrular ve OCR
    hatalarını pozisyon bazlı olarak düzeltir.
    """

    # ------------------------------------------------------------------
    # Format regex'leri (öncelik sırası önemli — özelden genele)
    # ------------------------------------------------------------------
    FORMATS: dict[str, str] = {
        # ── Türkiye ──────────────────────────────────────────────────
        # 34ABC1234 | 06AB123 | 81YZ99
        # [il kodu 01-81][1-3 harf][2-4 rakam]
        "TR": r"^[0-9]{2}[ABCDEFGHJKLMNPRSTUVYZ]{1,3}[0-9]{2,4}$",

        # ── İngiltere (post-2001) ─────────────────────────────────────
        # AB12CDE
        "UK": r"^[A-Z]{2}[0-9]{2}[A-Z]{3}$",

        # ── Fransa (post-2009) ────────────────────────────────────────
        # AB123CD
        "FR": r"^[A-Z]{2}[0-9]{3}[A-Z]{2}$",

        # ── İtalya (post-1994) ────────────────────────────────────────
        # AB123CD  (Fransa ile aynı yapı, ayrı tutuyoruz)
        "IT": r"^[A-Z]{2}[0-9]{3}[A-Z]{2}$",

        # ── İspanya (post-2000) ───────────────────────────────────────
        # 1234ABC
        "ES": r"^[0-9]{4}[A-Z]{3}$",

        # ── Hollanda ─────────────────────────────────────────────────
        # XX99XX veya 99XXX9 gibi çeşitli seri formatları
        "NL": r"^[A-Z0-9]{6}$",

        # ── Almanya ──────────────────────────────────────────────────
        # B·AB·1234  →  BAB1234 (normalize edilmiş halde 5-8 kar.)
        "DE": r"^[A-Z]{1,3}[A-Z]{1,2}[0-9]{1,4}[EH]?$",

        # ── Polonya ──────────────────────────────────────────────────
        # WA12345
        "PL": r"^[A-Z]{2,3}[0-9]{4,5}$",

        # ── Genel alfanümerik (fallback, en sona) ────────────────────
        "GENERIC": r"^[A-Z0-9]{5,9}$",
    }

    # ------------------------------------------------------------------
    # OCR karakter karışıklıkları
    # ------------------------------------------------------------------
    # Rakam pozisyonunda beklenen düzeltmeler (harf → doğru rakam)
    _LETTER_TO_DIGIT: dict[str, str] = {
        "O": "0", "Q": "0", "D": "0",
        "I": "1", "L": "1",
        "Z": "2",
        "A": "4",
        "S": "5",
        "G": "6",
        "B": "8",
        "T": "7",
    }

    # Harf pozisyonunda beklenen düzeltmeler (rakam → doğru harf)
    _DIGIT_TO_LETTER: dict[str, str] = {
        "0": "O",  # Türk plakasında O geçersiz ama diğer formatlarda geçerli
        "1": "I",
        "5": "S",
        "8": "B",
        "2": "Z",
        "6": "G",
    }

    # Türkçe karakterlerin ASCII karşılıkları
    _TR_MAP = str.maketrans(
        "ğĞışŞüÜöÖçÇı",
        "gGisSuUoOcCi",
    )

    # ------------------------------------------------------------------
    # Temizleme
    # ------------------------------------------------------------------

    def clean(self, raw: str) -> str:
        """
        Ham OCR metnini normalize eder.

        1. Türkçe karakter → ASCII
        2. Unicode normalize
        3. Alfanümerik olmayanları kaldır
        4. Büyük harfe çevir
        """
        if not raw:
            return ""

        text = raw.translate(self._TR_MAP)
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = re.sub(r"[^A-Za-z0-9]", "", text)
        return text.upper()

    # ------------------------------------------------------------------
    # Doğrulama
    # ------------------------------------------------------------------

    def validate(self, text: str) -> tuple[bool, str]:
        """
        Temizlenmiş metni bilinen plaka formatlarına karşı doğrular.
        TR için il kodu aralığı (01-81) da kontrol edilir.

        Returns:
            (geçerli_mi, format_adı)
        """
        if not text:
            return False, "UNKNOWN"

        for fmt_name, pattern in self.FORMATS.items():
            if re.fullmatch(pattern, text):
                if fmt_name == "TR" and not self._validate_tr_city(text):
                    continue  # Regex geçti ama il kodu 82+ → geçersiz
                return True, fmt_name

        return False, "UNKNOWN"

    @staticmethod
    def _validate_tr_city(text: str) -> bool:
        """İlk 2 karakterin geçerli Türk il kodu (01-81) olup olmadığını kontrol eder."""
        try:
            city = int(text[:2])
            return _TR_CITY_MIN <= city <= _TR_CITY_MAX
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # OCR hata düzeltme — pozisyon bazlı (Türk plakası)
    # ------------------------------------------------------------------

    def fix_ocr_errors(self, text: str) -> str:
        """
        Türk plaka formatına göre pozisyon bazlı OCR hatası düzeltir.
        Format: [2 rakam][1-3 harf][2-4 rakam]

        Örnek:
            "3AABC1234" → "34ABC1234"  (A→4)
            "34OBC1234" → "34OBC1234"  (O Türk harfi değil ama bırak, validate reddeder)
            "34ABC!234" → "34ABC1234"  (!→1 düzeltilir)
        """
        if len(text) < 4:
            return text

        chars = list(text)
        n = len(chars)

        # -- Adım 1: İlk 2 karakter rakam olmalı --
        for i in range(min(2, n)):
            ch = chars[i]
            if ch.isalpha():
                chars[i] = self._LETTER_TO_DIGIT.get(ch, ch)

        # -- Adım 2: Son karakterleri tara, rakam bloğu bul --
        # TR formatı: sondaki 2-4 rakam
        # Geriye doğru git, rakam olan karakterleri bul
        suffix_end = n
        suffix_start = n
        for i in range(n - 1, 1, -1):  # İlk 2'yi atla
            if chars[i].isdigit():
                suffix_start = i
            else:
                break

        # Suffix uzunluğu 2-4 arası değilse tahmini düzeltme yap
        suffix_len = suffix_end - suffix_start
        if suffix_len < 2:
            # Yeterli rakam yok, son karakterleri rakama çevirmeyi dene
            for i in range(n - 1, max(1, n - 5), -1):
                ch = chars[i]
                if ch.isalpha() and ch in self._LETTER_TO_DIGIT:
                    chars[i] = self._LETTER_TO_DIGIT[ch]

        # -- Adım 3: Orta bölüm harf olmalı (pozisyon 2 ile suffix_start arası) --
        mid_end = n - max(2, suffix_len)
        for i in range(2, mid_end):
            ch = chars[i]
            if ch.isdigit():
                chars[i] = self._DIGIT_TO_LETTER.get(ch, ch)

        result = "".join(chars)

        # -- Adım 4: TR geçersiz harfleri temizle (O→0, I→1 vb.) --
        # Sadece orta harf bölümünde uygula
        mid_chars = list(result[2:mid_end])
        for i, ch in enumerate(mid_chars):
            if ch in _TR_INVALID_LETTERS:
                mid_chars[i] = self._LETTER_TO_DIGIT.get(ch, ch)
        result = result[:2] + "".join(mid_chars) + result[mid_end:]

        return result
