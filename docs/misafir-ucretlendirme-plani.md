# Sistem Yeniden Tasarım Planı — v2

**Tarih:** 2026-05-01  
**Durum:** Tartışma aşaması — onaydan sonra uygulanacak

---

## 1. Onaylanan Kararlar

| Karar | Detay |
|---|---|
| **Borç plakaya bağlanır** | Müşteri kaydı olmayan anonim araçlar da borç taşıyabilir |
| **Kasiyer rolü kaldırılıyor** | Sistemde yalnızca Admin ve Müşteri kalacak |
| **Giriş ekranı yeniden tasarlanıyor** | Tek landing page: Admin + Müşteri + Plaka Sorgula |
| **Müşteri paneli genişletiliyor** | Borç, abonelik, hareketler tek ekranda |
| **Aboneliği olmayan araç kapıdan geçer** | DENY → ALLOW_GUEST |
| **Ücretlendirme: dilim bazlı** | Türkiye standardı — hangi dilime düşüyorsa o dilimiın tam fiyatı |
| **Borç eşiği var** | Eşik altında engelleme yok, eşik üstünde giriş reddedilir |

---

## 2. Yeni Erişim Modeli

```
                    [ CanPark Ana Sayfa ]
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    Admin Girişi    Müşteri Girişi    Plaka Sorgula
    (e-posta+şifre) (e-posta+şifre)  (plaka no, login yok)
          │                │                │
          ▼                ▼                ▼
    Admin Paneli     Müşteri Paneli   Plaka Sonuç Sayfası
    (tüm yönetim)   (kişisel görünüm) (sadece okuma)
```

### 2.1 Admin (Yönetici)
- Mevcut `admin` + `kasiyer` yetkilerinin birleşimi
- Araç, müşteri, abonelik, ödeme, kamera, raporlar
- Otopark ayarları (saat başı ücret, kapasite vs.)

### 2.2 Müşteri
- Kendi araçları ve abonelikleri
- Abonelik süresi + kalan gün
- Giriş/çıkış geçmişi
- **YENİ: Araçlarının borç durumu**

### 2.3 Plaka Sorgulama (Login Gerektirmez)
- Herkes erişebilir (anonim ziyaretçi, abone, misafir)
- Plaka numarasını girer → anlık sonuç
- Gösterilenler: şu an içeride mi / ödenmemiş borçlar / toplam tutar
- Kişisel bilgi gösterilmez (isim, TC vs.) — sadece plakaya ait borç

---

## 3. Giriş Ekranı Yeni Tasarımı

**Mevcut durum:** `/login` → sadece personel girişi, altta müşteri portalı linki

**Yeni durum:** Tek sayfa, 3 kart yan yana (ya da sekmeli)

```
┌─────────────────────────────────────────────────────────┐
│                      C A N P A R K                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │              │  │              │  │              │  │
│  │  🔐 Admin    │  │  👤 Müşteri  │  │  🔍 Plaka    │  │
│  │   Girişi     │  │   Girişi     │  │  Sorgula     │  │
│  │              │  │              │  │              │  │
│  │  e-posta     │  │  e-posta     │  │  34 ABC 123  │  │
│  │  şifre       │  │  şifre       │  │              │  │
│  │              │  │              │  │  [Sorgula]   │  │
│  │  [Giriş Yap] │  │  [Giriş Yap] │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**URL değişiklikleri:**
- `/` → Yeni landing page (üç kart)
- `/login` → Sadece admin login (redirect `/` dan)
- `/musteri/login` → Sadece müşteri login (redirect `/` dan)
- `/plaka-sorgula` → GET (form) / POST veya query param ile sonuç

---

## 4. Müşteri Paneli — Yeni İçerik

**Mevcut:** Araçlar + abonelikler + giriş/çıkış geçmişi

**Yeni:** Aynı ekrana borç özeti de ekleniyor

```
┌────────────────────────────────────────────────────────┐
│  Merhaba, Ahmet Bey                                    │
├────────────────────────────────────────────────────────┤
│  ARAÇLARIM                                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 34 ABC 1234  │  Abonelik: Aylık (18 gün kaldı)  │  │
│  │              │  Borç: ₺0  ✓                     │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 34 XYZ 5678  │  Abonelik: Yok                   │  │
│  │              │  Borç: ₺75  ⚠  [Detay]           │  │
│  └─────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│  SON HAREKETLERİM                                      │
│  01.05.2026  09:15 giriş → 11:30 çıkış  (2s 15dk)     │
│  30.04.2026  14:00 giriş → 16:45 çıkış  (2s 45dk) ₺45 │
└────────────────────────────────────────────────────────┘
```

---

## 5. Plaka Sorgula Sayfası

**URL:** `/plaka-sorgula?plaka=34ABC1234` (ya da POST form)

### Senaryo A — Aboneli araç, içeride değil, borç yok:
```
Plaka: 34 ABC 1234
━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Aktif abonelik var — Aylık Plan
  Bitiş: 18 Mayıs 2026 (18 gün kaldı)
  Araç şu an otoparkta değil.
  Ödenmemiş borç: ₺0
```

### Senaryo B — Anonim araç, şu an içeride:
```
Plaka: 34 DEF 9999
━━━━━━━━━━━━━━━━━━━━━━━━━
🚗 Araç şu an otoparkta
  Giriş: 01.05.2026 saat 10:30
  Geçen süre: 1 saat 45 dakika
  Tahmini ücret: ₺45 (çıkışta kesinleşir)

Ödenmemiş geçmiş borç: ₺75
  → 28.04.2026 — 3 saat 0 dk — ₺45
  → 25.04.2026 — 1 saat 30 dk — ₺30

Toplam borç: ₺75
(Ödeme için lütfen güvenlik birimine başvurun)
```

### Senaryo C — Sistemde hiç kayıt yok:
```
Plaka: 06 ZZZ 0000
━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ Bu plakaya ait kayıt bulunamadı.
  Sisteme hiç giriş yapılmamış.
```

---

## 6. Ücretlendirme Modeli — Dilim Bazlı (Türkiye Standardı)

### 6.1 Nasıl Çalışır?

Araç hangi zaman dilimine giriyorsa **o dilimiın sabit ücretini öder**.  
1 dakika geç kalma bile üst dilime geçirir — dakika bazlı değil, dilim bazlı.

```
Araç 1 saat 1 dakika kaldı → "1–2 Saat" dilimine girer → ₺80 öder
Araç 2 saat 0 dakika kaldı → "1–2 Saat" dilimine girer → ₺80 öder
Araç 2 saat 1 dakika kaldı → "2–4 Saat" dilimine girer → ₺120 öder
```

### 6.2 Araştırma Bulguları — Türkiye Fiyatları

**Kaynak: İSPARK 2026, Empark, UlaşımPark gerçek tarifeleri**

İSPARK bölgesel fiyatlandırma kullanıyor (merkez pahalı, dış ilçeler ucuz):

| Bölge | 0-1 saat | 1-2 saat | 2-4 saat | 4-8 saat | 8-12 saat | 12-24 saat |
|---|---|---|---|---|---|---|
| Premium (Fatih, Kadıköy) | ₺200 | ₺240 | ₺300 | ₺380 | ₺480 | ₺650 |
| Merkez (Beşiktaş, Şişli) | ₺140 | ₺180 | ₺230 | ₺280 | ₺370 | ₺450 |
| **Orta (Beykoz, Ataşehir)** | **₺110** | **₺140** | **₺170** | **₺220** | **₺260** | **₺370** |
| Dış (Esenyurt, Başakşehir) | ₺80 | ₺100 | ₺110 | ₺140 | ₺210 | ₺260 |

**Not:** Beykoz Üniversitesi konumuna göre "Orta" bölge fiyatları referans alındı.

Özel operatör (AkMerkez AVM örneği):
- 0-30 dk: Ücretsiz
- 30dk-1 saat: ₺60
- 1-2 saat: ₺90
- 2-3 saat: ₺110
- 3-4 saat: ₺130
- 4-6 saat: ₺150
- 8-12 saat: ₺250
- 12-24 saat: ₺400

### 6.3 Sisteme Önerilen Varsayılan Tarife

Admin panelinden değiştirilebilir olacak. Varsayılan değerler:

| # | Dilim Adı | Süre (dakika) | Ücret (₺) |
|---|---|---|---|
| 1 | Ücretsiz (tolerans) | 0 – 30 dk | ₺0 |
| 2 | İlk 1 Saat | 30 dk – 1 saat | ₺50 |
| 3 | 1–2 Saat | 1 saat – 2 saat | ₺80 |
| 4 | 2–4 Saat | 2 saat – 4 saat | ₺120 |
| 5 | 4–8 Saat | 4 saat – 8 saat | ₺180 |
| 6 | 8–12 Saat | 8 saat – 12 saat | ₺250 |
| 7 | Günlük Tavan | 12 saat – 24 saat | ₺350 |

**24 saati aşarsa:** Her gün için günlük tavan (₺350) çarpı gün sayısı.

### 6.4 Hesaplama Algoritması

```python
def calculate_fee(duration_minutes: int, brackets: list[ParkingRateBracket]) -> float:
    """
    duration_minutes: giriş - çıkış farkı (dakika)
    brackets: min_minutes, max_minutes, price ile sıralı liste
    """
    if duration_minutes <= 0:
        return 0.0
    
    # Gün sayısını hesapla (24 saatten uzun kalışlar için)
    full_days = duration_minutes // (24 * 60)
    remaining_minutes = duration_minutes % (24 * 60)
    
    # Kalan dakika için dilim bul
    daily_max = brackets[-1].price  # Son dilim = günlük tavan
    
    day_fee = 0.0
    for bracket in brackets:
        if bracket.min_minutes < remaining_minutes <= bracket.max_minutes:
            day_fee = bracket.price
            break
    
    return (full_days * daily_max) + day_fee
```

**Örnekler:**

| Kalış Süresi | Hesaplama | Ücret |
|---|---|---|
| 20 dakika | ≤ 30dk → tolerans | **₺0** |
| 45 dakika | 30dk-1 saat dilimi | **₺50** |
| 1 saat 0 dakika | 30dk-1 saat dilimi | **₺50** |
| 1 saat 1 dakika | 1-2 saat dilimi | **₺80** |
| 3 saat 59 dakika | 2-4 saat dilimi | **₺120** |
| 7 saat | 4-8 saat dilimi | **₺180** |
| 25 saat | 1 gün (₺350) + 1 saatlik kalış (₺50) | **₺400** |

### 6.5 Yeni Veritabanı Tablosu: `parking_rate_brackets`

```python
class ParkingRateBracket(Base):
    __tablename__ = "parking_rate_brackets"
    
    id            = Column(Integer, primary_key=True)
    name          = Column(String(100))           # "İlk 1 Saat", "1-2 Saat"
    min_minutes   = Column(Integer, nullable=False) # Dilimiın başlangıcı (dahil değil)
    max_minutes   = Column(Integer, nullable=False) # Dilimiın bitişi (dahil)
    price         = Column(Float, nullable=False)   # ₺ cinsinden sabit ücret
    display_order = Column(Integer, default=0)      # Sıralama
    is_active     = Column(Boolean, default=True)
```

**Dikkat:** `hourly_rate` ve `grace_period_minutes` `parking_config`'den kaldırılır,  
yerine bu tablo gelir. Admin panelinden dilimler eklenip düzenlenebilir olacak.

---

## 6b. Borç Eşiği — Giriş Engelleme Mantığı

```
Araç girişe gelir
    │
    ▼
Ödenmemiş borç hesaplanır
    │
    ├── Borç < eşik değeri (varsayılan: ₺500)
    │       → Normal giriş, ALLOW_GUEST
    │       → UI'da sarı uyarı: "₺X borcunuz var"
    │
    └── Borç ≥ eşik değeri
            → GİRİŞ REDDEDİLİR (DENY_DEBT)
            → UI'da kırmızı: "Ödenmemiş borcunuz nedeniyle giriş yapılamaz"
            → Plaka sorgula sayfasına yönlendirme
```

**`parking_config`'e eklenecek alan:**
```python
debt_block_threshold = Column(Float, default=500.0)  # ₺ — Bu değer üzeri engel
```

Admin istediği eşiği ayarlayabilir (₺0 = her borçlu engellenir, NULL = hiç engelleme yok).

---

## 6c. Veritabanı Değişiklikleri (güncellenmiş)

### 6.1 `users` tablosu — kasiyer kaldırma
```python
# ÖNCE:
role = Column(Enum("admin", "kasiyer"), default="kasiyer")

# SONRA:
role = Column(Enum("admin"), default="admin")
```
**Migration notu:** Mevcut `kasiyer` kayıtları `admin` yapılarak migrate edilir.

### 6.2 `vehicles` tablosu — 2 yeni alan
```python
customer_id   = Column(Integer, ForeignKey("customers.id"), nullable=True)  # NULL = anonim
is_anonymous  = Column(Boolean, default=False, nullable=False)
```

### 6.3 `parking_sessions` tablosu — fee alanları
```python
is_guest              = Column(Boolean, default=False)
fee_amount            = Column(Float, nullable=True)        # NULL = abone, 0 = tolerans
is_paid               = Column(Boolean, default=False)
paid_at               = Column(DateTime, nullable=True)
payment_method        = Column(String(50), nullable=True)   # nakit / kredi_karti
processed_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)
```

### 6.4 `parking_config` tablosu — 1 yeni alan (eski hourly_rate kaldırılıyor)
```python
# KALDIRILAN: hourly_rate, grace_period_minutes, min_billable_minutes, max_daily_rate
# Bunların hepsi artık parking_rate_brackets tablosundan geliyor

# EKLENEN:
debt_block_threshold = Column(Float, default=500.0)  # ₺ — Bu tutarı aşan borçta giriş engeli
```

### 6.5 YENİ TABLO: `parking_rate_brackets`
```python
class ParkingRateBracket(Base):
    __tablename__ = "parking_rate_brackets"
    
    id            = Column(Integer, primary_key=True)
    name          = Column(String(100), nullable=False)   # "İlk 1 Saat", "1–2 Saat"
    min_minutes   = Column(Integer, nullable=False)       # Başlangıç dakikası (dahil değil)
    max_minutes   = Column(Integer, nullable=False)       # Bitiş dakikası (dahil)
    price         = Column(Float, nullable=False)         # Sabit ücret (₺)
    display_order = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)
```

**Seed verisi (varsayılan tarife):**
```python
brackets = [
    {"name": "Ücretsiz",    "min_minutes": 0,    "max_minutes": 30,   "price": 0,   "display_order": 1},
    {"name": "İlk 1 Saat",  "min_minutes": 30,   "max_minutes": 60,   "price": 50,  "display_order": 2},
    {"name": "1–2 Saat",    "min_minutes": 60,   "max_minutes": 120,  "price": 80,  "display_order": 3},
    {"name": "2–4 Saat",    "min_minutes": 120,  "max_minutes": 240,  "price": 120, "display_order": 4},
    {"name": "4–8 Saat",    "min_minutes": 240,  "max_minutes": 480,  "price": 180, "display_order": 5},
    {"name": "8–12 Saat",   "min_minutes": 480,  "max_minutes": 720,  "price": 250, "display_order": 6},
    {"name": "Günlük Tavan","min_minutes": 720,  "max_minutes": 1440, "price": 350, "display_order": 7},
]
```

---

## 7. Borç Mantığı

**Borç → plakaya bağlı, müşteriye değil.**

```
Plaka: 34 ABC 1234
  └── Vehicle kaydı (anonim veya kayıtlı)
        └── ParkingSession'lar
              ├── session #1: is_paid=True, fee=₺45
              ├── session #2: is_paid=False, fee=₺30  ← BORÇ
              └── session #3: is_paid=False, fee=₺45  ← BORÇ
              
Toplam borç = ₺75 (is_paid=False olanların toplamı)
```

Müşteri sisteme kayıtlıysa aynı plakaya sahip araçlar müşteri üzerinden de görünür,  
ama borç verisi direkt `vehicle_id` → `parking_sessions` zincirinden gelir.

---

## 8. Kasiyer Rolü Kaldırma — Etki Analizi

Kaldırılacak / değiştirilecek dosyalar:

| Dosya | Değişiklik |
|---|---|
| `app/models/user.py` | `Enum("admin", "kasiyer")` → `Enum("admin")` |
| `app/dependencies.py` | `require_kasiyer()` dependency silinir, tüm yetkiler admin'de |
| `app/routers/admin.py` | Kasiyer kontrolü olan `if role == "kasiyer"` blokları |
| `app/templates/dashboard/kasiyer.html` | Dosya silinir |
| `app/templates/index.html` | Yeni landing page ile değiştirilir |
| `app/templates/auth/login.html` | Yeni 3-kart tasarımına taşınır |
| `scripts/seed_db.py` | Kasiyer seed verisi kaldırılır |

---

## 9. Yeni Endpoint Özeti

| Endpoint | Yöntem | Auth | Amaç |
|---|---|---|---|
| `/` | GET | Yok | Yeni landing page (3 kart) |
| `/plaka-sorgula` | GET/POST | Yok | Plaka sorgulama + borç göster |
| `/admin/debts` | GET | Admin | Tüm ödenmemiş borçlar listesi |
| `/admin/debts/{session_id}/pay` | POST | Admin | Ödeme tahsilatı |
| `/api/plaka-sorgula/{plate}` | GET | Yok | JSON API (ileride kiosk için) |
| `/musteri/debts` | GET | Müşteri | Kendi araçlarının borçları |

---

## 10. OCR İyileştirme Planı

### 10.1 Mevcut Durum — Ne Var, Ne Yok?

**Araştırma ve kod incelemesi sonucu** ([src/ocr/reader.py](../src/ocr/reader.py), [src/postprocess/text_cleaner.py](../src/postprocess/text_cleaner.py)):

| Teknik | Durum | Konum |
|---|---|---|
| CLAHE (adaptif kontrast) | ✅ Var | `reader._preprocess_bgr` |
| Bilateral filtre | ✅ Var | `reader._preprocess_bgr` |
| Upscale + keskinleştirme | ✅ Var | `reader._preprocess_bgr` |
| Dual-model oylama | ✅ Var | `reader.read()` |
| Karakter bazlı oylama | ✅ Var | `reader._char_vote()` |
| Pozisyon bazlı OCR düzeltme | ✅ Var | `text_cleaner.fix_ocr_errors()` |
| Format doğrulama (regex) | ✅ Var | `text_cleaner.validate()` |
| **Deskewing (eğiklik düzeltme)** | ❌ Yok | — |
| **Multi-frame oylama (zamansal)** | ❌ Yok | — |
| **`to_display()` format fonksiyonu** | ❌ Yok | — |
| Adaptive threshold + morfoloji | ❌ Yok | — |

### 10.2 Plaka Görüntü Formatı: "34 ABC 1234"

**Sorun:** `PlateCleaner.clean()` tüm boşlukları silip `34ABC1234` döndürüyor. Görüntüleme için `34 ABC 1234` formatına çeviren fonksiyon yok.

**Çözüm:** `to_display()` metodu eklenmeli — [src/postprocess/text_cleaner.py](../src/postprocess/text_cleaner.py):
```python
def to_display(self, normalized: str) -> str:
    """
    Normalize edilmiş Türk plakasını görüntü formatına çevirir.
    "34ABC1234"  → "34 ABC 1234"
    "06AB1234"   → "06 AB 1234"
    "81YZ99"     → "81 YZ 99"
    """
    m = re.fullmatch(r'(\d{2})([ABCDEFGHJKLMNPRSTUVYZ]{1,3})(\d{2,4})', normalized)
    if m:
        return f"{m.group(1)} {m.group(2)} {m.group(3)}"
    return normalized  # TR formatına uymuyorsa olduğu gibi
```

Bu fonksiyon şu yerlerde kullanılacak:
- `Vehicle.plate_display` kaydedilirken (şu an elle giriliyor, otomatik olacak)
- Kamera panelinde sonuç gösterirken
- Plaka sorgulama sonuç sayfasında
- Müşteri panelinde araç listesinde

### 10.3 Deskewing — Eğik Plaka Düzeltme

Kamera açısı veya araç pozisyonu nedeniyle plaka eğik yakalanabilir. ±15° içindeki eğiklikler Hough çizgi tespiti ile düzeltilebilir:

**Eklenecek yer:** `reader._preprocess_bgr()` içinde, CLAHE'den önce:
```python
@staticmethod
def _deskew(bgr: np.ndarray) -> np.ndarray:
    gray  = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180,
                            threshold=30, minLineLength=20, maxLineGap=8)
    if lines is None:
        return bgr
    angles = [
        np.degrees(np.arctan2(y2 - y1, x2 - x1))
        for x1, y1, x2, y2 in lines[:, 0]
        if abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) < 15
    ]
    if not angles:
        return bgr
    angle = float(np.median(angles))
    h, w  = bgr.shape[:2]
    M     = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(bgr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
```

### 10.4 Multi-Frame Konsensüs Oylama (Zamansal)

Şu an sadece **iki model arasında** oylama var. Asıl güç ise **video akışından aynı plaka N kez okunup sonuçlar birleştirildiğinde** ortaya çıkıyor (araştırma: %15-25 iyileştirme).

**Eklenecek yer:** `src/pipeline.py` — yeni `PlateVoter` iç sınıfı:
```python
class PlateVoter:
    """Son N karedeki OCR sonuçlarını karakter bazlı oylama ile birleştirir."""
    
    def __init__(self, window: int = 5):
        self._window  = window
        self._history: list[tuple[str, float]] = []  # (plate_text, confidence)
    
    def add(self, text: str, confidence: float) -> None:
        self._history.append((text, confidence))
        if len(self._history) > self._window:
            self._history.pop(0)
    
    def best(self) -> str | None:
        """Güven ağırlıklı karakter bazlı oylama."""
        valid = [(t, c) for t, c in self._history if t]
        if not valid:
            return None
        max_len = max(len(t) for t, _ in valid)
        result  = []
        for i in range(max_len):
            votes: dict[str, float] = {}
            for text, conf in valid:
                if i < len(text):
                    votes[text[i]] = votes.get(text[i], 0) + conf
            if votes:
                result.append(max(votes, key=votes.get))
        return "".join(result) if result else None
    
    def reset(self) -> None:
        self._history.clear()
```

WebSocket entry/exit handler'da her frame sonrası `voter.add(plate_text, confidence)` çağrılacak; yeterli kare birikince `voter.best()` ile karar verilecek.

### 10.5 Öngörülen İyileşme

| Teknik | Tahmini Katkı | Zorluk |
|---|---|---|
| `to_display()` formatı | Görünüm ✓ | Çok kolay |
| Deskewing | +%5-10 doğruluk | Orta |
| Multi-frame oylama | +%15-25 doğruluk | Orta |
| Adaptive threshold + morfoloji | +%3-8 doğruluk | Kolay |

**Toplam beklenen iyileşme:** Mevcut baseline'a göre **+%20-35** doğruluk artışı.

---

## 11. Uygulama Sırası

### Faz 0 — OCR İyileştirme (önce bu, diğer değişiklikler daha az riskli)
1. `text_cleaner.py` → `to_display()` metodu ekle
2. Tüm plaka kayıt/gösterim noktalarını `to_display()` ile güncelle
3. `reader.py` → `_deskew()` ekle, `_preprocess_bgr`'a entegre et
4. `pipeline.py` → `PlateVoter` sınıfı ekle
5. `camera.py` WebSocket handler → voter entegrasyonu

### Faz 1 — Temizlik ve Altyapı
6. Kasiyer rolünü kaldır (User model, dependencies, templates)
7. DB migration: `vehicles.customer_id` nullable, `vehicles.is_anonymous`
8. DB migration: `parking_sessions` fee alanları
9. DB migration: `parking_config.debt_block_threshold`
10. Yeni tablo: `parking_rate_brackets` + seed verisi
11. `fee_calculator.py` servisi yaz

### Faz 2 — Çekirdek Mantık
12. `plate_checker.py` → misafir/anonim giriş-çıkış
13. Plaka sorgulama endpoint (`/plaka-sorgula`)
14. Ödeme tahsilatı endpoint (`/admin/debts`)

### Faz 3 — Arayüz
15. Landing page yeniden tasarımı (3 kart)
16. Müşteri paneline borç özeti
17. Admin borç listesi sayfası
18. Kamera panelinde misafir badge + ücret gösterimi

---

## 11. Kararlaşan Noktalar ✓ ve Açık Sorular

### Kararlaşanlar ✓
| Karar | Detay |
|---|---|
| Ücretlendirme modeli | Dilim bazlı (bracket) — Türkiye standardı |
| Borç eşiği | Var — varsayılan ₺500, admin değiştirebilir |
| Çıkış modeli | Kapı her zaman açılır, borç sonra tahsil |
| Kasiyer rolü | Kaldırılıyor |
| 24 saat üzeri kalış | Günlük tavan × gün sayısı |
| Ücret hesaplama zamanı | Çıkış anındaki aktif tarife kullanılır |

### Hâlâ Açık
| # | Soru | Seçenekler |
|---|---|---|
| 1 | Anonim araç çıkışta dilim görünsün mü kamera panelinde? | "Ücret: ₺120 (2-4 Saat dilimi)" gibi |
| 2 | Anonim araçlara ileride müşteri eşleştirme? | Plaka + TC ile birleştirme (sonraki faz) |
| 3 | Plaka sorgulama sayfasına CAPTCHA? | İlk aşamada hayır |
| 4 | Admin dilim tarifesini UI'dan düzenleyebilmeli mi? | Önerilir, Faz 3'e eklenebilir |
