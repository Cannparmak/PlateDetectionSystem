"""
Veritabanı migration scripti — misafir ücretlendirme sistemi için schema güncellemeleri.

Çalıştırma:
    python scripts/migrate.py

Yapılan değişiklikler:
    1. vehicles       → customer_id nullable, is_anonymous kolonu eklendi
    2. parking_sessions → fee alanları eklendi (is_guest, fee_amount, is_paid, vb.)
    3. parking_config → debt_block_threshold eklendi
    4. parking_rate_brackets → yeni tablo oluşturuldu + varsayılan tarife seed'i
    5. users          → kasiyer rolü admin'e dönüştürüldü
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "otopark.db"


def run(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")

    _migrate_vehicles(conn)
    _migrate_parking_sessions(conn)
    _migrate_parking_config(conn)
    _create_parking_rate_brackets(conn)
    _migrate_users_role(conn)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("\n[OK] Migration tamamlandi.")


# ---------------------------------------------------------------------------
# 1. vehicles — customer_id nullable + is_anonymous
# ---------------------------------------------------------------------------

def _migrate_vehicles(conn: sqlite3.Connection) -> None:
    """
    SQLite ALTER TABLE kolon kısıtlaması değiştirmeyi desteklemez.
    Tablo yeniden oluşturulur: customer_id → nullable, is_anonymous → yeni kolon.
    """
    cols = {row[1] for row in conn.execute("PRAGMA table_info(vehicles)")}

    needs_rebuild = True  # customer_id nullable yapılması için her zaman rebuild

    if "is_anonymous" in cols and needs_rebuild is False:
        print("  [ATLA] vehicles tablosu zaten güncel.")
        return

    print("  [vehicles] Tablo yeniden oluşturuluyor (customer_id nullable, is_anonymous)...")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vehicles_new (
            id            INTEGER PRIMARY KEY,
            customer_id   INTEGER REFERENCES customers(id) ON DELETE SET NULL,
            is_anonymous  INTEGER NOT NULL DEFAULT 0,
            plate_number  TEXT NOT NULL UNIQUE,
            plate_display TEXT NOT NULL,
            vehicle_type  TEXT NOT NULL DEFAULT 'otomobil',
            brand         TEXT,
            model         TEXT,
            color         TEXT,
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now'))
        );

        INSERT INTO vehicles_new
            (id, customer_id, is_anonymous, plate_number, plate_display,
             vehicle_type, brand, model, color, is_active, created_at)
        SELECT
            id, customer_id, 0, plate_number, plate_display,
            vehicle_type, brand, model, color, is_active, created_at
        FROM vehicles;

        DROP TABLE vehicles;
        ALTER TABLE vehicles_new RENAME TO vehicles;

        CREATE INDEX IF NOT EXISTS ix_vehicles_customer_id   ON vehicles(customer_id);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_vehicles_plate  ON vehicles(plate_number);
    """)
    print("  [OK] vehicles güncellendi.")


# ---------------------------------------------------------------------------
# 2. parking_sessions — fee alanları
# ---------------------------------------------------------------------------

def _migrate_parking_sessions(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(parking_sessions)")}
    new_cols = {
        "is_guest":             "INTEGER NOT NULL DEFAULT 0",
        "fee_amount":           "REAL",
        "is_paid":              "INTEGER NOT NULL DEFAULT 0",
        "paid_at":              "DATETIME",
        "payment_method":       "TEXT",
        "processed_by_user_id": "INTEGER REFERENCES users(id) ON DELETE SET NULL",
    }
    added = []
    for col, definition in new_cols.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE parking_sessions ADD COLUMN {col} {definition}")
            added.append(col)

    if added:
        print(f"  [OK] parking_sessions: {', '.join(added)} eklendi.")
    else:
        print("  [ATLA] parking_sessions fee alanları zaten mevcut.")


# ---------------------------------------------------------------------------
# 3. parking_config — debt_block_threshold
# ---------------------------------------------------------------------------

def _migrate_parking_config(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(parking_config)")}
    if "debt_block_threshold" not in cols:
        conn.execute(
            "ALTER TABLE parking_config ADD COLUMN debt_block_threshold REAL NOT NULL DEFAULT 500.0"
        )
        print("  [OK] parking_config: debt_block_threshold eklendi.")
    else:
        print("  [ATLA] parking_config.debt_block_threshold zaten mevcut.")


# ---------------------------------------------------------------------------
# 4. parking_rate_brackets — yeni tablo + varsayılan tarife
# ---------------------------------------------------------------------------

_DEFAULT_BRACKETS = [
    ("Ücretsiz",     0,   30,   0.0,  1),
    ("İlk 1 Saat",  30,   60,  50.0,  2),
    ("1–2 Saat",    60,  120,  80.0,  3),
    ("2–4 Saat",   120,  240, 120.0,  4),
    ("4–8 Saat",   240,  480, 180.0,  5),
    ("8–12 Saat",  480,  720, 250.0,  6),
    ("Günlük Tavan",720, 1440, 350.0, 7),
]


def _create_parking_rate_brackets(conn: sqlite3.Connection) -> None:
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if "parking_rate_brackets" not in tables:
        conn.execute("""
            CREATE TABLE parking_rate_brackets (
                id            INTEGER PRIMARY KEY,
                name          TEXT NOT NULL,
                min_minutes   INTEGER NOT NULL,
                max_minutes   INTEGER NOT NULL,
                price         REAL NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                is_active     INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.executemany(
            """INSERT INTO parking_rate_brackets
               (name, min_minutes, max_minutes, price, display_order)
               VALUES (?, ?, ?, ?, ?)""",
            _DEFAULT_BRACKETS,
        )
        print(f"  [OK] parking_rate_brackets oluşturuldu ({len(_DEFAULT_BRACKETS)} dilim eklendi).")
    else:
        existing = conn.execute("SELECT COUNT(*) FROM parking_rate_brackets").fetchone()[0]
        if existing == 0:
            conn.executemany(
                """INSERT INTO parking_rate_brackets
                   (name, min_minutes, max_minutes, price, display_order)
                   VALUES (?, ?, ?, ?, ?)""",
                _DEFAULT_BRACKETS,
            )
            print(f"  [OK] parking_rate_brackets: {len(_DEFAULT_BRACKETS)} varsayılan dilim eklendi.")
        else:
            print("  [ATLA] parking_rate_brackets zaten mevcut.")


# ---------------------------------------------------------------------------
# 5. users — kasiyer → admin
# ---------------------------------------------------------------------------

def _migrate_users_role(conn: sqlite3.Connection) -> None:
    updated = conn.execute(
        "UPDATE users SET role = 'admin' WHERE role = 'kasiyer'"
    ).rowcount
    if updated:
        print(f"  [OK] users: {updated} kasiyer hesabı admin'e dönüştürüldü.")
    else:
        print("  [ATLA] Dönüştürülecek kasiyer hesabı yok.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"HATA: Veritabanı bulunamadı: {DB_PATH}")
        print("Önce uygulamayı çalıştırarak tabloları oluşturun: python run.py")
        sys.exit(1)

    print(f"Migration başlıyor: {DB_PATH}\n")
    with sqlite3.connect(DB_PATH) as conn:
        run(conn)
