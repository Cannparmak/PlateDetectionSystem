#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP32Servo.h>

// ─── AYARLAR ──────────────────────────────────────────────
const char* SSID       = "FiberHGW_ZTJE44_2.4GHz";
const char* PASSWORD   = "HXXpzK9aKq";
const char* SERVER_IP  = "192.168.1.33";   // Bilgisayarın IP'si (ipconfig ile bak)
const int   SERVER_PORT = 8000;
const char* API_KEY    = "esp32-otopark-2024";  // .env ARDUINO_API_KEY ile aynı

const int PIN_GREEN  = 4;    // D4 → Yeşil LED
const int PIN_RED    = 2;    // D2 → Kırmızı LED
const int PIN_SERVO  = 18;   // D18 → Servo motor

const unsigned long POLL_INTERVAL_MS   = 2000;  // 2 saniyede bir sunucuyu sorgula
const unsigned long SCROLL_INTERVAL_MS = 350;   // LCD 2. satır kayma hızı (ms/karakter)

const int LCD_W = 16;          // LCD genişliği (karakter)

const int SERVO_KAPALI = 0;    // Kapı kapalı pozisyonu (0°)
const int SERVO_ACIK   = 90;   // Kapı açık pozisyonu (90°)

const unsigned long ACIK_KALMA_MS = 5000;   // Kapı açıldıktan 5 sn sonra kapanır
// ─────────────────────────────────────────────────────────

LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo kapiServo;

bool kapiAcik = false;          // Mevcut kapı durumunu takip eder
unsigned long acilmaZamani = 0; // Kapının açıldığı an (millis)
bool sureDoldu = false;         // 5 sn dolup kapandı mı (sunucu 0 olana dek tekrar açma)

// ── LCD durum / kaydırma (scroll) takibi ──────────────────
String lcdLine1 = "";           // 1. satırda yazan metin (gereksiz yenilemeyi önler)
String scrollSrc = "";          // 2. satır kaynak metni (16'dan uzunsa kayar)
int   scrollPos = 0;            // Kayma penceresinin başlangıç indeksi
unsigned long lastPoll   = 0;   // Son sunucu sorgusu (millis)
unsigned long lastScroll = 0;   // Son kaydırma adımı (millis)

// ── LCD yardımcıları ──────────────────────────────────────
// 2. satırı mevcut scrollPos'a göre çizer (16 karakterlik pencere).
void renderLine2() {
  String out;
  if (scrollSrc.length() <= LCD_W) {
    out = scrollSrc;
    while ((int)out.length() < LCD_W) out += ' ';   // kalanı boşlukla temizle
  } else {
    String src = scrollSrc + "    ";                 // sona 4 boşluk = döngü boşluğu
    int n = src.length();
    for (int i = 0; i < LCD_W; i++) {
      out += src.charAt((scrollPos + i) % n);
    }
  }
  lcd.setCursor(0, 1);
  lcd.print(out);
}

// 1. satırı yazar — yalnızca metin değiştiyse (titremeyi önler).
void setLine1(const String& s) {
  if (s == lcdLine1) return;
  lcdLine1 = s;
  String p = s;
  while ((int)p.length() < LCD_W) p += ' ';
  lcd.setCursor(0, 0);
  lcd.print(p.substring(0, LCD_W));
}

// 2. satır kaynak metnini ayarlar; aynı metinse kaymayı bozmadan korur.
void setInfo(const String& s) {
  if (s == scrollSrc) return;
  scrollSrc = s;
  scrollPos = 0;
  renderLine2();
}

// Tek bir kaydırma adımı — periyodik çağrılır (kısa metin kaymaz).
void stepScroll() {
  if ((int)scrollSrc.length() <= LCD_W) return;
  int n = scrollSrc.length() + 4;
  scrollPos = (scrollPos + 1) % n;
  renderLine2();
}

// İki satırlık statik mesaj (boot/hata ekranları için).
void lcdYaz(const String& satir1, const String& satir2) {
  setLine1(satir1);
  setInfo(satir2);
}

void setGreen() {
  digitalWrite(PIN_GREEN, HIGH);
  digitalWrite(PIN_RED,   LOW);

  if (!kapiAcik) {
    kapiServo.write(SERVO_ACIK);   // Saat yönünde 90° döndür
    kapiAcik = true;
    acilmaZamani = millis();       // Açılma anını kaydet
  }
}

void setRed() {
  digitalWrite(PIN_GREEN, LOW);
  digitalWrite(PIN_RED,   HIGH);

  if (kapiAcik) {
    kapiServo.write(SERVO_KAPALI);  // Saat yönünün tersine 90° döndür (eski hale)
    kapiAcik = false;
  }
}

bool pingServer() {
  HTTPClient http;
  String url = "http://" + String(SERVER_IP) + ":" + SERVER_PORT + "/api/arduino/ping";
  http.begin(url);
  http.addHeader("X-API-Key", API_KEY);
  int code = http.GET();
  http.end();
  return (code == 200);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_RED,   OUTPUT);

  // Servo başlangıç pozisyonu
  kapiServo.attach(PIN_SERVO);
  kapiServo.write(SERVO_KAPALI);
  kapiAcik = false;

  setRed();   // Başlangıç: kırmızı (geçemez), kapı kapalı

  Wire.begin(21, 22);   // SDA=21, SCL=22
  lcd.init();
  lcd.backlight();

  lcdYaz("Sisteme", "baglaniliyor...");

  // WiFi bağlan
  WiFi.begin(SSID, PASSWORD);
  int deneme = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    deneme++;
    if (deneme > 30) {
      setRed();
      lcdYaz("WiFi Hatasi!", "Kontrol edin");
      Serial.println("WiFi baglanamiyor, yeniden baslatiliyor...");
      delay(5000);
      ESP.restart();
    }
  }

  Serial.print("WiFi baglandi. IP: ");
  Serial.println(WiFi.localIP());
  lcdYaz("WiFi Baglandi", WiFi.localIP().toString());
  delay(1500);

  // Sunucu ping
  lcdYaz("Sunucu", "bekleniyor...");
  int pingDeneme = 0;
  while (!pingServer()) {
    delay(1000);
    pingDeneme++;
    if (pingDeneme > 15) {
      lcdYaz("Sunucu Hatasi!", "Baglanamadi");
      Serial.println("Sunucu yanit vermiyor!");
      delay(5000);
      break;
    }
  }

  setRed();
  lcdYaz("KAPI KAPALI", "Sistem hazir - Plaka okutunuz");
}

// Sunucuyu sorgular: "<signal>|<info>" cevabını ayrıştırır,
// LED/servo/LCD durumunu günceller. Bloklamadan loop() içinden çağrılır.
void pollServer() {
  HTTPClient http;
  String url = "http://" + String(SERVER_IP) + ":" + SERVER_PORT + "/api/arduino/state";
  http.begin(url);
  http.addHeader("X-API-Key", API_KEY);
  http.setTimeout(1500);

  int code = http.GET();

  if (code == 200) {
    String body = http.getString();
    body.trim();
    Serial.println("Sunucu yaniti: " + body);

    // Cevap formati: "<signal>|<info>"  (örn. "1|Borc yok", "0|Borc: 600TL...")
    int sep = body.indexOf('|');
    int sig;
    String info;
    if (sep >= 0) {
      sig  = body.substring(0, sep).toInt();
      info = body.substring(sep + 1);
    } else {
      sig  = body.toInt();   // Eski format (yalniz "1"/"0") ile uyumluluk
      info = "";
    }
    info.trim();

    if (sig == 1) {
      if (!sureDoldu) {              // Süre dolup kapandıysa, sunucu 0 olana dek açma
        setGreen();
        setLine1("KAPI ACIK");
        setInfo(info.length() ? info : "Gecebilirsiniz");
      }
    } else {
      sureDoldu = false;            // Sunucu sıfırlandı, yeni açılışa hazır
      setRed();
      setLine1("KAPI KAPALI");
      setInfo(info.length() ? info : "Plaka okutunuz");
    }

  } else if (code == 401) {
    setRed();
    setLine1("API Key Hatasi");
    setInfo("Kod: 401");
    Serial.println("API Key yanlis!");

  } else {
    setRed();
    setLine1("Sunucu Hatasi");
    setInfo("Kod: " + String(code));
    Serial.println("HTTP Hata: " + String(code));
  }

  http.end();
}

void loop() {
  unsigned long now = millis();

  // ── WiFi kontrol ──
  if (WiFi.status() != WL_CONNECTED) {
    setRed();
    setLine1("WiFi Kesildi!");
    setInfo("Yeniden baglaniliyor...");
    WiFi.reconnect();
    stepScroll();      // Ekran kaymaya devam etsin
    delay(300);
    return;
  }

  // ── Periyodik sunucu sorgusu (bloklamadan) ──
  if (now - lastPoll >= POLL_INTERVAL_MS) {
    lastPoll = now;
    pollServer();
  }

  // ── Kapı açıldıktan 5 saniye sonra otomatik kapan ──
  if (kapiAcik && (millis() - acilmaZamani >= ACIK_KALMA_MS)) {
    setRed();
    sureDoldu = true;
    setLine1("KAPI KAPALI");
    // 2. satırdaki borç/abonelik bilgisi korunur — sürücü okumaya devam etsin
    Serial.println("5 saniye doldu, kapi kapatildi.");
  }

  // ── LCD 2. satır kaydırma (marquee) ──
  if (now - lastScroll >= SCROLL_INTERVAL_MS) {
    lastScroll = now;
    stepScroll();
  }
}