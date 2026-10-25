from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserSettingUpdate(BaseModel):
    building_name: str = "AquaGuard Demo"
    building_type: str = "Household"
    number_of_users: int = 8
    number_of_tanks: int = 1
    tank_capacity_l: float = 2500.0
    pipe_diameter_mm: float = 50.0
    daily_consumption_target_l: float = 1800.0
    monitoring_mode: Literal["Demo", "Physical IoT", "Hybrid"] = "Demo"
    location_name: str = "Demo Campus"
    min_ph: float = 6.5
    max_ph: float = 8.5
    turbidity_max_ntu: float = 2.0
    low_tank_threshold_pct: float = 20.0
    high_flow_threshold_lpm: float = 70.0
    leak_sensitivity: float = 15.0
    temp_warning_high_c: float = 32.0
    temp_warning_low_c: float = 5.0
    email_notifications: bool = False
    simulator_mode: str = "Normal Mode"


class DeviceReading(BaseModel):
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
    def validate_sensor_value(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if value == float("nan") or value == float("inf"):
            raise ValueError("sensor values must be finite numbers")
        return value


class AlertMessage(BaseModel):
    alert_type: str
    severity: str = "medium"
    explanation: str
    suggested_action: str = "Review the system and inspect the affected sensor."


class UserRecord(BaseModel):
    id: int
    email: str
    onboarding_complete: bool
    model_config = ConfigDict(from_attributes=True)
