from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SensorSample(BaseModel):
    device_id: str = Field(..., min_length=2)
    timestamp: datetime
    flow_lpm: Optional[float] = None
    inlet_flow_lpm: Optional[float] = None
    outlet_flow_lpm: Optional[float] = None
    ph: Optional[float] = None
    turbidity_ntu: Optional[float] = None
    temperature_c: Optional[float] = None
    tank_level_pct: Optional[float] = None
    source: str = "REAL SENSOR"

    @field_validator("flow_lpm", "inlet_flow_lpm", "outlet_flow_lpm", "ph", "turbidity_ntu", "temperature_c", "tank_level_pct")
    @classmethod
    def validate_value(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value == float("nan") or value == float("inf"):
            raise ValueError("sensor values must be finite")
        return value

    model_config = ConfigDict(extra="ignore")
