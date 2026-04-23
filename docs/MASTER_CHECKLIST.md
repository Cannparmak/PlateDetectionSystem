# PLATEDETECTIONSYSTEM — OTOPARK YÖNETİM SİSTEMİ
## Senior Software Architect — Master Geliştirme Planı

**Proje Tipi:** Bitirme Projesi — Otopark Yönetim + AI Plaka Tespit Sistemi  
**Deployment:** Local  
**Güncelleme:** 2026-04-03  

---

## PROJE TANIMI

Yapay zeka destekli otopark yönetim sistemi. Kamera girişte/çıkışta araç plakasını otomatik okur, abonelik durumunu kontrol eder ve giriş/çıkış kaydı tutar. Web arayüzü üzerinden müşteri kaydı, araç ve abonelik yönetimi, ödeme simülasyonu ve raporlama yapılır.

**Temel İş Akışı:**
```
Araç Gelir → Kamera Plakayı Okur → Abonelik Kontrolü
     ↓ Abonelik Var                    ↓ Abonelik Yok
Giriş Kaydı + Session Başlat    Uyarı / Kasiyer Bildirimi
     ↓
Araç Çıkar → Kamera Okur → Session Kapat → Log Kaydı
```

---

## MİMARİ KARAR ÖZETİ

| Alan | Seçim | Gerekçe |
|------|-------|---------|
| Backend | FastAPI (async Python) | En hızlı Python framework, WebSocket, az kaynak |
| Frontend | Jinja2 + Alpine.js + Tailwind CSS | Node.js gerektirmez, tek process, ultra hafif |
| Realtime | WebSocket | Canlı kamera akışı + anlık bildirimler |
| Veritabanı | SQLite + SQLAlchemy ORM | Local, sıfır konfigürasyon, ilişkisel |
| Detector | YOLOv11s (upgrade) | Nano'dan %3-5 daha iyi mAP |
| OCR | EasyOCR (çoklu dil) | Global plaka desteği |
| Ödeme | Simülasyon (kart animasyonu) | Bitirme projesi |

---

## DOMAIN MODELİ (İŞ MANTIĞI)

```
ROLLER:
├── Admin      → Tam yetki: sistem yönetimi, raporlar, kullanıcı yönetimi
├── Kasiyer    → Giriş/çıkış işlemleri, müşteri kaydı, abonelik satışı
└── Müşteri    → Kendi aracı ve aboneliğini görür, uzatma yapabilir

İLİŞKİLER:
├── Customer (müşteri kişi bilgileri)
│       └──[1:N]── Vehicle (plaka, araç tipi)
│                      └──[1:N]── Subscription (plan, tarih, durum)
│                      └──[1:N]── ParkingSession (giriş/çıkış kayıtları)
│
├── SubscriptionPlan (saatlik, günlük, haftalık, aylık, 3aylık, yıllık + fiyat)
├── ParkingConfig (toplam kapasite, güncel doluluk)
└── User (staff: admin + kasiyer, ayrı tablodan)
```

---

## PROJE KLASÖR YAPISI (HEDEF)

```
PlateDetectionSystem/
├── app/                          ← FastAPI uygulaması
│   ├── main.py                   ← Entry point, startup events
│   ├── config.py                 ← Ayarlar (.env okuma)
│   ├── database.py               ← SQLAlchemy engine + session
│   ├── dependencies.py           ← get_db, get_current_user, require_admin vb.
│   │
│   ├── models/                   ← ORM (DB tabloları)
│   │   ├── __init__.py
│   │   ├── user.py               ← Staff kullanıcılar (admin/kasiyer)
│   │   ├── customer.py           ← Otopark müşterileri
│   │   ├── vehicle.py            ← Müşteriye ait araçlar + plaka
│   │   ├── subscription_plan.py  ← Abonelik planları (saatlik/aylık vb.)
│   │   ├── subscription.py       ← Araç-Plan bağlantısı, tarihler
│   │   ├── parking_session.py    ← Giriş/çıkış kayıtları
│   │   └── parking_config.py     ← Otopark kapasitesi
│   │
│   ├── routers/                  ← API endpoint grupları
│   │   ├── __init__.py
│   │   ├── auth.py               ← /login, /logout, /register (müşteri)
│   │   ├── dashboard.py          ← /dashboard (rol bazlı yönlendirme)
│   │   ├── camera.py             ← /camera, /ws/stream (WebSocket)
│   │   ├── customers.py          ← /customers CRUD
│   │   ├── vehicles.py           ← /vehicles CRUD
│   │   ├── subscriptions.py      ← /subscriptions CRUD + abonelik satışı
│   │   ├── sessions.py           ← /sessions giriş/çıkış + geçmiş
│   │   ├── payment.py            ← /payment simülasyon
│   │   └── admin.py              ← /admin yönetim paneli
│   │
│   ├── services/                 ← İş mantığı
│   │   ├── __init__.py
│   │   ├── detector.py           ← YOLO detection servisi
│   │   ├── ocr_service.py        ← EasyOCR servisi
│   │   ├── pipeline.py           ← Detect + OCR birleşik
│   │   ├── auth_service.py       ← JWT + bcrypt
│   │   ├── plate_checker.py      ← Plaka → abonelik kontrolü (ana iş mantığı)
│   │   └── session_service.py    ← Giriş/çıkış session yönetimi
│   │
│   ├── schemas/                  ← Pydantic modelleri
│   │   ├── auth.py
│   │   ├── customer.py
│   │   ├── vehicle.py
│   │   ├── subscription.py
│   │   ├── session.py
│   │   └── detection.py
│   │
│   ├── templates/                ← Jinja2 HTML
│   │   ├── base.html
│   │   ├── index.html            ← Landing page
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html     ← Müşteri kayıt
│   │   ├── dashboard/
│   │   │   ├── admin.html        ← Admin dashboard
│   │   │   ├── kasiyer.html      ← Kasiyer dashboard
│   │   │   └── musteri.html      ← Müşteri dashboard
│   │   ├── camera/
│   │   │   └── live.html         ← Canlı kamera + tespit
│   │   ├── customers/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── form.html
│   │   ├── vehicles/
│   │   │   ├── list.html
│   │   │   └── form.html
│   │   ├── subscriptions/
│   │   │   ├── plans.html        ← Plan seçim sayfası
│   │   │   ├── list.html
│   │   │   └── new.html
│   │   ├── sessions/
│   │   │   └── history.html      ← Giriş/çıkış geçmişi
│   │   ├── payment/
│   │   │   ├── checkout.html     ← Kart animasyonu ödeme
│   │   │   └── success.html      ← Başarılı ödeme
│   │   └── admin/
│   │       ├── dashboard.html
│   │       ├── users.html
│   │       └── reports.html
│   │
│   └── static/
│       ├── css/custom.css
│       ├── js/
│       │   ├── alpine.min.js
│       │   ├── chart.min.js
│       │   └── app.js            ← Kamera, animasyonlar, genel JS
│       └── img/logo.svg
│
├── src/                          ← ML modülleri
│   ├── detection/detector.py
│   ├── ocr/reader.py
│   ├── postprocess/text_cleaner.py
│   └── utils/
│
├── data/                         ← Dataset
├── scripts/                      ← Eğitim scriptleri
├── models/                       ← Model ağırlıkları
├── docs/
├── tests/
├── .env.example
├── requirements.txt
└── run.py
```

---

# ============================================================
# PHASE 0 — HAZIRLIK VE ORTAM
# ============================================================

## [ ] 0.1 Ortam Doğrulama

- [ ] Python sürümü kontrol: `python --version` (3.10+ gerekli)
- [ ] GPU durumu: `python -c "import torch; print(torch.cuda.is_available())"`
- [ ] Disk alanı kontrol (min 15GB — dataset + model + DB)
- [ ] Mevcut `best.pt` → `models/plate_detector_v1_ccpd.pt` olarak yedekle
- [ ] `.venv` aktif et

## [ ] 0.2 requirements.txt Güncelleme

```txt
# Web Framework
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
jinja2>=3.1.3
python-multipart>=0.0.9
aiofiles>=23.2.1

# Auth & Security
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
python-dotenv>=1.0.1

# Database
sqlalchemy>=2.0.30
alembic>=1.13.0

# ML / Detection
ultralytics>=8.2.0
easyocr>=1.7.1
opencv-python>=4.9.0
torch>=2.3.0
torchvision>=0.18.0

# Utils
numpy>=1.26.0
pillow>=10.3.0
pandas>=2.2.0

# Testing
pytest>=8.2.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

## [ ] 0.3 .env.example Oluştur

```env
APP_NAME=OtoparkPro
SECRET_KEY=change-this-in-production-super-secret
DATABASE_URL=sqlite:///./otopark.db
MODEL_PATH=models/plate_detector_global_v1.pt
UPLOAD_DIR=outputs/uploads
RESULTS_DIR=outputs/results
MAX_UPLOAD_MB=20
OCR_LANGUAGES=tr,en,de,fr
ADMIN_EMAIL=admin@otopark.local
ADMIN_PASSWORD=admin123
KASIYER_EMAIL=kasiyer@otopark.local
KASIYER_PASSWORD=kasiyer123
PARKING_CAPACITY=100
```

---

# ============================================================
# PHASE 1 — GLOBAL DATASET VE MODEL İYİLEŞTİRME
# ============================================================

## [ ] 1.1 Global Dataset İndirilmesi

### DATASET A — Roboflow License Plate Recognition
- **İndirme:** `https://universe.roboflow.com/roboflow-universe-projects/license-plate-recognition-rxg4e`
- **Görüntü:** ~8,823 (train/val/test hazır)
- **Format:** YOLO v8 (direkt kullanılabilir)
- **Lisans:** CC BY 4.0
- [ ] Roboflow hesabı aç (ücretsiz)
- [ ] API key al → YOLO formatında indir
- [ ] `data/raw/roboflow_lp/` klasörüne çıkart

### DATASET B — CCPD 2019 (mevcut + genişletilmiş)
- **Mevcut:** 2,983 Çin plakası görüntüsü
- [ ] Mevcut `scripts/01_prepare_ccpd_sample.py` → `n=15000` ile yeniden çalıştır
- [ ] `data/interim/ccpd_sample_15k/` olarak kaydet

### DATASET C — UC3M-LP (Avrupa plakaları)
- **İndirme:** `https://github.com/ramajoballester/UC3M-LP`
- **Görüntü:** ~1,975 İspanya/Avrupa plakası
- [ ] GitHub'dan clone et
- [ ] YOLO formatına dönüştürme script'i yaz
- [ ] `data/raw/uc3m_lp/` klasörüne çıkart

### Hedef Dataset Boyutları:

| Dataset | Görüntü | Kapsam |
|---------|---------|--------|
| Roboflow LP Recognition | ~8,823 | Global |
| CCPD 2019 (subset) | ~15,000 | Asya/Çin |
| UC3M-LP | ~1,975 | Avrupa |
| **TOPLAM** | **~25,800** | **Global** |

## [ ] 1.2 Dataset Birleştirme ve Hazırlık

- [ ] Yeni script: `scripts/01b_merge_datasets.py`
  - Tüm kaynaklardan görüntü + label topla
  - Duplicate kontrolü (md5 hash)
  - Label format: hepsi `0 cx cy w h` (class=0, "plate")
  - Görüntü format standardizasyonu (RGB JPEG)
- [ ] Yeni split: 80% train / 10% val / 10% test
  - Her kaynaktan orantılı alım (stratified)
- [ ] `scripts/03_split_dataset.py` güncelle
- [ ] Kalite kontrol:
  - [ ] Boş label dosyası → kaldır
  - [ ] Koordinat 0-1 aralığı kontrolü
  - [ ] Görüntü-label eşleşme
  - [ ] 20 rastgele görsel görselleştir

## [ ] 1.3 Yeni Model Eğitimi (YOLOv11s)

`scripts/04_train_yolo.py` güncellenecek:

```python
from ultralytics import YOLO

model = YOLO("yolo11s.pt")   # nano → small

model.train(
    data="data/processed/yolo_plate_global_v2/dataset.yaml",
    epochs=100,
    imgsz=1280,          # 640 → 1280 (küçük nesne kritik)
    batch=8,             # 1280 imgsz için
    device=0,            # GPU varsa, yoksa "cpu"
    patience=20,         # Early stopping
    optimizer="AdamW",
    lr0=0.001,
    lrf=0.01,
    warmup_epochs=5,
    
    # Augmentation
    degrees=15,          # Açı (rampalı park yerleri)
    perspective=0.002,   # Perspektif (kamera açısı)
    mosaic=1.0,
    mixup=0.15,
    copy_paste=0.1,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    blur=0.01,           # Bulanık (hızlı araç)
    
    project="runs/detect",
    name="plate_global_v1",
    save_period=10,
    plots=True,
)
```

### Hedef Metrikler:

| Metrik | Mevcut | Hedef |
|--------|--------|-------|
| mAP50 | 99.31% | **> 99.5%** |
| mAP50-95 | 88.85% | **> 92%** |
| Precision | 99.32% | > 99.4% |
| Recall | 99.66% | > 99.6% |

## [ ] 1.4 Model Değerlendirme ve Export

- [ ] Test seti üzerinde inference
- [ ] Confusion matrix inceleme
- [ ] Yanlış tespitleri manuel incele
- [ ] Koşul testleri: gece, bulanık, uzak, açılı, çoklu araç
- [ ] **ONNX Export** (CPU inference için daha hızlı):
  ```python
  model.export(format="onnx", simplify=True, imgsz=1280)
  ```
- [ ] Model yedekleme: `models/plate_detector_global_v1.pt`

---

# ============================================================
# PHASE 2 — ML MODÜLLERI (src/)
# ============================================================

## [ ] 2.1 PlateDetector Sınıfı (`src/detection/detector.py`)

```python
@dataclass
class Detection:
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    crop: np.ndarray                 # Kırpılmış plaka

class PlateDetector:
    def __init__(self, model_path: str, conf: float = 0.35, device: str = "auto")
    def detect(self, image: np.ndarray) -> list[Detection]
    def detect_file(self, path: str) -> list[Detection]
    def warmup(self)                 # Startup'ta çalıştır
```

- [ ] Model lazy loading (ilk kullanımda yükle)
- [ ] Model warm-up (dummy inference)
- [ ] Confidence threshold: 0.35 (otopark için yüksek tutulmalı — FP istemeyiz)
- [ ] Device otomatik: CUDA > CPU

## [ ] 2.2 PlateOCR Sınıfı (`src/ocr/reader.py`)

```python
@dataclass
class OCRResult:
    text: str              # Ham metin
    cleaned_text: str      # Temizlenmiş
    confidence: float
    format_valid: bool     # Plaka formatı geçerli mi

class PlateOCR:
    def __init__(self, languages: list[str], gpu: bool = False)
    def read(self, crop: np.ndarray) -> OCRResult
    def read_batch(self, crops: list[np.ndarray]) -> list[OCRResult]
```

- [ ] EasyOCR reader singleton
- [ ] Diller: `['tr', 'en', 'de', 'fr', 'es', 'pl', 'nl']` (global kapsam)
- [ ] Görüntü ön işleme (OCR öncesi):
  - Gri tonlama
  - CLAHE kontrast artırma
  - Adaptive threshold
  - 2x upscale (küçük plakalar için)
- [ ] GPU varsa otomatik aktif

## [ ] 2.3 Metin Temizleyici (`src/postprocess/text_cleaner.py`)

```python
class PlateCleaner:
    FORMATS = {
        "TR": r"^[0-9]{2}[A-Z]{1,3}[0-9]{2,4}$",
        "EU_GENERIC": r"^[A-Z0-9]{2,8}$",
        "US": r"^[A-Z0-9]{5,7}$",
    }
    
    OCR_FIXES = {
        "0": ["O", "Q"], "1": ["I", "L"],
        "5": ["S"], "8": ["B"], "2": ["Z"]
    }
    
    def clean(self, raw: str) -> str
    def validate(self, text: str) -> tuple[bool, str]  # (valid, format_name)
```

- [ ] Boşluk + özel karakter kaldırma
- [ ] Türk plaka regex: `34 ABC 1234` → `34ABC1234` (normalize)
- [ ] Yaygın OCR hata düzeltme
- [ ] Çoklu format desteği

## [ ] 2.4 Birleşik Pipeline (`src/pipeline.py`)

```python
@dataclass
class PlateInfo:
    bbox: tuple
    plate_text: str
    confidence_det: float
    confidence_ocr: float
    format_valid: bool
    crop_b64: str          # Base64 encoded crop (API yanıtı için)

@dataclass
class PipelineResult:
    annotated_image_b64: str
    plates: list[PlateInfo]
    processing_ms: float
    plate_texts: list[str]  # Sadece temizlenmiş metinler (hızlı erişim)

class PlateDetectionPipeline:
    def process_image(self, image: np.ndarray) -> PipelineResult
    def process_frame(self, frame: np.ndarray) -> PipelineResult
```

- [ ] Pipeline singleton (uygulama genelinde tek örnek)
- [ ] `startup_event`'te warmup
- [ ] İşlem süresi loglama

## [ ] 2.5 Plaka Kontrol Servisi (`app/services/plate_checker.py`)

**Bu, otopark iş mantığının kalbidir:**

```python
class PlateChecker:
    def check_entry(self, plate_text: str) -> CheckResult
    def check_exit(self, plate_text: str) -> CheckResult

@dataclass
class CheckResult:
    plate_text: str
    vehicle_found: bool
    subscription_active: bool
    subscription_info: dict | None    # Plan adı, bitiş tarihi
    customer_name: str | None
    action: str                       # "ALLOW_ENTRY" | "ALLOW_EXIT" | "DENY" | "EXPIRED"
    message: str                      # Kullanıcıya gösterilecek mesaj
```

- [ ] Plaka metni normalize ederek ara (büyük harf, boşluksuz)
- [ ] Aktif session var mı kontrol (zaten içeride mi?)
- [ ] Abonelik geçerlilik tarihi kontrolü
- [ ] Son 3 günde biten abonelikler için uyarı
- [ ] Bilinmeyen plaka → kasiyer bildirimi

---

# ============================================================
# PHASE 3 — VERİTABANI KATMANI
# ============================================================

## [ ] 3.1 SQLAlchemy Kurulumu

- [ ] `app/database.py`: Engine, SessionLocal, Base
- [ ] SQLite WAL mode aktif (eşzamanlı okuma)
- [ ] Alembic kurulumu: `alembic init alembic`

## [ ] 3.2 ORM Modelleri

### `app/models/user.py` — Staff (Admin/Kasiyer):
```sql
users:
  id, email, username, hashed_password,
  full_name, role (admin/kasiyer),
  is_active, created_at, last_login
```

### `app/models/customer.py` — Müşteri:
```sql
customers:
  id, first_name, last_name,
  phone, email, tc_no (opsiyonel),
  address, notes,
  is_active, created_at,
  portal_password_hash  ← müşteri portal girişi için
```

### `app/models/vehicle.py` — Araç:
```sql
vehicles:
  id, customer_id (FK → customers),
  plate_number (UNIQUE, normalized — boşluksuz büyük harf),
  plate_display  ← orijinal format "34 ABC 1234"
  vehicle_type (otomobil/suv/minibüs/kamyonet),
  brand, model, color,
  is_active, created_at
```

### `app/models/subscription_plan.py` — Abonelik Planları:
```sql
subscription_plans:
  id, name,
  plan_type (hourly/daily/weekly/monthly/quarterly/biannual/annual),
  duration_hours,   ← saatlik: 1, günlük: 24, aylık: 720 vb.
  price,            ← TL cinsinden
  description,
  is_active, display_order
  
Örnek planlar:
  Saatlik        | 1h     | ₺10
  Günlük         | 24h    | ₺50
  Haftalık       | 168h   | ₺200
  Aylık          | 720h   | ₺500
  3 Aylık        | 2160h  | ₺1300
  6 Aylık        | 4320h  | ₺2400
  Yıllık         | 8760h  | ₺4200
```

### `app/models/subscription.py` — Araç Aboneliği:
```sql
subscriptions:
  id, vehicle_id (FK),
  plan_id (FK),
  start_date, end_date,
  status (active/expired/cancelled/pending),
  total_paid,
  payment_simulated (bool),
  payment_date,
  notes,
  created_by_user_id (FK → users),
  created_at
```

### `app/models/parking_session.py` — Giriş/Çıkış:
```sql
parking_sessions:
  id, vehicle_id (FK),
  subscription_id (FK, nullable — aboneliksiz girebilirse)
  entry_time, exit_time (nullable — içerdeyse null),
  duration_minutes (çıkışta hesaplanır),
  is_active (True = içeride),
  entry_plate_confidence,  ← kamera güven skoru
  exit_plate_confidence,
  entry_snapshot_path,     ← giriş anı görüntüsü
  exit_snapshot_path,
  notes, created_at
```

### `app/models/parking_config.py` — Otopark Ayarları:
```sql
parking_config:
  id, total_capacity,
  current_occupancy,    ← aktif session sayısı (hesaplanır)
  name, address, phone,
  open_time, close_time,
  updated_at
```

## [ ] 3.3 Migration ve Seed Data

- [ ] `alembic revision --autogenerate -m "initial_schema"`
- [ ] `alembic upgrade head`
- [ ] `scripts/seed_db.py` — başlangıç verisi:
  - Admin kullanıcısı
  - Kasiyer kullanıcısı
  - 7 abonelik planı
  - Otopark konfigürasyonu (kapasite: 100)
  - 3-5 örnek müşteri + araç + abonelik (demo için)

---

# ============================================================
# PHASE 4 — FASTAPI BACKEND
# ============================================================

## [ ] 4.1 Ana Uygulama (`app/main.py`)

- [ ] FastAPI app + metadata (title, version)
- [ ] Jinja2Templates + StaticFiles mount
- [ ] Startup event: Pipeline yükle + warm-up
- [ ] Routers include (tümü)
- [ ] Exception handlers (404/500 → özel sayfa)
- [ ] CORS (localhost için)

## [ ] 4.2 Auth Router (`app/routers/auth.py`)

### Staff (Admin/Kasiyer) Girişi:
```
GET  /login              → login sayfası
POST /login              → giriş → rol bazlı yönlendir
GET  /logout             → oturumu kapat
```

### Müşteri Portal:
```
GET  /musteri/register   → müşteri kayıt sayfası
POST /musteri/register   → kayıt işlemi (ad, plaka, telefon, şifre)
GET  /musteri/login      → müşteri giriş
POST /musteri/login      → giriş → müşteri dashboard
```

### Auth Servisi:
- [ ] Bcrypt şifre hash
- [ ] JWT (staff için 8 saat, müşteri için 24 saat)
- [ ] HttpOnly cookie (güvenli)
- [ ] 3 ayrı dependency:
  - `get_current_staff_user` → admin veya kasiyer
  - `get_current_admin` → sadece admin
  - `get_current_customer` → sadece müşteri

## [ ] 4.3 Kamera Router (`app/routers/camera.py`)

```
GET  /camera             → canlı kamera sayfası
WS   /ws/stream          → WebSocket kamera akışı
POST /api/camera/detect  → tek görüntü tespit (REST)
POST /api/camera/entry   → giriş işlemi (plaka okuyup session aç)
POST /api/camera/exit    → çıkış işlemi (session kapat)
```

### WebSocket Akış Protokolü:
```json
// Client → Server (her 150ms bir frame)
{ "frame": "base64_jpeg...", "action": "stream" }

// Server → Client
{
  "annotated_frame": "base64_jpeg...",
  "detections": [
    {
      "plate_text": "34ABC1234",
      "confidence": 0.97,
      "subscription_status": "ACTIVE",
      "customer_name": "Ahmet Yılmaz",
      "expires": "2026-05-01"
    }
  ],
  "fps": 8.3,
  "processing_ms": 120
}
```

### Giriş/Çıkış İş Akışı:
- [ ] Plaka tespit et → metni al
- [ ] `PlateChecker.check_entry()` çağır
- [ ] Sonuca göre session aç/kapat
- [ ] Snapshot'ı kaydet (`outputs/snapshots/YYYY-MM-DD/`)
- [ ] DB'ye session kaydı yaz
- [ ] Kapasite sayacını güncelle

## [ ] 4.4 Müşteri Router (`app/routers/customers.py`)

```
GET  /customers          → liste sayfası (admin/kasiyer)
GET  /customers/new      → yeni müşteri formu
POST /customers          → müşteri oluştur
GET  /customers/{id}     → müşteri detayı + araçları
PUT  /customers/{id}     → müşteri güncelle
```

- [ ] Müşteri arama (isim, telefon, plaka)
- [ ] Müşterinin tüm araçlarını ve aboneliklerini göster
- [ ] Müşteri silinemiyor (sadece pasif yapılabilir — geçmiş kayıtlar korunmalı)

## [ ] 4.5 Araç Router (`app/routers/vehicles.py`)

```
GET  /vehicles           → araç listesi
GET  /vehicles/new       → yeni araç formu
POST /vehicles           → araç ekle (hangi müşteriye ait)
GET  /vehicles/{id}      → araç detayı + abonelik + session geçmişi
PUT  /vehicles/{id}      → araç güncelle
POST /vehicles/{id}/deactivate → pasif yap
```

- [ ] Plaka normalizasyonu (kayıt sırasında otomatik)
- [ ] Duplicate plaka kontrolü
- [ ] Araç tipi seçimi (dropdown)

## [ ] 4.6 Abonelik Router (`app/routers/subscriptions.py`)

```
GET  /subscriptions/plans     → plan listesi (herkese açık)
GET  /subscriptions/new       → yeni abonelik formu
POST /subscriptions           → abonelik oluştur (ödeme simülasyonu ile)
GET  /subscriptions/{id}      → abonelik detayı
PUT  /subscriptions/{id}/cancel → iptal et
POST /subscriptions/{id}/renew  → uzat
GET  /api/subscriptions/expiring → bu hafta biten abonelikler (admin)
```

### Abonelik Oluşturma Akışı:
1. Araç seç (veya yeni araç ekle)
2. Plan seç
3. Ödeme sayfasına yönlendir
4. Simüle et → DB'ye yaz → abonelik aktif

### Otomatik Özellikler:
- [ ] Son 3 günde biten abonelikler için dashboard uyarısı
- [ ] Abonelik uzatmada tarihi bugünden değil mevcut bitiş tarihinden devam ettir

## [ ] 4.7 Session Router (`app/routers/sessions.py`)

```
GET  /sessions           → giriş/çıkış geçmişi (filtreli)
GET  /api/sessions/active → şu an içerideki araçlar
GET  /api/sessions/stats  → istatistik JSON (grafik için)
GET  /api/sessions/export → CSV export
```

- [ ] Tarih filtresi
- [ ] Araç/plaka arama
- [ ] Sayfalama (30 kayıt/sayfa)
- [ ] CSV: tarih, plaka, müşteri, giriş/çıkış, süre

## [ ] 4.8 Ödeme Router (`app/routers/payment.py`)

```
GET  /payment/{subscription_id}  → kart animasyonu sayfası
POST /api/payment/simulate       → ödeme simülasyonu
GET  /payment/success            → başarılı ödeme sayfası
```

### Simülasyon Akışı:
1. Kart bilgileri girilir
2. POST isteği → 2 saniyelik bekleme (loading)
3. `subscription.payment_simulated = True`
4. `subscription.status = "active"`
5. Success sayfasına yönlendir

## [ ] 4.9 Admin Router (`app/routers/admin.py`)

```
GET  /admin              → admin dashboard
GET  /admin/users        → staff kullanıcı listesi
POST /admin/users        → yeni kasiyer ekle
PUT  /admin/users/{id}/toggle → aktif/pasif
GET  /admin/reports      → raporlar sayfası
GET  /api/admin/stats    → gelir, doluluk, müşteri istatistikleri
```

---

# ============================================================
# PHASE 5 — PREMIUM WEB ARAYÜZÜ
# ============================================================

## TASARIM SİSTEMİ

**Renk Paleti (Dark Mode — Varsayılan):**
```css
--primary:       #6366f1   /* Indigo */
--primary-dark:  #4f46e5
--secondary:     #0ea5e9   /* Sky */
--accent:        #f59e0b   /* Amber — uyarı/vurgu */
--success:       #10b981   /* Emerald — aktif/başarı */
--danger:        #ef4444   /* Red — hata/iptal */
--warning:       #f97316   /* Orange — dikkat */
--bg-main:       #0f172a   /* Slate 900 */
--bg-card:       #1e293b   /* Slate 800 */
--bg-input:      #0f172a
--text-primary:  #f8fafc
--text-muted:    #94a3b8
--border:        #334155   /* Slate 700 */
```

**Tipografi:** Inter (Google Fonts CDN)  
**İkonlar:** Heroicons (CDN veya SVG inline)  
**Grafik:** Chart.js (CDN)  
**Animasyonlar:** CSS transitions + Alpine.js

**Ortak UI Prensipler:**
- Glassmorphism kartlar: `backdrop-blur + bg-opacity`
- Gradient butonlar (primary → primary-dark)
- Status badge'leri: renk kodlu (yeşil=aktif, kırmızı=süresi dolmuş, sarı=yakında bitiyor)
- Loading skeleton animasyonları
- Toast bildirim sistemi (sağ alt köşe)

---

## [ ] 5.1 Base Layout (`templates/base.html`)

```html
<!-- İçerik: -->
- <head>: Tailwind CDN, Inter font, Alpine.js, Chart.js
- Navbar:
    Admin/Kasiyer: Logo | Dashboard | Kamera | Müşteriler | Araçlar | Abonelikler | Geçmiş | [Kullanıcı ▼]
    Müşteri:       Logo | Dashboard | Aracım | Aboneliğim | Geçmişim | [Ad ▼]
- Flash message: success/error/warning toast (Alpine.js ile auto-dismiss 4sn)
- <slot /> içerik bölgesi
- Footer: "OtoparkPro v2.0 | AI Destekli Plaka Tanıma"
```

---

## [ ] 5.2 Landing Page (`templates/index.html`)

**Bölümler:**

### Hero:
```
┌───────────────────────────────────────────────────────────┐
│  [LOGO] OtoparkPro                    [Giriş] [Kayıt]    │
├───────────────────────────────────────────────────────────┤
│                                                           │
│    Yapay Zeka Destekli                                   │
│    Otopark Yönetim Sistemi                               │
│                                                           │
│    YOLOv11s · 99.5%+ Doğruluk · Gerçek Zamanlı          │
│    Global Plaka Desteği                                  │
│                                                           │
│    [Sisteme Giriş →]     [Demo İzle ▶]                  │
│                                                           │
│    [Animasyon: Kamera → bbox çiziliyor → "34 ABC 1234"] │
└───────────────────────────────────────────────────────────┘
```

### İstatistik Sayaçları (animate-on-scroll):
```
[99.5% Doğruluk] [25,000+ Eğitim] [<100ms Hız] [Global Destek]
```

### Özellikler Grid (3 sütun):
```
[🔍 AI Plaka Tespiti]  [📋 Abonelik Yönetimi]  [📊 Raporlama]
[🎥 Canlı Kamera]      [👥 Müşteri Portalı]    [📱 Kolay Arayüz]
```

### Nasıl Çalışır (3 adım animasyon):
```
① Araç Gelir  →  ② Kamera Okur  →  ③ Otomatik Giriş
```

### Abonelik Planları Önizleme:
- Saatlik / Günlük / Aylık / Yıllık kart örnekleri

---

## [ ] 5.3 Admin Dashboard (`templates/dashboard/admin.html`)

```
┌─────────────────────────────────────────────────────────────┐
│  Admin Paneli — OtoparkPro        [Şu an: 14:35 Salı]      │
├─────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│ │ 67/100     │ │ 42         │ │ 38         │ │ ₺12,400  │ │
│ │ Doluluk    │ │ Aktif Abone│ │ Müşteri    │ │ Bu Ay    │ │
│ │ ████░░ 67% │ │ ▲ +3 bugün │ │ Toplam     │ │ Gelir    │ │
│ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────┤
│ [Son 7 Gün Giriş/Çıkış Grafiği — Bar Chart.js]            │
├─────────────────────────────┬───────────────────────────────┤
│ Son Giriş/Çıkışlar          │ Yakında Biten Abonelikler     │
│ ┌─────────────────────────┐ │ ┌─────────────────────────┐  │
│ │ ⬆ 34ABC1234 14:32 GİR. │ │ │ ⚠ 06KL9988 — 2 gün     │  │
│ │ ⬇ 06KL5678 14:28 ÇIK. │ │ │ ⚠ 34ZZ4421 — 1 gün     │  │
│ │ ⬆ 35BD0012 14:15 GİR. │ │ │ ⚠ 41AB1234 — 3 gün     │  │
│ └─────────────────────────┘ │ └─────────────────────────┘  │
│ [Tüm Geçmiş →]             │ [Hepsini Gör →]              │
└─────────────────────────────┴───────────────────────────────┘
```

- [ ] Doluluk bar'ı (yeşil < 70%, sarı 70-90%, kırmızı > 90%)
- [ ] Sayaçlar Alpine.js ile otomatik güncellenir (30sn polling)
- [ ] Grafik: Son 7 günün saatlik bazda giriş/çıkış yoğunluğu

---

## [ ] 5.4 Kasiyer Dashboard (`templates/dashboard/kasiyer.html`)

```
┌─────────────────────────────────────────────────────────────┐
│  Kasiyer Paneli                  Doluluk: [██████░░░] 67%  │
├────────────────────────┬────────────────────────────────────┤
│  CANLI KAMERA          │  PLAKA SONUCU                      │
│  ┌──────────────────┐  │  ┌─────────────────────────────┐  │
│  │                  │  │  │                             │  │
│  │  [Kamera Feed]   │  │  │  34 ABC 1234                │  │
│  │                  │  │  │  ━━━━━━━━━━━━━━━━━━━━━━    │  │
│  │  [BBOX çizgisi]  │  │  │  ✅ AKTİF ABONELİK         │  │
│  │                  │  │  │  Ahmet Yılmaz               │  │
│  └──────────────────┘  │  │  Aylık Plan                 │  │
│  [📷 Başlat/Durdur]   │  │  Bitiş: 2026-05-01          │  │
│                        │  │                             │  │
│                        │  │  [✅ GİRİŞ ONAYLA]         │  │
│                        │  │  [❌ REDDET]               │  │
│                        │  └─────────────────────────────┘  │
├────────────────────────┴────────────────────────────────────┤
│  Bugünkü Hareketler   Giriş: 24 | Çıkış: 18 | İçeride: 67 │
│  [Son 10 hareket listesi...]                                │
└─────────────────────────────────────────────────────────────┘
```

- [ ] Kamera WebSocket bağlantısı (Alpine.js yönetiminde)
- [ ] Plaka tespitinde sonuç paneli otomatik güncellenir
- [ ] Onay/red butonu → `/api/camera/entry` veya `/api/camera/exit`
- [ ] Aboneliği olmayan araç → turuncu uyarı + "Abonelik Sat" butonu

---

## [ ] 5.5 Müşteri Dashboard (`templates/dashboard/musteri.html`)

```
┌─────────────────────────────────────────────────────────────┐
│  Merhaba, Ahmet Bey!                                        │
├──────────────────────────────┬──────────────────────────────┤
│  Aracım                      │  Aboneliğim                  │
│  ┌──────────────────────┐    │  ┌────────────────────────┐ │
│  │ 34 ABC 1234          │    │  │ ⭐ Aylık Plan           │ │
│  │ Toyota Corolla       │    │  │ ₺500/ay                │ │
│  │ Beyaz, 2022          │    │  │ Başlangıç: 01.04.2026  │ │
│  └──────────────────────┘    │  │ Bitiş: 01.05.2026      │ │
│  [Araç Bilgilerimi Güncelle] │  │ ████████░░ 8 gün kaldı │ │
│                              │  │ [Aboneliği Uzat]       │ │
│                              │  └────────────────────────┘ │
├──────────────────────────────┴──────────────────────────────┤
│  Son Giriş/Çıkışlarım                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 03.04.2026 14:32 Giriş — 03.04.2026 18:45 Çıkış    │  │
│  │ 02.04.2026 09:15 Giriş — 02.04.2026 13:20 Çıkış    │  │
│  └──────────────────────────────────────────────────────┘  │
│  [Tüm Geçmişim →]                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## [ ] 5.6 Müşteri Listesi (`templates/customers/list.html`)

```
┌─────────────────────────────────────────────────────────────┐
│  Müşteriler            [🔍 Ad/Plaka Ara] [+ Yeni Müşteri]  │
├────────┬──────────────┬────────────┬────────────┬──────────┤
│ #      │ Müşteri      │ Araç(lar)  │ Abonelik   │ İşlem    │
├────────┼──────────────┼────────────┼────────────┼──────────┤
│ 1      │ Ahmet Yılmaz │ 34 ABC 123 │ ✅ Aktif   │ [Detay] │
│        │ 0532-xxx-xx  │            │ 28 gün     │ [Düzenle]│
├────────┼──────────────┼────────────┼────────────┼──────────┤
│ 2      │ Fatma Demir  │ 06 KL 5678 │ ⚠️ 2 gün  │ [Detay] │
│        │ 0535-xxx-xx  │            │            │ [Düzenle]│
└────────┴──────────────┴────────────┴────────────┴──────────┘
│  ← Önceki   [1] [2] [3]   Sonraki →                       │
└─────────────────────────────────────────────────────────────┘
```

- [ ] Canlı arama (Alpine.js + debounce 300ms)
- [ ] Abonelik durumu badge renkleri
- [ ] Sayfalama

---

## [ ] 5.7 Abonelik Planları (`templates/subscriptions/plans.html`)

```
┌─────────────────────────────────────────────────────────────┐
│              Abonelik Planları                              │
│                                                             │
│  [Saatlik] [Günlük] [Haftalık] [Aylık] [3 Aylık] [Yıllık] │
│       ←── Tab/Buton Seçici ───►                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  ⭐ AYLIK PLAN                         │ │
│  │                                                       │ │
│  │                    ₺500/ay                            │ │
│  │                                                       │ │
│  │   ✓ 30 gün kesintisiz park                           │ │
│  │   ✓ 7/24 erişim                                      │ │
│  │   ✓ Müşteri portalı                                  │ │
│  │   ✓ Giriş/çıkış bildirimi                           │ │
│  │                                                       │ │
│  │         [Bu Planı Seç →]                             │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Tüm Planlar Karşılaştırması:                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Plan     │ Süre  │ Fiyat  │ Günlük Maliyet         │  │
│  │ Saatlik  │ 1s    │ ₺10    │ max ₺240/gün           │  │
│  │ Günlük   │ 24s   │ ₺50    │ ₺50/gün                │  │
│  │ Haftalık │ 7 gün │ ₺200   │ ₺28.5/gün  %43 ucuz   │  │
│  │ Aylık    │ 30 g  │ ₺500   │ ₺16.7/gün  %67 ucuz   │  │
│  │ 3 Aylık  │ 90 g  │ ₺1300  │ ₺14.4/gün  %71 ucuz   │  │
│  │ 6 Aylık  │ 180g  │ ₺2400  │ ₺13.3/gün  %73 ucuz   │  │
│  │ Yıllık   │ 365g  │ ₺4200  │ ₺11.5/gün  %77 ucuz   │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## [ ] 5.8 Ödeme Simülasyonu (`templates/payment/checkout.html`)

```
┌─────────────────────────────────────────────────────────────┐
│  Güvenli Ödeme                                  🔒 SSL      │
│                                                             │
│  Sipariş Özeti:                                            │
│  34 ABC 1234 — Aylık Plan — ₺500                          │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  [3D Kart Animasyonu — CSS Transform3d]             │  │
│  │  ┌────────────────────────────────────┐            │  │
│  │  │ ≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋≋ │            │  │
│  │  │ ██████████████████                 │            │  │
│  │  │ 4242  ████  ████  1234             │            │  │
│  │  │ KART SAHİBİ               12/28   │            │  │
│  │  │                    [VISA LOGO]    │            │  │
│  │  └────────────────────────────────────┘            │  │
│  │                                                     │  │
│  │  Kart No:    [____ ____ ____ ____]                 │  │
│  │  Son K.Tar.: [MM/YY]    CVV: [___] ← kart döner   │  │
│  │  Kart Adı:   [______________________]              │  │
│  │                                                     │  │
│  │  [ ──────── Ödemeyi Tamamla ₺500 ──────── ]       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ⚠ Bu ödeme bir simülasyondur. Gerçek ödeme alınmaz.      │
│  [Visa] [Mastercard] [Amex] [Troy]                         │
└─────────────────────────────────────────────────────────────┘
```

**Kart Animasyonu Detayları:**
- [ ] Input'a yazarken kart üzerinde anlık güncelleme
- [ ] CVV alanına odaklanınca kart 180° döner (arka yüz gösterilir)
- [ ] Kart numarasına göre otomatik logo (4=Visa, 5=MC, 3=Amex, 9=Troy)
- [ ] Luhn algoritması ile kart validasyonu (renk değişimi)
- [ ] "Ödemeyi Tamamla" → 2sn loading spinner → success/fail

**Başarılı Ödeme (`templates/payment/success.html`):**
- [ ] Confetti animasyonu (CSS)
- [ ] Yeşil checkmark animasyonu (SVG stroke-dashoffset)
- [ ] Abonelik detayları özet kartı
- [ ] "Dashboard'a Dön" ve "Makbuzu Yazdır" butonları

---

## [ ] 5.9 Giriş/Çıkış Geçmişi (`templates/sessions/history.html`)

```
┌─────────────────────────────────────────────────────────────┐
│  Giriş/Çıkış Geçmişi          [🔍 Ara] [📅] [📥 CSV]      │
│                                                             │
│  Filtreler: [Bugün] [Bu Hafta] [Bu Ay] [Tüm Zamanlar]     │
│             [Tarih Aralığı: _____ — _____]                  │
├──────────┬──────────────┬────────────┬────────────┬────────┤
│ Tarih    │ Plaka        │ Müşteri    │ Süre       │ Durum  │
├──────────┼──────────────┼────────────┼────────────┼────────┤
│ 14:32    │ 34 ABC 1234  │ A. Yılmaz  │ İçeride    │ 🟢 Var│
│ 14:28    │ 06 KL 5678   │ F. Demir   │ 4s 12dk    │ ⬇ Çık │
│ 14:15    │ 35 BD 0012   │ M. Çelik   │ İçeride    │ 🟢 Var│
└──────────┴──────────────┴────────────┴────────────┴────────┘
│  ← Önceki   Sayfa 1/12   Sonraki →       Toplam: 234 kayıt│
└─────────────────────────────────────────────────────────────┘
```

- [ ] Canlı "içeride" araçlar yeşil badge
- [ ] Çıkış yapmış araçlar süre gösterir
- [ ] CSV export (pandas ile)

---

## [ ] 5.10 Admin Panel (`templates/admin/dashboard.html`)

- [ ] Staff kullanıcı yönetimi (kasiyer ekle/çıkar)
- [ ] Abonelik plan yönetimi (fiyat güncelleme)
- [ ] Otopark kapasitesi ayarı
- [ ] Sistem logları görünümü
- [ ] Gelir raporu (grafikle)

---

# ============================================================
# PHASE 6 — PERFORMANS OPTİMİZASYONU
# ============================================================

## [ ] 6.1 Model Optimizasyonu

- [ ] ONNX export (CPU için ~30% hız artışı)
  ```python
  model.export(format="onnx", simplify=True, imgsz=1280)
  ```
- [ ] Model warmup (startup'ta 3 dummy inference)
- [ ] Singleton pattern (global model instance)
- [ ] Confidence threshold: 0.35 (otopark için — yanlış tespit istemeyiz)
- [ ] NMS IoU threshold: 0.45

## [ ] 6.2 OCR Optimizasyonu

- [x] EasyOCR singleton
- [x] OCR throttling — WebSocket'te 1.5s aralıkla OCR, arası YOLO-only frame
- [x] Crop top-70% — plaka altındaki bayi/şehir yazısını OCR'dan çıkarır
- [x] Erken çıkış: RGB confidence ≥ 0.72 ise CLAHE varyantını atla
- [ ] **Temporal voting** — son 5 frame'de ≥2 kez okunan plakayı kabul et (one-off sahte okumaları filtreler)
  - WebSocket döngüsünde `plate_history: deque(maxlen=5)` tut
  - Plaka metni ≥2 kez geçmişte varsa `confirmed=True` olarak işaretle
  - UI'da sadece `confirmed=True` plakaları giriş/çıkış butonu için etkinleştir
- [ ] Crop refinement — dikey %65 + yatay %10 kenar boşluğu kırp (araştırma: en etkili ikinci iyileştirme)
- [ ] **fast-plate-ocr** (alternatif OCR motoru): `pip install fast-plate-ocr`
  - EasyOCR'dan ~3x daha hızlı, plakaya özel eğitilmiş
  - Test: mevcut EasyOCR sonuçlarıyla kıyasla, daha iyiyse değiştir
- [ ] Görüntü preprocessing pipeline optimize:
  - Kırp → 2x upscale → CLAHE → threshold

## [ ] 6.3 Web Performansı

- [ ] Static dosyalar: CDN linki (Tailwind, Alpine, Chart.js)
- [ ] Upload görüntüleri max 1920px resize (kayıt öncesi)
- [ ] Sonuç görüntüsü JPEG quality=85
- [ ] SQLite WAL mode
- [ ] DB index: `vehicles.plate_number`, `subscriptions.status`, `parking_sessions.is_active`

## [ ] 6.4 WebSocket Akış Optimizasyonu

- [x] Frame resize (1280→640 WebSocket akışı için) — `src/pipeline.py`'de max 640
- [x] OCR throttling 1.5s — arası frame'lerde son OCR sonucu kullanılır
- [ ] JPEG quality 70 (akış için bant genişliği tasarrufu)
- [ ] Ardışık aynı plaka tespitlerini filtrele (debounce)

## [ ] 6.5 OBS Virtual Camera / Test Kamerası Desteği

> Araştırma tarihi: 2026-04-06

- [ ] OBS Studio → Virtual Camera → tarayıcı `getUserMedia` ile al
  - Tarayıcı virtual cam'ı fiziksel kamera gibi görür — ek entegrasyon GEREKMEZ
  - Camera selection UI ekle: `<select>` ile hangi kameranın kullanılacağını seç
  - `navigator.mediaDevices.enumerateDevices()` ile kamera listesi al
- [ ] OBS bitrate ayarı: En az 2500 kbps + keyframe 1s (plaka metni bozulmasın)
  - Düşük bitrate → JPEG artefaktı → OCR hataları
- [ ] Test senaryosu: OBS'de plaka görseli döngüye al → sisteme bağla → tanıma testi
- [ ] Debug log ekle: frame boyutu + timestamp tutarlılığı kontrol (OBS jitter tespiti)

## [ ] 6.6 Hedef Performans Metrikleri

| Metrik | Hedef |
|--------|-------|
| mAP50 | > 99.5% |
| mAP50-95 | > 92% |
| Görüntü inference (CPU, ONNX) | < 80ms |
| WebSocket akış FPS | 8-15 FPS |
| OCR süresi | < 100ms/plaka |
| Web sayfa yükleme | < 1.5s |
| DB sorgu (plaka kontrolü) | < 5ms |

---

# ============================================================
# PHASE 7 — TEST VE KALİTE KONTROL
# ============================================================

## [ ] 7.1 Model Testleri

- [ ] Test seti inference → mAP hesapla
- [ ] Farklı koşul testleri:
  - [ ] Gece/loş ışık
  - [ ] Yağmur/ıslak cam
  - [ ] Hızlı araç (bulanık)
  - [ ] Uzak mesafe
  - [ ] Açılı plaka (perspektif)
  - [ ] Türk + Avrupa + Asya plakaları
- [ ] False positive analizi (yanlış plaka tespiti)
- [ ] False negative analizi (plaka kaçırdı mı)

## [ ] 7.2 Entegrasyon Testleri (`tests/`)

- [ ] `test_detector.py` — Detection unit testleri
- [ ] `test_ocr.py` — OCR unit testleri
- [ ] `test_plate_checker.py` — İş mantığı testleri
- [ ] `test_api_auth.py` — Login/logout/register
- [ ] `test_api_camera.py` — Entry/exit akışı
- [ ] `test_api_subscription.py` — Abonelik CRUD

## [ ] 7.3 UI/UX Kontrol Listesi

- [ ] Tüm sayfalarda responsive (masaüstü + tablet)
- [ ] Boş durum (empty state) sayfaları (kayıt yokken)
- [ ] Tüm form validasyonları
- [ ] Hata mesajları anlaşılır
- [ ] Kamera izni reddedilirse graceful fallback
- [ ] Aboneliği olmayan araç girişi doğru uyarı verir
- [ ] Süresi dolmuş abonelik doğru uyarı verir

---

# ============================================================
# PHASE 8 — DOKÜMANTASYON VE SUNUM
# ============================================================

## [ ] 8.1 README.md

- Kurulum adımları
- `python run.py` ile çalıştırma
- Demo hesapları (admin/kasiyer/müşteri)
- Ekran görüntüleri

## [ ] 8.2 Teknik Sunum Materyalleri

- [ ] Sistem mimarisi diyagramı
- [ ] Veritabanı ER diyagramı
- [ ] Model eğitim sonuçları (karşılaştırma tablosu v1 vs v2)
- [ ] Demo video (canlı kamera tespiti)
- [ ] Performans kıyaslama tablosu

## [ ] 8.3 Başlatma

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# DB oluştur + seed
alembic upgrade head
python scripts/seed_db.py

# Uygulamayı başlat
python run.py
# veya
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Demo Hesaplar:**
- Admin: `admin@otopark.local` / `admin123`
- Kasiyer: `kasiyer@otopark.local` / `kasiyer123`
- Müşteri: Kendi kaydıyla portal girişi

---

# ============================================================
# FAZE BAĞIMLILIK HARİTASI
# ============================================================

```
PHASE 0 (Hazırlık)
    │
    ├──► PHASE 1 (Dataset + Model)         paralel başlar
    │         │
    └──► PHASE 3 (Veritabanı)             paralel başlar
              │
              └──► PHASE 2 (ML Modülleri src/)
                        │
                        └──► PHASE 4 (FastAPI Backend)
                                  │
                                  └──► PHASE 5 (Web UI)
                                            │
                                            └──► PHASE 6 (Performans)
                                                      │
                                                      └──► PHASE 7 (Test)
                                                                │
                                                                └──► PHASE 8 (Sunum)
```

**NOT:** Model eğitimi (Phase 1) uzun sürer. Eğitim arka planda çalışırken
Phase 3, 4, 5 geliştirilebilir. Model hazır olunca Phase 2 ve entegrasyon tamamlanır.

---

# ============================================================
# RİSK ANALİZİ
# ============================================================

| Risk | Çözüm |
|------|-------|
| GPU yok → eğitim uzun | Google Colab / Kaggle free GPU kullan |
| Dataset indirme erişim sorunu | Roboflow API veya manuel indirme |
| OCR plaka hatası | Post-process regex + karakter düzeltme |
| WebSocket kamera | localhost'ta HTTP OK, production HTTPS gerekir |
| SQLite eşzamanlılık | WAL mode + connection pooling |

---

# ============================================================
# BAŞARI KRİTERLERİ (BİTİRME PROJESİ DEĞERLENDİRMESİ)
# ============================================================

### Model:
- [ ] mAP50 > 99.5%
- [ ] mAP50-95 > 92%
- [ ] Global plaka desteği (TR + EU + Asya test edildi)
- [ ] < 100ms CPU inference

### Sistem:
- [ ] Otomatik giriş/çıkış kaydı çalışıyor
- [ ] 3 rol (admin/kasiyer/müşteri) doğru çalışıyor
- [ ] 7 farklı abonelik planı çalışıyor
- [ ] Kart animasyonu ödeme simülasyonu çalışıyor
- [ ] Canlı kamera WebSocket çalışıyor

### Kalite:
- [ ] Clean code, modüler yapı
- [ ] DB ilişkileri doğru
- [ ] Export (CSV) çalışıyor
- [ ] Responsive tasarım

---

**Son Güncelleme:** 2026-04-03  
**Hazırlayan:** Senior Software Architect  
**Proje:** PlateDetectionSystem — Otopark Yönetim Sistemi — Bitirme Projesi
