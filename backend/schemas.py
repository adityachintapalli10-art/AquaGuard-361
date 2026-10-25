from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.alerts import evaluate_alerts
from backend.auth import create_session_token, get_current_user, hash_password, verify_password
from backend.database import create_db_and_tables, get_db
from backend.models import AlertRecord, ConsumptionRecord, SensorReading, User, UserSetting, UserSession, default_user_settings, utcnow
from backend.schemas import AlertMessage, DeviceReading, LoginRequest, RegisterRequest, UserSettingUpdate

app = FastAPI(title="AquaGuard 360 API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "demo-device-key")


def ensure_demo_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "demo@aquaguard.local").first()
    if not user:
        user = User(email="demo@aquaguard.local", password_hash=hash_password(os.getenv("DEMO_PASSWORD", "demo123")))
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user.settings:
        settings = UserSetting(user_id=user.id, **default_user_settings())
        db.add(settings)
        db.commit()
    return user


def serialize_settings(settings: UserSetting) -> dict[str, Any]:
    return {
        "building_name": settings.building_name,
        "building_type": settings.building_type,
        "number_of_users": settings.number_of_users,
        "number_of_tanks": settings.number_of_tanks,
        "tank_capacity_l": settings.tank_capacity_l,
        "pipe_diameter_mm": settings.pipe_diameter_mm,
        "daily_consumption_target_l": settings.daily_consumption_target_l,
        "monitoring_mode": settings.monitoring_mode,
        "location_name": settings.location_name,
        "min_ph": settings.min_ph,
        "max_ph": settings.max_ph,
        "turbidity_max_ntu": settings.turbidity_max_ntu,
        "low_tank_threshold_pct": settings.low_tank_threshold_pct,
        "high_flow_threshold_lpm": settings.high_flow_threshold_lpm,
        "leak_sensitivity": settings.leak_sensitivity,
        "temp_warning_high_c": settings.temp_warning_high_c,
        "temp_warning_low_c": settings.temp_warning_low_c,
        "email_notifications": settings.email_notifications,
        "simulator_mode": settings.simulator_mode,
        "onboarding_complete": settings.user.onboarding_complete if settings.user else False,
    }


@app.on_event("startup")
def startup_event() -> None:
    create_db_and_tables()
    db = next(get_db())
    try:
        ensure_demo_user(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "AquaGuard 360 API"}


@app.post("/api/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    normalized_email = payload.email.lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(email=normalized_email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    settings = UserSetting(user_id=user.id, **default_user_settings())
    db.add(settings)
    db.commit()

    token = create_session_token(user, db)
    return {
        "message": "registration successful",
        "token": token,
        "user": {"id": user.id, "email": user.email, "onboarding_complete": user.onboarding_complete},
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_session_token(user, db)
    return {
        "message": "login successful",
        "token": token,
        "user": {"id": user.id, "email": user.email, "onboarding_complete": user.onboarding_complete},
    }


@app.post("/api/auth/logout")
def logout(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        return {"message": "logged out"}
    token = authorization.split(" ", 1)[1]
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()
    return {"message": "logged out"}


@app.get("/api/auth/me")
def auth_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    payload = {"id": current_user.id, "email": current_user.email, "onboarding_complete": current_user.onboarding_complete}
    if settings:
        payload["settings"] = serialize_settings(settings)
    return payload


@app.get("/api/settings")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if settings is None:
        settings = UserSetting(user_id=current_user.id, **default_user_settings())
        db.add(settings)
        db.commit()
    current_user.onboarding_complete = bool(settings.building_name)
    db.commit()
    return serialize_settings(settings)


@app.put("/api/settings")
def put_settings(payload: UserSettingUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    settings = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if settings is None:
        settings = UserSetting(user_id=current_user.id)
        db.add(settings)

    for field, value in payload.model_dump().items():
        if hasattr(settings, field):
            setattr(settings, field, value)

    settings.updated_at = utcnow()
    current_user.onboarding_complete = True
    db.commit()
    db.refresh(settings)
    return serialize_settings(settings)


@app.get("/api/sensors/latest")
def latest_sensors(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    metrics = ["ph", "turbidity", "temperature", "flow", "tank_level", "consumption"]
    latest = {}
    for measurement in metrics:
        reading = (
            db.query(SensorReading)
            .filter(SensorReading.user_id == current_user.id, SensorReading.measurement_type == measurement)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )
        latest[measurement] = {
            "value": reading.value if reading else None,
            "unit": reading.unit if reading else "",
            "source": reading.source if reading else "SIMULATED",
            "quality_status": reading.quality_status if reading else "UNKNOWN",
            "timestamp": reading.timestamp.isoformat() if reading else None,
        }
    return latest


@app.get("/api/sensors/history")
def sensor_history(
    measurement_type: str = Query(default="ph"),
    limit: int = Query(default=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = (
        db.query(SensorReading)
        .filter(SensorReading.user_id == current_user.id, SensorReading.measurement_type == measurement_type)
        .order_by(SensorReading.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "sensor_id": row.sensor_id,
            "measurement_type": row.measurement_type,
            "value": row.value,
            "unit": row.unit,
            "source": row.source,
            "quality_status": row.quality_status,
            "timestamp": row.timestamp.isoformat(),
            "ingested_at": row.ingested_at.isoformat(),
        }
        for row in rows
    ]


@app.post("/api/sensors/data")
def sensor_data(
    payload: DeviceReading,
    x_device_key: str | None = Header(default=None, alias="X-Device-Key"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device key")

    user = ensure_demo_user(db)
    if not payload.device_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_id is required")

    sensor_map = [
        ("flow", "flow_lpm", "L/min"),
        ("inlet_flow", "inlet_flow_lpm", "L/min"),
        ("outlet_flow", "outlet_flow_lpm", "L/min"),
        ("ph", "ph", "pH"),
        ("turbidity", "turbidity_ntu", "NTU"),
        ("temperature", "temperature_c", "°C"),
        ("tank_level", "tank_level_pct", "%"),
    ]

    stored = []
    values = payload.model_dump(exclude_none=True)
    for measurement_type, field_name, unit in sensor_map:
        if field_name not in values:
            continue
        reading = SensorReading(
            user_id=user.id,
            sensor_id=payload.device_id,
            measurement_type=measurement_type,
            unit=unit,
            value=float(values[field_name]),
            source=payload.source or "REAL SENSOR",
            quality_status="OK",
            timestamp=payload.timestamp,
            ingested_at=utcnow(),
        )
        db.add(reading)
        stored.append(reading)

    db.commit()

    settings = db.query(UserSetting).filter(UserSetting.user_id == user.id).first()
    metrics = {
        "ph": next((r.value for r in reversed(stored) if r.measurement_type == "ph"), None),
        "turbidity": next((r.value for r in reversed(stored) if r.measurement_type == "turbidity"), None),
        "tank_level": next((r.value for r in reversed(stored) if r.measurement_type == "tank_level"), None),
        "flow": next((r.value for r in reversed(stored) if r.measurement_type == "flow"), None),
        "temperature": next((r.value for r in reversed(stored) if r.measurement_type == "temperature"), None),
        "timestamp": payload.timestamp,
    }
    if settings:
        evaluate_alerts(db, user.id, settings, metrics)
    return {"status": "accepted", "saved": len(stored), "device_id": payload.device_id}


@app.get("/api/consumption/daily")
def consumption_daily(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(ConsumptionRecord).filter(ConsumptionRecord.user_id == current_user.id).order_by(ConsumptionRecord.timestamp.asc()).all()
    if not rows:
        now = datetime.now(timezone.utc)
        baseline = [
            (now - timedelta(days=7), 148.2),
            (now - timedelta(days=6), 160.5),
            (now - timedelta(days=5), 172.1),
            (now - timedelta(days=4), 185.4),
            (now - timedelta(days=3), 168.7),
            (now - timedelta(days=2), 155.9),
            (now - timedelta(days=1), 176.3),
            (now, 190.2),
        ]
        for ts, amount in baseline:
            db.add(ConsumptionRecord(user_id=current_user.id, timestamp=ts, consumption_l=amount, period_label="day"))
        db.commit()
        rows = db.query(ConsumptionRecord).filter(ConsumptionRecord.user_id == current_user.id).order_by(ConsumptionRecord.timestamp.asc()).all()
    return [{"timestamp": row.timestamp.isoformat(), "consumption_l": row.consumption_l, "period_label": row.period_label} for row in rows]


@app.get("/api/alerts")
def get_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(AlertRecord).filter(AlertRecord.user_id == current_user.id).order_by(AlertRecord.timestamp.desc()).all()
    return [{
        "id": row.id,
        "alert_type": row.alert_type,
        "severity": row.severity,
        "timestamp": row.timestamp.isoformat(),
        "explanation": row.explanation,
        "suggested_action": row.suggested_action,
        "status": row.status,
        "acknowledged": row.acknowledged,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "metadata": json.loads(row.metadata) if row.metadata else {},
    } for row in rows]


@app.post("/api/alerts/test")
def test_alert(payload: AlertMessage, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    alert = AlertRecord(
        user_id=current_user.id,
        alert_type=payload.alert_type,
        severity=payload.severity,
        timestamp=utcnow(),
        explanation=payload.explanation,
        suggested_action=payload.suggested_action,
        status="open",
        acknowledged=False,
        metadata=json.dumps({"source": "manual_test"}),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"status": "created", "id": alert.id, "alert_type": alert.alert_type}


@app.get("/api/reports/csv")
def csv_report(report_type: str = "sensor", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> StreamingResponse:
    if report_type == "sensor":
        rows = db.query(SensorReading).filter(SensorReading.user_id == current_user.id).order_by(SensorReading.timestamp.asc()).all()
        fieldnames = ["timestamp", "sensor_id", "measurement_type", "value", "unit", "source", "quality_status"]
    elif report_type == "consumption":
        rows = db.query(ConsumptionRecord).filter(ConsumptionRecord.user_id == current_user.id).order_by(ConsumptionRecord.timestamp.asc()).all()
        fieldnames = ["timestamp", "consumption_l", "period_label"]
    elif report_type == "alerts":
        rows = db.query(AlertRecord).filter(AlertRecord.user_id == current_user.id).order_by(AlertRecord.timestamp.asc()).all()
        fieldnames = ["timestamp", "alert_type", "severity", "status", "explanation", "suggested_action"]
    else:
        raise HTTPException(status_code=400, detail="Unsupported report type")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        if report_type == "sensor":
            writer.writerow({
                "timestamp": row.timestamp.isoformat(),
                "sensor_id": row.sensor_id,
                "measurement_type": row.measurement_type,
                "value": row.value,
                "unit": row.unit,
                "source": row.source,
                "quality_status": row.quality_status,
            })
        elif report_type == "consumption":
            writer.writerow({
                "timestamp": row.timestamp.isoformat(),
                "consumption_l": row.consumption_l,
                "period_label": row.period_label,
            })
        else:
            writer.writerow({
                "timestamp": row.timestamp.isoformat(),
                "alert_type": row.alert_type,
                "severity": row.severity,
                "status": row.status,
                "explanation": row.explanation,
                "suggested_action": row.suggested_action,
            })

    response = StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{report_type}-report.csv"'
    return response
