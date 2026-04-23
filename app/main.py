"""
OtoparkPro — FastAPI ana uygulama.

Başlatma:
    python run.py
    veya
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import app.models  # Tüm modelleri yükle — relationship çözümü için
from app.config import settings
from app.database import Base, engine
from app.services.gate_controller import GateController

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Startup / Shutdown
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("OtoparkPro baslatiliyor...")

    # Tabloları oluştur (yoksa)
    Base.metadata.create_all(bind=engine)
    logger.info("Veritabani hazir.")

    # Çıktı klasörlerini oluştur
    for d in ["outputs/uploads", "outputs/results", "outputs/snapshots"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Gate controller başlat
    gate = GateController.get_instance()
    logger.info("Gate controller: %s", "BAGLI" if gate.is_connected() else "STUB (donanim yok)")

    # ML Pipeline — lazy, ilk istek geldiğinde yüklenir
    # (warmup burada yapmıyoruz — büyük modeller startup'ı uzatır)
    logger.info("Uygulama hazir: http://localhost:8000")

    yield

    # ── SHUTDOWN ─────────────────────────────────────────────────
    logger.info("Uygulama kapatiliyor...")
    GateController.get_instance().disconnect()


# ------------------------------------------------------------------
# Uygulama
# ------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    description="Otopark yönetim sistemi",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

# Static dosyalar
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# ------------------------------------------------------------------
# Router'ları ekle
# ------------------------------------------------------------------

from app.routers import auth, camera, customers, vehicles, subscriptions, sessions, admin, payment, dashboard

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(camera.router)
app.include_router(customers.router)
app.include_router(vehicles.router)
app.include_router(subscriptions.router)
app.include_router(sessions.router)
app.include_router(admin.router)
app.include_router(payment.router)

# ------------------------------------------------------------------
# Ana sayfa
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


# ------------------------------------------------------------------
# Exception handler'lar
# ------------------------------------------------------------------

@app.exception_handler(401)
async def unauthorized(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Giris yapmaniz gerekiyor."}, status_code=401)
    # Musteri portal istekleri musteri login'e, diger istekler staff login'e
    if request.url.path.startswith("/musteri/"):
        return RedirectResponse("/musteri/login", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.exception_handler(403)
async def forbidden(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Bu islem icin yetkiniz yok."}, status_code=403)
    return RedirectResponse("/dashboard", status_code=302)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Endpoint bulunamadi."}, status_code=404)
    return templates.TemplateResponse(
        request, "errors/404.html", status_code=404
    )


@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.exception("500 hatasi: %s", request.url)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Sunucu hatasi."}, status_code=500)
    return templates.TemplateResponse(
        request, "errors/500.html", status_code=500
    )
