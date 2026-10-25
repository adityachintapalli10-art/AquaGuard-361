from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "demo-device-key")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_payload(mode: str, index: int) -> dict[str, Any]:
    base = {
        "device_id": "simulator-1",
        "timestamp": (_now() - timedelta(minutes=index)).isoformat(),
        "source": "SIMULATED",
        "flow_lpm": 32.0,
        "inlet_flow_lpm": 34.0,
        "outlet_flow_lpm": 30.0,
        "ph": 7.2,
        "turbidity_ntu": 1.4,
        "temperature_c": 24.5,
        "tank_level_pct": 68.0,
    }

    if mode == "Normal Mode":
        base["flow_lpm"] = 30 + math.sin(index / 6) * 8
        base["inlet_flow_lpm"] = base["flow_lpm"] + 2
        base["outlet_flow_lpm"] = base["flow_lpm"] - 1.5
        base["ph"] = 7.2 + math.sin(index / 4) * 0.28
        base["turbidity_ntu"] = 1.4 + math.sin(index / 5) * 0.5
        base["temperature_c"] = 24.5 + math.cos(index / 7) * 1.6
        base["tank_level_pct"] = max(25.0, 68.0 - (index * 0.1))
    elif mode == "Leak Mode":
        base["flow_lpm"] = 48.0 + math.sin(index / 3) * 10
        base["inlet_flow_lpm"] = 52.0
        base["outlet_flow_lpm"] = 38.0
        base["ph"] = 7.1 + math.cos(index / 4) * 0.2
        base["turbidity_ntu"] = 1.7
        base["temperature_c"] = 25.1
        base["tank_level_pct"] = max(18.0, 64.0 - index * 0.2)
    elif mode == "High Usage Mode":
        base["flow_lpm"] = 72.0 + math.sin(index / 2) * 12
        base["inlet_flow_lpm"] = 76.0
        base["outlet_flow_lpm"] = 70.0
        base["ph"] = 7.3
        base["turbidity_ntu"] = 1.6
        base["temperature_c"] = 26.0
        base["tank_level_pct"] = max(15.0, 55.0 - index * 0.3)
    elif mode == "Poor Water Quality Mode":
        base["ph"] = 6.2 + math.sin(index / 6) * 0.6
        base["turbidity_ntu"] = 4.2 + math.cos(index / 4) * 1.2
        base["flow_lpm"] = 34.0
        base["inlet_flow_lpm"] = 35.0
        base["outlet_flow_lpm"] = 33.0
        base["temperature_c"] = 24.9
        base["tank_level_pct"] = 61.0
    elif mode == "Low Tank Mode":
        base["flow_lpm"] = 22.0 + math.sin(index / 4) * 4
        base["inlet_flow_lpm"] = 24.0
        base["outlet_flow_lpm"] = 21.0
        base["ph"] = 7.0
        base["turbidity_ntu"] = 1.3
        base["temperature_c"] = 23.6
        base["tank_level_pct"] = max(8.0, 48.0 - index * 0.7)
    elif mode == "Sensor Failure Mode":
        if index % 3 == 0:
            base["ph"] = None
            base["turbidity_ntu"] = None
            base["flow_lpm"] = None
        else:
            base["ph"] = 7.5
            base["turbidity_ntu"] = 2.1
            base["flow_lpm"] = 28.0
        base["tank_level_pct"] = 52.0
        base["temperature_c"] = 25.1
        base["inlet_flow_lpm"] = 29.0
        base["outlet_flow_lpm"] = 29.0

    return {k: v for k, v in base.items() if v is not None}


def run_once(mode: str = "Normal Mode") -> dict[str, Any]:
    payload = _build_payload(mode, 1)
    response = requests.post(
        f"{BACKEND_URL}/api/sensors/data",
        json=payload,
        headers={"X-Device-Key": DEVICE_API_KEY},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    selected = os.getenv("SIMULATOR_MODE", "Normal Mode")
    print(run_once(selected))
