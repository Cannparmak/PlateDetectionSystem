"""
DB'deki eksik müşteri verilerini geçerli Türk formatında rastgele değerlerle doldurur.

Doldurduğu alanlar:
  - phone:  boşsa +90 5XX XXX XX XX formatında
  - tc_no:  boşsa geçerli TC algoritmasına uygun 11 haneli numara

Çalıştırma:
    python scripts/fill_missing_data.py
    python scripts/fill_missing_data.py --dry-run   # sadece göster, kaydetme
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Proje kök dizinini sys.path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.customer import Customer
from app.config import settings


# ---------------------------------------------------------------------------
# TC Kimlik No üretimi — resmi algoritma
# ---------------------------------------------------------------------------

def _generate_tc() -> str:
    """Geçerli Türk TC Kimlik Numarası üretir."""
    while True:
        # İlk 9 basamak: 1-9 ile başlar
        first = random.randint(1, 9)
        rest = [random.randint(0, 9) for _ in range(8)]
        d = [first] + rest

        # 10. basamak: (d[0]+d[2]+d[4]+d[6]+d[8])*7 - (d[1]+d[3]+d[5]+d[7]) mod 10
        d10 = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
        if d10 < 0:
            d10 += 10
        d.append(d10)

        # 11. basamak: sum(d[0:10]) mod 10
        d11 = sum(d) % 10
        d.append(d11)

        tc = "".join(str(x) for x in d)
        # Çift kontrol
        if len(tc) == 11 and tc[0] != "0":
            return tc


# ---------------------------------------------------------------------------
# Telefon üretimi — Türk GSM formatı
# ---------------------------------------------------------------------------

# Geçerli Türk GSM hat başlıkları (Turkcell/Vodafone/Türk Telekom)
_TR_GSM_PREFIXES = [
    "530", "531", "532", "533", "534", "535", "536", "537", "538", "539",
    "540", "541", "542", "543", "544", "545", "546", "547", "548", "549",
    "550", "551", "552", "553", "554", "555", "556", "557", "558", "559",
    "501", "502", "503", "504", "505", "506", "507",
    "510", "511", "512", "513", "514", "515", "516",
    "560", "561", "562",
    "570",
]

def _generate_phone(country_code: str = "+90") -> str:
    """Türk GSM numarası üretir: +90 5XX XXX XX XX"""
    prefix = random.choice(_TR_GSM_PREFIXES)
    suffix = "".join(str(random.randint(0, 9)) for _ in range(7))
    return f"{country_code}{prefix}{suffix}"


# ---------------------------------------------------------------------------
# Ana script
# ---------------------------------------------------------------------------

def main(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        customers = db.query(Customer).all()
        updated = 0

        for c in customers:
            changed = False

            if not c.phone or c.phone.strip() in ("", "None", "none"):
                new_phone = _generate_phone(settings.PHONE_COUNTRY_CODE)
                print(f"  Müşteri #{c.id} {c.full_name}: telefon -> {new_phone}")
                if not dry_run:
                    c.phone = new_phone
                changed = True

            if not c.tc_no or c.tc_no.strip() in ("", "None", "none"):
                new_tc = _generate_tc()
                print(f"  Müşteri #{c.id} {c.full_name}: TC -> {new_tc}")
                if not dry_run:
                    c.tc_no = new_tc
                changed = True

            if changed:
                updated += 1

        if updated == 0:
            print("Tüm müşterilerin telefon ve TC bilgisi dolu. Güncelleme gerekmedi.")
        elif dry_run:
            print(f"\n[DRY-RUN] {updated} müşteri güncellenecekti. Değişiklik kaydedilmedi.")
        else:
            db.commit()
            print(f"\n{updated} müşteri güncellendi.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eksik müşteri verilerini doldur")
    parser.add_argument("--dry-run", action="store_true", help="Sadece göster, kaydetme")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
