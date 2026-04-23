# OtoparkPro — Akıllı Otopark Yönetim Sistemi

Kamera görüntüsünden araç plakasını otomatik tanıyan, abonelik ve ödeme yönetimi sunan tam kapsamlı otopark yönetim sistemi. Beykoz Üniversitesi Bitirme Projesi.

## Özellikler

- **Plaka Tespiti** — Özel eğitilmiş YOLOv11 modeli ile gerçek zamanlı plaka tespiti
- **OCR** — fast-plate-ocr ile TR/EN/DE/FR plaka okuma
- **Canlı Kamera** — WebSocket üzerinden anlık görüntü akışı
- **Giriş / Çıkış Yönetimi** — Plakaya göre otomatik tanıma ve bariyer kontrolü
- **Abonelik Sistemi** — Aylık/yıllık abonelik planları, müşteri portalı
- **Admin Paneli** — Raporlar, kullanıcı yönetimi, otopark kapasitesi
- **Kasiyör Ekranı** — Manuel işlem ve ödeme alma
- **Bariyer Kontrolü** — Serial port (COM) üzerinden fiziksel kapı entegrasyonu

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI + Uvicorn |
| Veritabanı | SQLite + SQLAlchemy |
| Şablon | Jinja2 |
| ML — Tespit | YOLOv11 (Ultralytics) |
| ML — OCR | fast-plate-ocr (ONNX) |
| Görüntü İşleme | OpenCV |
| Auth | JWT (python-jose) + bcrypt |
| Donanım | PySerial |

## Proje Yapısı

```
PlateDetectionSystem/
├── app/                    # FastAPI uygulaması
│   ├── models/             # SQLAlchemy veritabanı modelleri
│   ├── routers/            # API endpoint'leri
│   ├── services/           # İş mantığı (auth, gate, plate checker)
│   ├── templates/          # Jinja2 HTML şablonları
│   └── static/             # CSS, JS, görseller
├── src/                    # ML pipeline
│   ├── detection/          # YOLO dedektör
│   ├── ocr/                # OCR okuyucu
│   └── postprocess/        # Plaka metin temizleme
├── models/                 # Eğitilmiş model dosyaları (.pt, .onnx, OpenVINO)
├── scripts/                # Veri hazırlama ve eğitim scriptleri
├── docs/                   # Proje dokümantasyonu
├── requirements.txt
└── run.py                  # Başlatıcı
```

## Kurulum

### Gereksinimler

- Python 3.10+
- (Opsiyonel) CUDA destekli GPU — CPU ile de çalışır

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/Cannparmak/PlateDetectionSystem.git
cd PlateDetectionSystem

# 2. Sanal ortam oluştur ve aktif et
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ortam değişkenlerini ayarla
copy .env.example .env
# .env dosyasını düzenle (SECRET_KEY, admin bilgileri vb.)

# 5. Veritabanını başlat ve örnek veri ekle
python scripts/seed_db.py

# 6. Uygulamayı başlat
python run.py
```

Uygulama `http://localhost:8000` adresinde çalışır.

## Varsayılan Kullanıcılar

`.env` dosyasındaki değerlere göre:

| Rol | E-posta | Şifre |
|---|---|---|
| Admin | admin@otopark.local | admin123 |
| Kasiyör | kasiyer@otopark.local | kasiyer123 |

> Canlıya geçmeden önce `.env` içindeki `SECRET_KEY` ve şifreleri mutlaka değiştir.

## Model Bilgisi

`models/` klasöründe hazır eğitilmiş modeller yer alır — ek indirme gerekmez.

| Dosya | Açıklama |
|---|---|
| `plate_det_global_v1_best.pt` | YOLOv11 PyTorch ağırlığı |
| `plate_det_global_v1_best.onnx` | ONNX export (CPU optimize) |
| `plate_det_global_v1_best_openvino_model/` | OpenVINO export |

## Bariyer Entegrasyonu

Fiziksel bariyer bağlamak için `.env` dosyasında:

```
GATE_ENABLED=true
GATE_PORT=COM3   # Aygıt Yöneticisi'nden doğru COM portunu yaz
```

Bu proje bir bitirme çalışmasıdır.

## Lisans

MIT
