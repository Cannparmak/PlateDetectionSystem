# Arduino / ESP32 Kapı Kontrol Entegrasyonu

**Tarih:** 2026-05-18  
**Durum:** Tamamlandı — Üretimde çalışıyor

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
| ESP32 Dev Board | 1 | WiFi + Bluetooth mikrodenetleyici |
| I2C LCD Ekran (16x2, 0x27) | 1 | Durum mesajlarını gösterir |
| Yeşil LED | 1 | Giriş izni — GPIO4 (D4) |
| Kırmızı LED | 1 | Giriş reddedildi — GPIO2 (D2) |
| Direnç (220Ω) | 2 | Her LED için 1 adet |
| Jumper Kablo | — | Bağlantı kabloları |

---

## 3. Devre Şeması

```
ESP32                LCD (I2C, 0x27)
 GND ────────────── GND
 3.3V ───────────── VCC
 GPIO21 (SDA) ───── SDA
 GPIO22 (SCL) ───── SCL

ESP32                Yeşil LED
 GPIO4 ─── 220Ω ─── Anot (+)
 GND ──────────────  Katot (-)

ESP32                Kırmızı LED
 GPIO2 ─── 220Ω ─── Anot (+)
 GND ──────────────  Katot (-)
```

---

## 4. ESP32 Kodu (Arduino IDE)

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ── Yapılandırma ──────────────────────────────────────────
const char* WIFI_SSID     = "WiFi_Aginizin_Adi";
const char* WIFI_PASSWORD = "WiFi_Sifreniz";
const char* SERVER_URL    = "http://192.168.x.x:8000/api/arduino/state";
const char* API_KEY       = "esp32-otopark-2024";

const int PIN_GREEN = 4;   // D4 — Yeşil LED
const int PIN_RED   = 2;   // D2 — Kırmızı LED
const int POLL_MS   = 2000; // Sunucuyu her 2 saniyede sorgula

// ── Nesneler ──────────────────────────────────────────────
LiquidCrystal_I2C lcd(0x27, 16, 2);
HTTPClient http;

// ── Setup ─────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_RED, OUTPUT);
  digitalWrite(PIN_GREEN, LOW);
  digitalWrite(PIN_RED, HIGH);  // Başlangıçta kırmızı

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("OtoparkPro");
  lcd.setCursor(0, 1);
  lcd.print("Baglanıyor...");

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Baglandi!");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP());
  delay(2000);
}

// ── Loop ──────────────────────────────────────────────────
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    lcd.clear();
    lcd.print("WiFi yok!");
    delay(POLL_MS);
    return;
  }

  http.begin(SERVER_URL);
  http.addHeader("X-API-Key", API_KEY);

  int code = http.GET();

  if (code == 200) {
    String body = http.getString();
    body.trim();

    if (body == "1") {
      // Yeşil — Kapı aç
      digitalWrite(PIN_GREEN, HIGH);
      digitalWrite(PIN_RED, LOW);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("GECIS IZNI VAR");
      lcd.setCursor(0, 1);
      lcd.print("Hos Geldiniz!");
    } else {
      // Kırmızı — Bekleme / Reddedildi
      digitalWrite(PIN_GREEN, LOW);
      digitalWrite(PIN_RED, HIGH);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("BEKLENIYOR...");
      lcd.setCursor(0, 1);
      lcd.print("Plaka Okunu.");
    }
  } else {
    // Sunucuya ulaşılamadı
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("SUNUCU HATASI");
    lcd.setCursor(0, 1);
    lcd.print("Kod: " + String(code));
  }

  http.end();
  delay(POLL_MS);
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

Yanıt:
  "1"  — Yeşil sinyal var (GATE_OPEN_DURATION içinde)
  "0"  — Sinyal yok / süresi dolmuş
```

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
| `WiFi` | Arduino | Dahili — ESP32'de zaten var |
| `HTTPClient` | Arduino | Dahili — ESP32'de zaten var |

**Board Seçimi:** Tools → Board → ESP32 Dev Module  
**Port:** Aygıt Yöneticisi'nde görünen COM portu (USB takınca görünür)

---

## 10. LCD Durum Mesajları

| Durum | LCD Satır 1 | LCD Satır 2 |
|---|---|---|
| Bağlanıyor | `OtoparkPro` | `Baglanıyor...` |
| Bağlandı (2sn) | `Baglandi!` | IP adresi |
| Normal bekleme | `BEKLENIYOR...` | `Plaka Okunu.` |
| Yeşil sinyal | `GECIS IZNI VAR` | `Hos Geldiniz!` |
| Sunucu hatası | `SUNUCU HATASI` | `Kod: <HTTP kodu>` |
| WiFi koptu | `WiFi yok!` | — |

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

---

**Son Güncelleme:** 2026-05-18  
**İlgili Dosyalar:**  
- `app/routers/camera.py` — `/api/camera/entry-by-plate`, `/api/camera/exit-by-plate`  
- `app/routers/arduino.py` — `/api/arduino/state`, `/api/arduino/ping`  
- `app/services/gate_state.py` — sinyal bellek yönetimi  
- `app/templates/camera/entry.html` — frontend otomatik tetikleme  
- `app/templates/camera/exit.html` — frontend otomatik tetikleme  
- `.env` — `GATE_ENABLED`, `GATE_OPEN_DURATION`, `ARDUINO_API_KEY`
