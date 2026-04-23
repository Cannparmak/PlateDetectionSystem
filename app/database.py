"""
SQLAlchemy veritabanı bağlantısı.

Kullanım:
    from app.database import get_db, engine, Base

    # Tablo oluşturma (startup'ta)
    Base.metadata.create_all(bind=engine)

    # Dependency injection (FastAPI route'larında)
    def my_route(db: Session = Depends(get_db)):
        ...
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ------------------------------------------------------------------
# Engine
# ------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite için gerekli
    echo=False,
)


# SQLite WAL modu — eş zamanlı okuma/yazma için daha iyi performans
@event.listens_for(engine, "connect")
def _set_wal_mode(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")   # FK kısıtlamalarını aktif et
    cursor.execute("PRAGMA synchronous=NORMAL") # Hız/güvenlik dengesi
    cursor.close()


# ------------------------------------------------------------------
# Session factory
# ------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ------------------------------------------------------------------
# Declarative base (tüm modeller buradan türeyecek)
# ------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ------------------------------------------------------------------
# FastAPI Dependency
# ------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI route dependency — her istek için DB session açar ve kapatır.

    Kullanım:
        @router.get("/ornek")
        def ornek(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
