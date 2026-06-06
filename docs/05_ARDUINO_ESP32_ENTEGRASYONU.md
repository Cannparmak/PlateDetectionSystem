# Arduino / ESP32 Kapı Kontrol Entegrasyonu

**Tarih:** 2026-05-25  
**Durum:** Tamamlandı — Servo motor eklendi (v1.2)

---

## 1. Genel Bakış

Sistem, otopark giriş/çıkış kapısını WiFi üzerinden kontrol eden bir ESP32 devre kartı kullanır.  
ESP32, web sunucusunu belirli aralıklarla yoklayarak (polling) kapının açılıp açılmayacağına karar verir.

**Mimari:**

```
[Kamera Sayfası]                    [ESP32]
       │                               │
       │  Plaka onaylandı              │
       ▼                               │
[/api/camera/entry-by-plate]           │
       │                               │
       │  set_signal(1)                │
       ▼                               │
[gate_state.py — in-memory sinyal]     │
       ▲                               │
       │  GET /api/arduino/state       │
       └───────────────────────────────┘
              Her 2 saniyede bir
```

---

## 2. Donanım Listesi

| Parça | Adet | Açıklama |
|---|---|---|
| ESP32 Dev Board | 1 | Sistemin beyni — WiFi, HTTP polling, LED ve servo kontrolü |
| Arduino (Uno/Nano vb.) | 1 | **Sadece güç dağıtımı** — kod çalışmaz, bilgisayarın ayrı USB portuna takılır; LCD ve servo buradan beslenir |
| I2C LCD Ekran (16x2, 0x27) | 1 | Durum mesajlarını gösterir |
| Yeşil LED | 1 | Giriş izni — GPIO4 (D4) |
| Kırmızı LED | 1 | Giriş reddedildi — GPIO2 (D2) |
| Servo Motor (SG90 / MG90S) | 1 | Kapı mekanizması — GPIO18 (D18) |
| Direnç (220Ω) | 2 | Her LED için 1 adet |
| Jumper Kablo | — | Bağlantı kabloları |

---

## 3. Devre Şeması

```
ESP32                LCD (I2C, 0x27)
 GND ────────────── GND       ← Arduino üzerinden bilgisayar USB'den beslenir
 GPIO21 (SDA) ───── SDA
 GPIO22 (SCL) ───── SCL

ESP32                Yeşil LED
 GPIO4 ─── 220Ω ─── Anot (+)
 GND ──────────────  Katot (-)

ESP32                Kırmızı LED
 GPIO2 ─── 220Ω ─── Anot (+)
 GND ──────────────  Katot (-)

ESP32                Servo Motor (SG90/MG90S)
 GPIO18 ──────────── Sinyal (Turuncu/Sarı)
 GND ───────────────  GND   (Kahverengi/Siyah)

Arduino (sadece güç kaynağı — kod yok)
 VCC ────────────── Servo VCC (Kırmızı)   ← bilgisayarın ayrı USB portundan beslenir
 VCC ────────────── LCD   VCC
 GND ────────────── ESP32 GND  ← Ortak GND — zorunlu!
```

> **Neden Arduino?** ESP32'nin kendi USB bağlantısının yanı sıra Arduino bilgisayarın ayrı bir USB portuna takılır; LCD, servo ve diğer elemanlar güçlerini Arduino üzerinden bu bağlantıdan alır. Arduino'ya herhangi bir kod yüklenmez, salt güç dağıtımı için kullanılır.
>
> **Kritik:** Arduino GND ile ESP32 GND'nin jumper ile birleştirilmesi şarttır. Ortak GND olmadan servo sinyal pini referans noktası bulamaz ve hatalı/düzensiz hareket eder.

---

## 4. ESP32 Kodu (Arduino IDE) — v1.2

> Güncel kaynak dosya: `bitirme_projesi_arduino_kod-v1.2.ino`

**v1.2'de yapılan değişiklikler:**
- `ESP32Servo.h` kütüphanesi eklendi
- `PIN_SERVO = 18` (D18) tanımlandı
- `Servo kapiServo` nesnesi ve `bool kapiAcik` durum flag'i eklendi
- `setGreen()` → servo 0°'dan 90°'ye döner (kapı açılır)
- `setRed()` → servo 90°'dan 0°'ye döner (kapı kapanır)
- `kapiAcik` flag'i sayesinde servo sadece durum değiştiğinde hareket eder; her 2 saniyede titremez
- Setup içinde sunucu ping mekanizması eklendi (15 deneme, yanıt gelmezse devam eder)
- WiFi bağlantı kopukluğunda otomatik yeniden bağlanma iyileştirildi

**Temel yapı özeti:**

```cpp
#include <ESP32Servo.h>

const int PIN_SERVO  = 18;
const int SERVO_KAPALI = 0;   // Kapalı pozisyon
const int SERVO_ACIK   = 90;  // Açık pozisyon

Servo kapiServo;
bool  kapiAcik = false;

void setGreen() {
  // LED yeşil yap
  if (!kapiAcik) {
    kapiServo.write(SERVO_ACIK);   // 90° — kapı açılır
    kapiAcik = true;
  }
}

void setRed() {
  // LED kırmızı yap
  if (kapiAcik) {
    kapiServo.write(SERVO_KAPALI); // 0° — kapı kapanır
    kapiAcik = false;
  }
}

void setup() {
  kapiServo.attach(PIN_SERVO);
  kapiServo.write(SERVO_KAPALI);  // Başlangıç: kapalı
  // ... WiFi, LCD, ping ...
}
```

---

## 5. Sunucu Tarafı Yapılandırma

### 5.1 `.env` Ayarları

```env
# Gate controller — ESP32 WiFi tabanlı, seri port kullanılmıyor
GATE_ENABLED=false        # false = Serial port kapalı, sinyal yine de set_signal() ile yazılır
GATE_PORT=COM3            # Kullanılmıyor (GATE_ENABLED=false)
GATE_OPEN_DURATION=10     # Sinyalin geçerlilik süresi (saniye) — ESP32 yakalamak için yeterli süre
ARDUINO_API_KEY=esp32-otopark-2024  # ESP32'nin X-API-Key header değeri
```

**Neden `GATE_ENABLED=false`?**  
`GATE_ENABLED=true` sadece seri port üzerinden fiziksel kapı kontrolü yapar. ESP32 WiFi üzerinden kendi bağlandığı için bu flag'e gerek yok. Sinyal `gate_state.py` üzerinden her iki senaryoda da yazılır.

### 5.2 API Endpoint: `/api/arduino/state`

```
GET /api/arduino/state
Header: X-API-Key: esp32-otopark-2024

Yanıt formatı (tek satır):  "<signal>|<info>"
  signal:
    "1"  — Yeşil sinyal var (GATE_OPEN_DURATION içinde)
    "0"  — Sinyal yok / süresi dolmuş
  info:
    LCD 2. satırında gösterilecek borç/abonelik bilgisi (ASCII), boş olabilir.

Örnekler:
  "1|Borc yok - Iyi gunler"
  "1|Abonelik bitisi: 12.08.2026 - 45 gun kaldi"
  "0|Borc: 600TL - Limit 550TL asildi"
  "0|"
```

> `info` metni `camera.py` içindeki `_arduino_info_line()` tarafından `CheckResult`'tan
> üretilir; limit değeri `parking_config.debt_block_threshold` ayarından okunur.
> ESP32 `|` karakterinden böler: sol taraf LED/servo kararı, sağ taraf LCD 2. satırda
> kayan (marquee) yazı olur. Eski yalnız `"1"`/`"0"` formatı da geriye dönük desteklenir.

### 5.3 Sinyal Akış Süreci

1. Kamera sayfasında plaka `confirmed=true` olarak onaylanır
2. Frontend `/api/camera/entry-by-plate` veya `/api/camera/exit-by-plate` çağırır
3. Endpoint `gate_state.py`'deki `set_signal(1)` fonksiyonunu çağırır
4. `set_signal(1)` sinyal değerini ve zamanı bellekte saklar
5. ESP32 her ~2 saniyede `/api/arduino/state`'i sorgular
6. `get_signal()` fonksiyonu: `now - _updated_at < GATE_OPEN_DURATION` ise `"1"` döner
7. `GATE_OPEN_DURATION` (10 saniye) geçince sinyal otomatik `"0"` olur

---

## 6. Yeni API Endpoint'leri

### `POST /api/camera/entry-by-plate`

Plaka metnini alır, YOLO yeniden işleme yapmadan doğrudan abonelik kontrolü yapıp giriş kaydı açar.

**Neden bu endpoint gerekti?**  
Eski yöntemde frontend son kamera karesini sunucuya gönderip YOLO'ya tekrar işletiyordu. Ancak WebSocket'te OCR kısıtlaması (1.5s aralık) nedeniyle bazı kareler OCR içermez; dolayısıyla onaylanan plaka yerine yanlış/eksik bir plaka kaydediliyordu. Bu endpoint, zaten doğrulanmış plaka metnini doğrudan kullanır.

**İstek:**
```json
POST /api/camera/entry-by-plate
Content-Type: application/json

{ "plate": "66AR428" }
```

**Yanıt:**
```json
{
  "success": true,
  "action": "ALLOW_GUEST",
  "message": "Misafir giriş izni verildi.",
  "plate_text": "66AR428",
  "gate_result": "OPENED",
  "customer_name": null,
  "subscription_info": null,
  "expiry_warning": null,
  "fuzzy_match": false,
  "fuzzy_original": null,
  "user_type": "guest",
  "total_debt": 0,
  "annotated_frame": null
}
```

### `POST /api/camera/exit-by-plate`

Çıkış işlemi için aynı mantık. Ek olarak `fee_amount` ve `bracket_name` döner.

**Yanıt (ek alanlar):**
```json
{
  "success": true,
  "fee_amount": 120.0,
  "bracket_name": "2–4 Saat",
  ...
}
```

---

## 7. Frontend Otomatik Tetikleme Sistemi

### 7.1 PlateVoter (Client-Side)

Son 5 karedeki OCR sonuçlarını oylar. Aynı plaka >= 2 kez görülürse `confirmed=true`.

```
Frame 1: "66AR428" (confidence 0.92)
Frame 2: "66AR428" (confidence 0.89)  ← 2. kez görüldü → confirmed=true
Frame 3: YOLO-only (throttle) → son sonuç tekrar kullanılır
Frame 4: "66AR428" (confidence 0.94)
Frame 5: "66AR428" (confidence 0.91)
```

### 7.2 Abone Araç — Anlık Tetikleme

```javascript
// Abone ve aktif aboneliği varsa giriş anında tetikle
if (best.confirmed && best.can_enter && best.subscription_status === 'ACTIVE') {
  this.autoTrigger(best.plate_text);
}
```

### 7.3 Misafir Araç — 5 Saniye Bekle (guestConfirmedAt)

```javascript
// İlk confirmed anını kaydet
if (best.confirmed && !this.cam.guestConfirmedAt) {
  this.cam.guestConfirmedAt = Date.now();
}

// 5 saniye geçtikten sonra tetikle
const guestMs = Date.now() - this.cam.guestConfirmedAt;
if (guestMs >= 5000) {
  this.autoTrigger(best.plate_text);
}
```

**Neden 5 saniye?** Aracın durması ve sürücünün pozisyon alması için zaman tanır. Misafir araçlarda bunu `plateFirstSeenAt` yerine `guestConfirmedAt`'a bağlamak kritik — OCR değişkenliği başlangıç zamanını sürekli sıfırlıyordu.

### 7.4 Çift Tetikleme Önleme

```javascript
// Başarılı tetiklemeden sonra aynı plaka için tekrar tetikleme
this.cam.lastTriggeredPlate = data.plate_text;

// Kontrol
if (best.plate_text === this.cam.lastTriggeredPlate) return;
```

---

## 8. `gate_state.py` Sinyal Yönetimi

```
app/services/gate_state.py

_signal     = 0          # Mevcut sinyal (0 veya 1)
_updated_at = 0.0        # Son set_signal() çağrısının zamanı

set_signal(value):
    _signal     = value
    _updated_at = time.time()

get_signal():
    elapsed = time.time() - _updated_at
    if elapsed >= GATE_OPEN_DURATION:
        return 0          # Sinyal süresi dolmuş
    return _signal
```

---

## 9. Kütüphane Kurulumu (Arduino IDE)

Arduino IDE'de **Library Manager**'dan şunları yükle:

| Kütüphane | Yazar | Amaç |
|---|---|---|
| `LiquidCrystal_I2C` | Frank de Brabander | I2C LCD kontrolü |
| `ESP32Servo` | Kevin Harrington | ESP32 için PWM servo kontrolü |
| `WiFi` | Arduino | Dahili — ESP32'de zaten var |
| `HTTPClient` | Arduino | Dahili — ESP32'de zaten var |

**Board Seçimi:** Tools → Board → ESP32 Dev Module  
**Port:** Aygıt Yöneticisi'nde görünen COM portu (USB takınca görünür)

---

## 10. LCD Durum Mesajları

| Durum | LCD Satır 1 | LCD Satır 2 | Servo |
|---|---|---|---|
| Başlangıç | `Sisteme` | `baglaniliyor...` | 0° (kapalı) |
| WiFi bağlandı (1.5sn) | `WiFi Baglandi` | IP adresi | 0° |
| Sunucu bekleniyor | `Sunucu` | `bekleniyor...` | 0° |
| Hazır / bekleme | `Sistem Hazir` | `Gecis: KAPALI` | 0° (kapalı) |
| Yeşil sinyal | `KAPI ACIK` | `Gecebilirsiniz` | 90° (açık) |
| Kırmızı sinyal | `KAPI KAPALI` | `Gecemezsiniz` | 0° (kapalı) |
| API Key hatası | `API Key Hatasi` | `Kod: 401` | 0° |
| Sunucu hatası | `Sunucu Hatasi!` | `Kod: <HTTP kodu>` | 0° |
| WiFi koptu | `WiFi Kesildi!` | `Yeniden bagl.` | 0° |

---

## 11. Sorun Giderme

| Belirti | Olası Neden | Çözüm |
|---|---|---|
| LCD hiç yazmıyor | Yanlış I2C adresi | `i2c_scanner.ino` sketch ile adresi bul (genellikle 0x27 veya 0x3F) |
| "Sunucu hatası" | IP adresi yanlış | `.env`'deki veya ESP32 kodundaki IP'yi kontrol et |
| Yeşil LED yanmıyor | `GATE_OPEN_DURATION` çok kısa | `.env`'de `GATE_OPEN_DURATION=10` yap |
| Yanlış plaka kaydı | Eski frame-tabanlı kod | Bu döküman kapsamındaki endpoint'lere geçildi |
| Misafir LED yanmıyor | `plateFirstSeenAt` sıfırlanıyor | `guestConfirmedAt` kullanıldığından bu sorun çözüldü |
| Çift kayıt | `lastTriggeredPlate` kontrolü | Başarılı tetiklemeden sonra plaka sıfırlanmıyor — normal davranış |
| Servo hareket etmiyor | Güç hattı bağlı değil | Servo VCC'yi Arduino üzerinden bilgisayar USB'sine bağla; ESP32 GND ile Arduino GND ortak olmalı |
| Servo titriyor / sallanıyor | Her poll'da `write()` çağrılıyor | `kapiAcik` flag'i bunu önler; kodu v1.2 ile güncelle |
| Servo yanlış açıya gidiyor | `SERVO_ACIK` / `SERVO_KAPALI` sabit yanlış | Fiziksel mekanizmaya göre 0 ve 90 değerlerini ayarla |
| `ESP32Servo.h` bulunamıyor | Kütüphane yüklü değil | Arduino IDE → Library Manager → "ESP32Servo" ara ve yükle |

---

**Son Güncelleme:** 2026-05-25  
**İlgili Dosyalar:**  
- `bitirme_projesi_arduino_kod-v1.2.ino` — güncel ESP32 kodu (servo dahil)  
- `app/routers/camera.py` — `/api/camera/entry-by-plate`, `/api/camera/exit-by-plate`  
- `app/routers/arduino.py` — `/api/arduino/state`, `/api/arduino/ping`  
- `app/services/gate_state.py` — sinyal bellek yönetimi  
- `app/templates/camera/entry.html` — frontend otomatik tetikleme  
- `app/templates/camera/exit.html` — frontend otomatik tetikleme  
- `.env` — `GATE_ENABLED`, `GATE_OPEN_DURATION`, `ARDUINO_API_KEY`
