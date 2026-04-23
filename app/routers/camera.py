"""
Kamera router — canlı WebSocket akışı + giriş/çıkış işlemleri.

Endpoints:
    GET  /camera              → canlı kamera sayfası
    WS   /ws/stream           → WebSocket frame akışı (detect + OCR)
    POST /api/camera/entry    → giriş (plaka oku → DB kontrol → kapı aç)
    POST /api/camera/exit     → çıkış (plaka oku → session kapat → kapı aç)
    POST /api/camera/detect   → sadece tespit (giriş/çıkış yapmadan)

Thread pool notu:
    YOLO ve EasyOCR CPU-bound işlemler. FastAPI'nin async event loop'unu
    bloke etmemek için run_in_threadpool (starlette) ile çalıştırılır.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_staff_user
from app.models.user import User
from app.services.gate_controller import GateController
from app.services.plate_checker import PlateChecker

router = APIRouter(tags=["camera"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
logger = logging.getLogger(__name__)

# Snapshot kayıt klasörü
_SNAPSHOT_DIR = Path("outputs/snapshots")


def _get_pipeline():
    """Pipeline singleton — lazy load."""
    from app.config import settings
    from src.pipeline import PlateDetectionPipeline
    return PlateDetectionPipeline.get_instance(
        model_path=settings.model_path_abs,
        languages=settings.ocr_language_list,
        conf=settings.YOLO_CONF,
    )


def _save_snapshot(frame_b64: str, prefix: str) -> str | None:
    """Base64 frame'i dosyaya kaydeder, path döndürür."""
    try:
        from datetime import date
        day_dir = _SNAPSHOT_DIR / str(date.today())
        day_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        path = day_dir / f"{prefix}_{ts}.jpg"
        img_bytes = base64.b64decode(frame_b64)
        with open(path, "wb") as f:
            f.write(img_bytes)
        return str(path)
    except Exception as e:
        logger.warning("Snapshot kaydedilemedi: %s", e)
        return None


# ------------------------------------------------------------------
# Kamera sayfaları
# ------------------------------------------------------------------

@router.get("/camera", response_class=HTMLResponse)
async def camera_page(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/camera/entry", status_code=302)


@router.get("/camera/entry", response_class=HTMLResponse)
async def camera_entry_page(
    request: Request,
    user: User = Depends(get_current_staff_user),
):
    return templates.TemplateResponse(request, "camera/entry.html", {"user": user})


@router.get("/camera/exit", response_class=HTMLResponse)
async def camera_exit_page(
    request: Request,
    user: User = Depends(get_current_staff_user),
):
    return templates.TemplateResponse(request, "camera/exit.html", {"user": user})


# ------------------------------------------------------------------
# WebSocket — yardımcı fonksiyon
# ------------------------------------------------------------------

async def _drain_latest_frame(websocket: WebSocket, timeout: float = 5.0) -> str | None:
    """
    WebSocket buffer'ını boşaltır — yalnızca en son frame'i döndürür.

    Kamera client'ı pipeline'dan daha hızlı frame gönderiyorsa eski kareler
    birikmeden drop edilir; pipeline her zaman en güncel kareyle çalışır.
    """
    try:
        latest = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
    except asyncio.TimeoutError:
        return None  # Ping gönderilecek

    # Buffer'da bekleyen ek kareler varsa hepsini oku, sadece sonuncuyu tut
    while True:
        try:
            latest = await asyncio.wait_for(websocket.receive_text(), timeout=0.005)
        except asyncio.TimeoutError:
            break

    return latest


async def _ws_stream_loop(websocket: WebSocket, db: Session, ocr_interval: float = 1.0):
    """
    Ortak WebSocket döngüsü — hem giriş hem çıkış kamerası kullanır.

    FPS stratejisi:
    - Buffer drain: eski kareler drop edilir, pipeline her zaman en son kareyi işler.
    - OCR throttling: ocr_interval saniyede bir OCR çalışır, arada YOLO-only (hızlı) frame gönderilir.
    - Annotation cache: YOLO-only karelerde son annotated frame yeniden gönderilir.
    """
    pipeline = _get_pipeline()
    last_ocr_time = 0.0
    last_ocr_detections: list[dict] = []  # Son OCR sonucunu sakla

    try:
        while True:
            raw = await _drain_latest_frame(websocket, timeout=5.0)
            if raw is None:
                await websocket.send_text(json.dumps({"type": "ping"}))
                continue

            data = json.loads(raw)
            if data.get("action") != "stream":
                continue

            frame_b64 = data.get("frame", "")
            if not frame_b64:
                continue

            img_bytes = base64.b64decode(frame_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            now = time.time()
            run_ocr = (now - last_ocr_time) >= ocr_interval

            # run_ocr=False ise YOLO-only — çok daha hızlı
            result = await run_in_threadpool(pipeline.process_frame, frame, run_ocr)

            if run_ocr:
                last_ocr_time = now
                detections_out = []
                for plate in result.plates:
                    det = {
                        "plate_text": plate.plate_text,
                        "confidence_det": round(plate.confidence_det, 3),
                        "confidence_ocr": round(plate.confidence_ocr, 3),
                        "format_valid": plate.format_valid,
                        "plate_format": plate.plate_format,
                        "bbox": list(plate.bbox),
                        "crop_b64": plate.crop_b64,
                        "subscription_status": None,
                        "customer_name": None,
                        "expires": None,
                    }
                    if plate.plate_text:
                        vehicle_info = _query_vehicle_info(db, plate.plate_text)
                        det.update(vehicle_info)
                    detections_out.append(det)
                # TR plakaları öne al — aynı confidence olduğunda TR tercih edilsin
                detections_out.sort(key=lambda d: (d.get("plate_format") != "TR", -d.get("confidence_det", 0)))
                last_ocr_detections = detections_out
            else:
                # OCR yok — son OCR sonucunu yeniden kullan
                detections_out = last_ocr_detections

            await websocket.send_text(json.dumps({
                "type": "result",
                "annotated_frame": result.annotated_image_b64,
                "detections": detections_out,
                "processing_ms": result.processing_ms,
                "fps": round(1000 / max(result.processing_ms, 1), 1),
            }))

    except WebSocketDisconnect:
        logger.info("WebSocket baglantisi kesildi.")
    except Exception as e:
        logger.exception("WebSocket hatasi: %s", e)
        try:
            await websocket.close()
        except Exception:
            pass


# ------------------------------------------------------------------
# WebSocket — canlı kamera akışı (giriş / çıkış / genel)
# ------------------------------------------------------------------

@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    await _ws_stream_loop(websocket, db)


@router.websocket("/ws/entry")
async def websocket_entry(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    await _ws_stream_loop(websocket, db)


@router.websocket("/ws/exit")
async def websocket_exit(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    await _ws_stream_loop(websocket, db)


def _query_vehicle_info(db: Session, plate_text: str) -> dict:
    """
    Sadece görüntüleme için abonelik + oturum bilgisi sorgular (session açmaz).
    Exact eşleşme yoksa fuzzy arama yapar.
    """
    from app.models.vehicle import Vehicle
    from app.models.subscription import Subscription
    from app.models.parking_session import ParkingSession
    from app.services.plate_checker import PlateChecker
    from sqlalchemy.orm import joinedload
    from datetime import datetime

    # Exact arama
    vehicle = (
        db.query(Vehicle)
        .options(joinedload(Vehicle.customer))
        .filter(Vehicle.plate_number == plate_text, Vehicle.is_active == True)
        .first()
    )

    fuzzy_matched_plate: str | None = None
    if vehicle is None:
        # Fuzzy arama
        checker = PlateChecker(db)
        fuzzy_result = checker._find_vehicle_fuzzy(plate_text)
        if fuzzy_result:
            vehicle, _dist = fuzzy_result
            fuzzy_matched_plate = vehicle.plate_number

    if not vehicle:
        return {
            "subscription_status": "UNKNOWN",
            "customer_name": None,
            "expires": None,
            "can_enter": False,
            "can_exit": False,
            "is_inside": False,
            "fuzzy_matched_plate": None,
        }

    now = datetime.utcnow()
    sub = (
        db.query(Subscription)
        .options(joinedload(Subscription.plan))
        .filter(
            Subscription.vehicle_id == vehicle.id,
            Subscription.status == "active",
            Subscription.end_date > now,
        )
        .first()
    )

    # Aktif oturum kontrolü
    active_session = (
        db.query(ParkingSession)
        .filter(ParkingSession.vehicle_id == vehicle.id, ParkingSession.is_active == True)
        .first()
    )
    is_inside = active_session is not None

    customer_name = vehicle.customer.full_name if vehicle.customer else None

    if sub:
        return {
            "subscription_status": "ACTIVE",
            "customer_name": customer_name,
            "expires": sub.end_date.strftime("%d.%m.%Y"),
            "plan_name": sub.plan.name if sub.plan else None,
            "days_remaining": sub.days_remaining,
            "can_enter": not is_inside,   # aktif abonelik var + içeride değil
            "can_exit": is_inside,        # içerideyse çıkabilir
            "is_inside": is_inside,
            "fuzzy_matched_plate": fuzzy_matched_plate,
        }
    return {
        "subscription_status": "EXPIRED" if vehicle else "NO_SUB",
        "customer_name": customer_name,
        "expires": None,
        "can_enter": False,
        "can_exit": is_inside,   # içerideyse çıkabilir (abonelik bitmişse de)
        "is_inside": is_inside,
        "fuzzy_matched_plate": fuzzy_matched_plate,
    }


# ------------------------------------------------------------------
# REST — Giriş işlemi
# ------------------------------------------------------------------

@router.post("/api/camera/entry")
async def camera_entry(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    """
    Body: { "frame": "base64_jpeg" }
    1. Frame'i pipeline'dan geçir
    2. En yüksek confidence'lı plakayı al
    3. PlateChecker ile DB kontrolü
    4. ALLOW → gate aç + session kaydet
    """
    body = await request.json()
    frame_b64 = body.get("frame", "")

    if not frame_b64:
        raise HTTPException(400, "Frame eksik.")

    # Görüntüyü işle — thread pool
    img_bytes = base64.b64decode(frame_b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Gecersiz goruntu.")

    pipeline = _get_pipeline()
    result = await run_in_threadpool(pipeline.process_frame, frame)

    if not result.plates:
        return {"success": False, "action": "NO_PLATE", "message": "Plaka tespit edilemedi."}

    # En yüksek YOLO confidence'lı plakayı seç
    best = max(result.plates, key=lambda p: p.confidence_det)

    if not best.plate_text:
        return {"success": False, "action": "OCR_FAILED", "message": "Plaka okunamadi."}

    checker = PlateChecker(db)
    check = checker.check_entry(best.plate_text, confidence=best.confidence_det)

    gate_result = "DENIED"
    if check.gate_signal == 1:
        gate = GateController.get_instance()
        opened = await gate.async_open()
        gate_result = "OPENED" if opened else "ERROR"

    # Session'a gate sonucunu kaydet
    if check.session_id:
        from app.models.parking_session import ParkingSession
        session = db.query(ParkingSession).get(check.session_id)
        if session:
            snapshot_path = _save_snapshot(frame_b64, "entry")
            session.entry_snapshot_path = snapshot_path
            session.gate_result = gate_result

    db.commit()

    return {
        "success": check.gate_signal == 1,
        "action": check.action,
        "message": check.message,
        "plate_text": check.plate_text,
        "gate_result": gate_result,
        "customer_name": check.customer_name,
        "subscription_info": check.subscription_info,
        "expiry_warning": check.expiry_warning,
        "fuzzy_match": check.fuzzy_match,
        "fuzzy_original": check.fuzzy_original,
        "annotated_frame": result.annotated_image_b64,
    }


# ------------------------------------------------------------------
# REST — Çıkış işlemi
# ------------------------------------------------------------------

@router.post("/api/camera/exit")
async def camera_exit(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_staff_user),
):
    """Çıkış: plaka oku → session kapat → kapı aç."""
    body = await request.json()
    frame_b64 = body.get("frame", "")

    if not frame_b64:
        raise HTTPException(400, "Frame eksik.")

    img_bytes = base64.b64decode(frame_b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Gecersiz goruntu.")

    pipeline = _get_pipeline()
    result = await run_in_threadpool(pipeline.process_frame, frame)

    if not result.plates:
        return {"success": False, "action": "NO_PLATE", "message": "Plaka tespit edilemedi."}

    best = max(result.plates, key=lambda p: p.confidence_det)

    if not best.plate_text:
        return {"success": False, "action": "OCR_FAILED", "message": "Plaka okunamadi."}

    checker = PlateChecker(db)
    check = checker.check_exit(best.plate_text, confidence=best.confidence_det)

    gate_result = "DENIED"
    if check.gate_signal == 1:
        gate = GateController.get_instance()
        opened = await gate.async_open()
        gate_result = "OPENED" if opened else "ERROR"

    # Session'a snapshot kaydet
    if check.session_id:
        from app.models.parking_session import ParkingSession
        session = db.query(ParkingSession).get(check.session_id)
        if session:
            snapshot_path = _save_snapshot(frame_b64, "exit")
            session.exit_snapshot_path = snapshot_path
            session.gate_result = gate_result

    db.commit()

    return {
        "success": check.gate_signal == 1,
        "action": check.action,
        "message": check.message,
        "plate_text": check.plate_text,
        "gate_result": gate_result,
        "customer_name": check.customer_name,
        "subscription_info": check.subscription_info,
        "fuzzy_match": check.fuzzy_match,
        "fuzzy_original": check.fuzzy_original,
        "annotated_frame": result.annotated_image_b64,
    }


# ------------------------------------------------------------------
# REST — Sadece tespit (giriş/çıkış yapmadan)
# ------------------------------------------------------------------

@router.post("/api/camera/detect")
async def camera_detect(
    request: Request,
    user: User = Depends(get_current_staff_user),
):
    """Frame'den plaka tespiti yapar, DB'ye yazmaz, kapıyı açmaz."""
    body = await request.json()
    frame_b64 = body.get("frame", "")
    if not frame_b64:
        raise HTTPException(400, "Frame eksik.")

    img_bytes = base64.b64decode(frame_b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Gecersiz goruntu.")

    pipeline = _get_pipeline()
    result = await run_in_threadpool(pipeline.process_frame, frame)

    return {
        "plates": [
            {
                "plate_text": p.plate_text,
                "confidence_det": round(p.confidence_det, 3),
                "confidence_ocr": round(p.confidence_ocr, 3),
                "format_valid": p.format_valid,
                "bbox": list(p.bbox),
            }
            for p in result.plates
        ],
        "processing_ms": result.processing_ms,
        "annotated_frame": result.annotated_image_b64,
    }
