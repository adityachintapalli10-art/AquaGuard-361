from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    onboarding_complete: Mapped[bool] = mapped_column(default=False)

    settings: Mapped[Optional["UserSetting"]] = relationship(back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")
    readings: Mapped[list["SensorReading"]] = relationship(back_populates="user")
    alerts: Mapped[list["AlertRecord"]] = relationship(back_populates="user")
    consumption: Mapped[list["ConsumptionRecord"]] = relationship(back_populates="user")


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    building_name: Mapped[str] = mapped_column(String(255), default="AquaGuard Demo")
    building_type: Mapped[str] = mapped_column(String(50), default="Household")
    number_of_users: Mapped[int] = mapped_column(Integer, default=8)
    number_of_tanks: Mapped[int] = mapped_column(Integer, default=1)
    tank_capacity_l: Mapped[float] = mapped_column(Float, default=2500.0)
    pipe_diameter_mm: Mapped[float] = mapped_column(Float, default=50.0)
    daily_consumption_target_l: Mapped[float] = mapped_column(Float, default=1800.0)
    monitoring_mode: Mapped[str] = mapped_column(String(32), default="Demo")
    location_name: Mapped[str] = mapped_column(String(255), default="Demo Campus")
    min_ph: Mapped[float] = mapped_column(Float, default=6.5)
    max_ph: Mapped[float] = mapped_column(Float, default=8.5)
    turbidity_max_ntu: Mapped[float] = mapped_column(Float, default=2.0)
    low_tank_threshold_pct: Mapped[float] = mapped_column(Float, default=20.0)
    high_flow_threshold_lpm: Mapped[float] = mapped_column(Float, default=70.0)
    leak_sensitivity: Mapped[float] = mapped_column(Float, default=15.0)
    temp_warning_high_c: Mapped[float] = mapped_column(Float, default=32.0)
    temp_warning_low_c: Mapped[float] = mapped_column(Float, default=5.0)
    email_notifications: Mapped[bool] = mapped_column(default=False)
    simulator_mode: Mapped[str] = mapped_column(String(32), default="Normal Mode")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped[User] = relationship(back_populates="settings")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=7))

    user: Mapped[User] = relationship(back_populates="sessions")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (UniqueConstraint("user_id", "sensor_id", "measurement_type", "timestamp", name="uq_sensor_value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    sensor_id: Mapped[str] = mapped_column(String(64), default="sensor-1")
    measurement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="")
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="SIMULATED")
    quality_status: Mapped[str] = mapped_column(String(32), default="OK")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    user: Mapped[User] = relationship(back_populates="readings")


class AlertRecord(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="open")
    acknowledged: Mapped[bool] = mapped_column(default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata: Mapped[str] = mapped_column(Text, default="{}")

    user: Mapped[User] = relationship(back_populates="alerts")


class ConsumptionRecord(Base):
    __tablename__ = "consumption_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    consumption_l: Mapped[float] = mapped_column(Float, default=0.0)
    period_label: Mapped[str] = mapped_column(String(32), default="day")

    user: Mapped[User] = relationship(back_populates="consumption")


"""Helper functions used by the API and tests."""

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_user_settings() -> dict:
    return {
        "building_name": "AquaGuard Demo",
        "building_type": "Household",
        "number_of_users": 8,
        "number_of_tanks": 1,
        "tank_capacity_l": 2500.0,
        "pipe_diameter_mm": 50.0,
        "daily_consumption_target_l": 1800.0,
        "monitoring_mode": "Demo",
        "location_name": "Demo Campus",
        "min_ph": 6.5,
        "max_ph": 8.5,
        "turbidity_max_ntu": 2.0,
        "low_tank_threshold_pct": 20.0,
        "high_flow_threshold_lpm": 70.0,
        "leak_sensitivity": 15.0,
        "temp_warning_high_c": 32.0,
        "temp_warning_low_c": 5.0,
        "email_notifications": False,
        "simulator_mode": "Normal Mode",
    }
