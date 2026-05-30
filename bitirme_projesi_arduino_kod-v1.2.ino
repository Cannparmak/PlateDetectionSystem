#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ESP32Servo.h>

// ─── AYARLAR ──────────────────────────────────────────────
const char* SSID       = "R";
const char* PASSWORD   = "yusufxxx";
const char* SERVER_IP  = "172.20.10.2";   // Bilgisayarın IP'si (ipconfig ile bak)
const int   SERVER_PORT = 8000;
const char* API_KEY    = "esp32-otopark-2024";  // .env ARDUINO_API_KEY ile aynı

const int PIN_GREEN  = 4;    // D4 → Yeşil LED
const int PIN_RED    = 2;    // D2 → Kırmızı LED
const int PIN_SERVO  = 18;   // D18 → Servo motor

const int POLL_INTERVAL_MS = 2000;   // 2 saniyede bir sorgula

const int SERVO_KAPALI = 0;    // Kapı kapalı pozisyonu (0°)
const int SERVO_ACIK   = 90;   // Kapı açık pozisyonu (90°)
// ─────────────────────────────────────────────────────────

LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo kapiServo;

bool kapiAcik = false;   // Mevcut kapı durumunu takip eder

void lcdYaz(const String& satir1, const String& satir2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(satir1.substring(0, 16));
  lcd.setCursor(0, 1);
  lcd.print(satir2.substring(0, 16));
}

void setGreen() {
  digitalWrite(PIN_GREEN, HIGH);
  digitalWrite(PIN_RED,   LOW);

  if (!kapiAcik) {
    kapiServo.write(SERVO_ACIK);   // Saat yönünde 90° döndür
    kapiAcik = true;
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
  lcdYaz("Sistem Hazir", "Gecis: KAPALI");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setRed();
    lcdYaz("WiFi Kesildi!", "Yeniden bagl.");
    WiFi.reconnect();
    delay(3000);
    return;
  }

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

    if (body == "1") {
      setGreen();
      lcdYaz("KAPI ACIK", "Gecebilirsiniz");
    } else {
      setRed();
      lcdYaz("KAPI KAPALI", "Gecemezsiniz");
    }

  } else if (code == 401) {
    setRed();
    lcdYaz("API Key Hatasi", "Kod: 401");
    Serial.println("API Key yanlis!");

  } else {
    setRed();
    lcdYaz("Sunucu Hatasi!", "Kod: " + String(code));
    Serial.println("HTTP Hata: " + String(code));
  }

  http.end();
  delay(POLL_INTERVAL_MS);
}
