from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.models import AlertRecord, UserSetting


def _alert_payload(alert_type: str, severity: str, explanation: str, suggested_action: str, metadata: dict | None = None) -> dict:
    return {
        "alert_type": alert_type,
        "severity": severity,
        "explanation": explanation,
        "suggested_action": suggested_action,
        "metadata": metadata or {},
    }


def create_alert(db: Session, user_id: int, payload: dict[str, Any]) -> AlertRecord:
    alert = AlertRecord(
        user_id=user_id,
        alert_type=payload["alert_type"],
        severity=payload["severity"],
        timestamp=datetime.now(timezone.utc),
        explanation=payload["explanation"],
        suggested_action=payload["suggested_action"],
        status="open",
        acknowledged=False,
        metadata=json.dumps(payload.get("metadata", {})),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def evaluate_alerts(db: Session, user_id: int, settings: UserSetting, readings: dict[str, Any]) -> list[AlertRecord]:
    alerts: list[AlertRecord] = []
    ph = readings.get("ph")
    turbidity = readings.get("turbidity")
    tank = readings.get("tank_level")
    flow = readings.get("flow")
    temperature = readings.get("temperature")
    latest_timestamp = readings.get("timestamp")

    if ph is not None:
        if ph < settings.min_ph or ph > settings.max_ph:
            alerts.append(
                create_alert(
                    db,
                    user_id,
                    _alert_payload(
                        "ph_out_of_range",
                        "high",
                        f"pH reading {ph:.2f} is outside the configured reference range {settings.min_ph:.1f}-{settings.max_ph:.1f}.",
                        "Check the probe calibration and collect a follow-up sample before drawing conclusions.",
                        {"reading": ph, "threshold_min": settings.min_ph, "threshold_max": settings.max_ph, "timestamp": latest_timestamp.isoformat() if latest_timestamp else None},
                    ),
                )
            )

    if turbidity is not None and turbidity > settings.turbidity_max_ntu:
        alerts.append(
            create_alert(
                db,
                user_id,
                _alert_payload(
                    "high_turbidity",
                    "high",
                    f"Turbidity is {turbidity:.2f} NTU, above the configured threshold of {settings.turbidity_max_ntu:.2f} NTU.",
                    "Perform a follow-up water-quality test and inspect the filtration or intake system.",
                    {"reading": turbidity, "threshold": settings.turbidity_max_ntu, "timestamp": latest_timestamp.isoformat() if latest_timestamp else None},
                ),
            )
        )

    if tank is not None and tank < settings.low_tank_threshold_pct:
        alerts.append(
            create_alert(
                db,
                user_id,
                _alert_payload(
                    "low_tank_level",
                    "medium",
                    f"Tank level is {tank:.1f}% which is below the configured low-level threshold of {settings.low_tank_threshold_pct:.1f}%.",
                    "Inspect the water source, review consumption patterns, and plan replenishment or supply review.",
                    {"reading": tank, "threshold": settings.low_tank_threshold_pct, "timestamp": latest_timestamp.isoformat() if latest_timestamp else None},
                ),
            )
        )

    if flow is not None and flow > settings.high_flow_threshold_lpm:
        alerts.append(
            create_alert(
                db,
                user_id,
                _alert_payload(
                    "high_flow_detected",
                    "medium",
                    f"Flow rate is {flow:.1f} L/min, exceeding the configured threshold of {settings.high_flow_threshold_lpm:.1f} L/min.",
                    "Review for running taps, process loads, or possible pipe leakage in the downstream line.",
                    {"reading": flow, "threshold": settings.high_flow_threshold_lpm, "timestamp": latest_timestamp.isoformat() if latest_timestamp else None},
                ),
            )
        )

    if temperature is not None and temperature > settings.temp_warning_high_c:
        alerts.append(
            create_alert(
                db,
                user_id,
                _alert_payload(
                    "high_temperature",
                    "medium",
                    f"Temperature is {temperature:.1f}°C, above the configured warning threshold of {settings.temp_warning_high_c:.1f}°C.",
                    "Check the sensor placement and inspect for heat buildup or flow-related temperature anomalies.",
                    {"reading": temperature, "threshold": settings.temp_warning_high_c, "timestamp": latest_timestamp.isoformat() if latest_timestamp else None},
                ),
            )
        )

    if readings.get("sensor_failure"):
        alerts.append(
            create_alert(
                db,
                user_id,
                _alert_payload(
                    "sensor_failure",
                    "high",
                    "A sensor reading is missing, stale, or invalid, so the current condition may be incomplete.",
                    "Inspect the instrument, verify power and network connectivity, and install a replacement or recalibration check.",
                    {"failure": readings.get("sensor_failure"), "timestamp": latest_timestamp.isoformat() if latest_timestamp else None},
                ),
            )
        )

    return alerts
