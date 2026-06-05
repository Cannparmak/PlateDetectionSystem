from src.postprocess.text_cleaner import PlateCleaner
c = PlateCleaner()

print("=== normalize() testleri ===")
normalize_cases = [
    ("K9501AT",   "GENERIC", "Bulgar plaka temiz"),
    ("K9S0147",   "GENERIC", "Bulgar plaka OCR hatali"),
    ("34ABC123",  "TR",      "TR 3harf+3rakam"),
    ("34AB1234",  "TR",      "TR 2harf+4rakam"),
    ("34ABC12",   "TR",      "TR 3harf+2rakam"),
    ("34A1234",   "TR",      "TR 1harf+4rakam"),
    ("06AB123",   "TR",      "TR kisa"),
    ("81YZ99",    "TR",      "TR minimum"),
    ("34ABC1234", "GENERIC", "TR GECERSIZ 3harf+4rakam"),
    ("84ABC332",  "GENERIC", "Sahte TR il=84"),
    ("O6AB123",   "TR",      "TR O->0 OCR hatasi"),
    ("3AABC123",  "TR",      "TR A->4 OCR hatasi"),
    ("AB12CDE",   "UK",      "Ingiltere"),
    ("AB123CD",   "FR",      "Fransa"),
    ("1234ABC",   "ES",      "Ispanya"),
]

all_ok = True
for raw, exp, desc in normalize_cases:
    text, valid, fmt = c.normalize(raw)
    status = "OK  " if fmt == exp else "FAIL"
    if fmt != exp:
        all_ok = False
    print(f"{status}  {raw:<15} -> {text:<12}  fmt={fmt:<8}  beklenen={exp:<8}  ({desc})")

print()
print("=== is_fake_tr() testleri ===")
fake_cases = [
    ("84ABC123",  True,  "il=84 sahte TR"),
    ("99ZZ99",    True,  "il=99 sahte TR"),
    ("34ABC1234", False, "gecersiz kombinasyon ama TR shape degil artik"),
    ("34ABC123",  False, "gecerli TR"),
    ("01A11",     False, "gecerli TR kisa"),
    ("K9501AT",   False, "yabanci plaka"),
]
for raw, exp, desc in fake_cases:
    result = c.is_fake_tr(c.clean(raw))
    status = "OK  " if result == exp else "FAIL"
    if result != exp:
        all_ok = False
    print(f"{status}  {raw:<15}  fake_tr={result}  beklenen={exp}  ({desc})")

print()
print("Tum testler gecti." if all_ok else "BAZI TESTLER BASARISIZ!")
