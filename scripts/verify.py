"""Onceki degisiklikleri dogrular."""
import sys
sys.path.insert(0, '.')

# 1. Model import testi
from app.models import User, Vehicle, ParkingSession, ParkingConfig, ParkingRateBracket
print('[OK] Tum modeller import edildi.')

# 2. to_display testi
from src.postprocess.text_cleaner import PlateCleaner
c = PlateCleaner()
assert c.to_display('34ABC1234') == '34 ABC 1234'
assert c.to_display('06AB123')   == '06 AB 123'
assert c.to_display('FOREIGN')   == 'FOREIGN'
print('[OK] to_display dogru.')

# 3. PlateVoter testi
from src.pipeline import PlateVoter
v = PlateVoter(window=3)
v.add('34ABC1234', 0.9)
assert v.best() is None
v.add('34ABC1234', 0.8)
assert v.best() == '34ABC1234'
v.add('34AB01234', 0.3)
assert v.best() == '34ABC1234'
print('[OK] PlateVoter dogru.')

# 4. FeeCalculator testi
from app.database import SessionLocal
from app.services.fee_calculator import FeeCalculator
db = SessionLocal()
calc = FeeCalculator(db)
assert calc.calculate(10)   == 0.0
assert calc.calculate(61)   == 80.0
assert calc.calculate(121)  == 120.0
assert calc.calculate(1500) == 400.0
print('[OK] FeeCalculator dogru.')
db.close()

# 5. DB schema
import sqlite3
conn = sqlite3.connect('otopark.db')
cols_v  = {r[1] for r in conn.execute('PRAGMA table_info(vehicles)')}
cols_ps = {r[1] for r in conn.execute('PRAGMA table_info(parking_sessions)')}
cols_pc = {r[1] for r in conn.execute('PRAGMA table_info(parking_config)')}
tables  = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
assert 'is_anonymous'          in cols_v
assert 'fee_amount'            in cols_ps
assert 'debt_block_threshold'  in cols_pc
assert 'parking_rate_brackets' in tables
n = conn.execute("SELECT COUNT(*) FROM users WHERE role='kasiyer'").fetchone()[0]
assert n == 0, 'Kasiyer hesabi hala var!'
print('[OK] DB schema tam.')
conn.close()

print()
print('=== TUM KONTROLLER BASARILI ===')
