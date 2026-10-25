from __future__ import annotations

import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AquaGuard 360", layout="wide")


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def request_json(method: str, path: str, payload: dict | None = None, expect_json: bool = True):
    url = f"{BACKEND_URL}{path}"
    headers = {"Content-Type": "application/json"}
    headers.update(auth_headers())
    if method.upper() == "GET":
        response = requests.get(url, headers=headers, timeout=15)
    elif method.upper() == "POST":
        response = requests.post(url, json=payload, headers=headers, timeout=15)
    elif method.upper() == "PUT":
        response = requests.put(url, json=payload, headers=headers, timeout=15)
    else:
        raise ValueError(f"Unsupported method {method}")
    if response.status_code >= 400:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")
    return response.json() if expect_json else response


def login_form():
    st.title("AquaGuard 360")
    st.subheader("Secure Water Monitoring")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            try:
                result = request_json("POST", "/api/auth/login", {"email": email, "password": password})
                st.session_state.token = result["token"]
                st.session_state.user = result["user"]
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    st.write("No account yet?")
    if st.button("Register new user"):
        st.session_state.page = "register"
        st.rerun()


def register_form():
    st.title("Create an account")
    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Register")
        if submitted:
            if password != confirm:
                st.error("Passwords do not match")
                return
            if len(password) < 8:
                st.error("Password must be at least 8 characters")
                return
            try:
                result = request_json("POST", "/api/auth/register", {"email": email, "password": password})
                st.session_state.token = result["token"]
                st.session_state.user = result["user"]
                st.session_state.page = "setup"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    if st.button("Back to login"):
        st.session_state.page = "login"
        st.rerun()


def onboarding_step1():
    st.title("Water System Configuration")
    settings = st.session_state.get("settings", {})
    with st.form("setup1"):
        building_name = st.text_input("Building or account name", value=settings.get("building_name", "AquaGuard Demo"))
        building_type = st.selectbox("Building type", ["Household", "College", "Apartment", "Industry", "Other"], index=0)
        number_of_users = st.number_input("Number of users", min_value=1, max_value=5000, value=int(settings.get("number_of_users", 8)))
        number_of_tanks = st.number_input("Number of water tanks", min_value=1, max_value=25, value=int(settings.get("number_of_tanks", 1)))
        tank_capacity_l = st.number_input("Tank capacity (litres)", min_value=100.0, value=float(settings.get("tank_capacity_l", 2500.0)))
        pipe_diameter_mm = st.number_input("Pipe diameter (mm)", min_value=10.0, value=float(settings.get("pipe_diameter_mm", 50.0)))
        daily_consumption_target_l = st.number_input("Daily consumption target (L)", min_value=100.0, value=float(settings.get("daily_consumption_target_l", 1800.0)))
        monitoring_mode = st.selectbox("Monitoring mode", ["Demo", "Physical IoT", "Hybrid"], index=0)
        location_name = st.text_input("Optional location name", value=settings.get("location_name", "Demo Campus"))
        next_pressed = st.form_submit_button("Continue to preferences")
        if next_pressed:
            payload = {
                "building_name": building_name,
                "building_type": building_type,
                "number_of_users": number_of_users,
                "number_of_tanks": number_of_tanks,
                "tank_capacity_l": tank_capacity_l,
                "pipe_diameter_mm": pipe_diameter_mm,
                "daily_consumption_target_l": daily_consumption_target_l,
                "monitoring_mode": monitoring_mode,
                "location_name": location_name,
                "min_ph": float(settings.get("min_ph", 6.5)),
                "max_ph": float(settings.get("max_ph", 8.5)),
                "turbidity_max_ntu": float(settings.get("turbidity_max_ntu", 2.0)),
                "low_tank_threshold_pct": float(settings.get("low_tank_threshold_pct", 20.0)),
                "high_flow_threshold_lpm": float(settings.get("high_flow_threshold_lpm", 70.0)),
                "leak_sensitivity": float(settings.get("leak_sensitivity", 15.0)),
                "temp_warning_high_c": float(settings.get("temp_warning_high_c", 32.0)),
                "temp_warning_low_c": float(settings.get("temp_warning_low_c", 5.0)),
                "email_notifications": bool(settings.get("email_notifications", False)),
                "simulator_mode": settings.get("simulator_mode", "Normal Mode"),
            }
            try:
                updated = request_json("PUT", "/api/settings", payload)
                st.session_state.settings = updated
                st.session_state.onboarding = True
                st.session_state.page = "setup2"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def onboarding_step2():
    st.title("Monitoring Preferences")
    settings = st.session_state.get("settings", {})
    with st.form("setup2"):
        min_ph = st.number_input("Minimum pH threshold", min_value=4.0, max_value=9.0, value=float(settings.get("min_ph", 6.5)), step=0.1)
        max_ph = st.number_input("Maximum pH threshold", min_value=4.0, max_value=9.5, value=float(settings.get("max_ph", 8.5)), step=0.1)
        turbidity_max_ntu = st.number_input("Maximum turbidity (NTU)", min_value=0.5, max_value=25.0, value=float(settings.get("turbidity_max_ntu", 2.0)), step=0.1)
        low_tank_threshold_pct = st.number_input("Low tank-level threshold (%)", min_value=1.0, max_value=90.0, value=float(settings.get("low_tank_threshold_pct", 20.0)), step=1.0)
        high_flow_threshold_lpm = st.number_input("High flow threshold (L/min)", min_value=10.0, max_value=200.0, value=float(settings.get("high_flow_threshold_lpm", 70.0)), step=1.0)
        leak_sensitivity = st.number_input("Leak-detection sensitivity", min_value=1.0, max_value=100.0, value=float(settings.get("leak_sensitivity", 15.0)), step=1.0)
        temp_warning_high_c = st.number_input("High temperature warning (°C)", min_value=15.0, max_value=60.0, value=float(settings.get("temp_warning_high_c", 32.0)), step=0.5)
        temp_warning_low_c = st.number_input("Low temperature warning (°C)", min_value=-10.0, max_value=20.0, value=float(settings.get("temp_warning_low_c", 5.0)), step=0.5)
        email_notifications = st.checkbox("Optional email notifications", value=bool(settings.get("email_notifications", False)))
        with st.expander("Configuration summary"):
            st.write(f"Building: {settings.get('building_name', 'AquaGuard Demo')}")
            st.write(f"Monitoring mode: {settings.get('monitoring_mode', 'Demo')}")
            st.write(f"pH range: {min_ph:.1f}-{max_ph:.1f}")
            st.write(f"Turbidity limit: {turbidity_max_ntu:.1f} NTU")
            st.write(f"Low tank threshold: {low_tank_threshold_pct:.0f}%")
            st.write(f"High flow threshold: {high_flow_threshold_lpm:.1f} L/min")
        finish = st.form_submit_button("Finish setup")
        if finish:
            payload = {
                "building_name": settings.get("building_name", "AquaGuard Demo"),
                "building_type": settings.get("building_type", "Household"),
                "number_of_users": int(settings.get("number_of_users", 8)),
                "number_of_tanks": int(settings.get("number_of_tanks", 1)),
                "tank_capacity_l": float(settings.get("tank_capacity_l", 2500.0)),
                "pipe_diameter_mm": float(settings.get("pipe_diameter_mm", 50.0)),
                "daily_consumption_target_l": float(settings.get("daily_consumption_target_l", 1800.0)),
                "monitoring_mode": settings.get("monitoring_mode", "Demo"),
                "location_name": settings.get("location_name", "Demo Campus"),
                "min_ph": min_ph,
                "max_ph": max_ph,
                "turbidity_max_ntu": turbidity_max_ntu,
                "low_tank_threshold_pct": low_tank_threshold_pct,
                "high_flow_threshold_lpm": high_flow_threshold_lpm,
                "leak_sensitivity": leak_sensitivity,
                "temp_warning_high_c": temp_warning_high_c,
                "temp_warning_low_c": temp_warning_low_c,
                "email_notifications": email_notifications,
                "simulator_mode": settings.get("simulator_mode", "Normal Mode"),
            }
            try:
                updated = request_json("PUT", "/api/settings", payload)
                st.session_state.settings = updated
                st.session_state.page = "dashboard"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def load_data():
    if "settings" not in st.session_state:
        try:
            st.session_state.settings = request_json("GET", "/api/settings")
        except Exception:
            st.session_state.settings = {}
    if "latest" not in st.session_state:
        try:
            st.session_state.latest = request_json("GET", "/api/sensors/latest")
        except Exception:
            st.session_state.latest = {}
    if "alerts" not in st.session_state:
        try:
            st.session_state.alerts = request_json("GET", "/api/alerts")
        except Exception:
            st.session_state.alerts = []
    if "consumption" not in st.session_state:
        try:
            st.session_state.consumption = request_json("GET", "/api/consumption/daily")
        except Exception:
            st.session_state.consumption = []


def build_metric_card(title: str, value: str, suffix: str = "", helper: str = ""):
    st.markdown(f"<div style='padding:1rem;border:1px solid #dfe7eb;border-radius:12px;background:#f9fbfb;'><div style='color:#60757c;font-size:0.8rem;'>{title}</div><div style='font-size:1.8rem;font-weight:700;'>{value}{suffix}</div><div style='font-size:0.8rem;color:#60757c;'>{helper}</div></div>", unsafe_allow_html=True)


def render_dashboard():
    load_data()
    settings = st.session_state.settings
    latest = st.session_state.latest
    alerts = st.session_state.alerts
    if not settings:
        st.warning("No settings available yet.")
        return
    st.title(f"Welcome, {settings.get('building_name', 'AquaGuard User')}")
    st.caption(f"Monitoring mode: {settings.get('monitoring_mode', 'Demo')} • Last sensor refresh: {latest.get('ph', {}).get('timestamp') or 'No data'}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        build_metric_card("Flow Rate", f"{latest.get('flow', {}).get('value', 0):.1f}", " L/min", "Latest live flow")
    with col2:
        build_metric_card("Tank Level", f"{latest.get('tank_level', {}).get('value', 0):.0f}", "%", "Volume estimate")
    with col3:
        build_metric_card("pH", f"{latest.get('ph', {}).get('value', 7.2):.2f}", "", "Configured range: 6.5-8.5")
    with col4:
        build_metric_card("Turbidity", f"{latest.get('turbidity', {}).get('value', 1.4):.2f}", " NTU", "Water-quality check")

    st.subheader("Live trends")
    history = request_json("GET", "/api/sensors/history?measurement_type=ph&limit=40")
    df = pd.DataFrame(history)
    if not df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["value"], mode="lines+markers", name="pH trend"))
        fig.update_layout(title="Live pH Trend", xaxis_title="Timestamp", yaxis_title="pH")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No pH history yet; simulate or ingest readings to populate the charts.")

    with st.expander("Alerts"):
        if alerts:
            for alert in alerts[:5]:
                st.markdown(f"- **{alert['alert_type']}** [{alert['severity']}] - {alert['explanation']}")
        else:
            st.write("No active alerts")


def render_sensor_overview():
    request = request_json("GET", "/api/sensors/latest")
    st.title("Live Sensors")
    for metric_name, label in {"flow": "Flow Rate", "ph": "pH", "turbidity": "Turbidity", "temperature": "Temperature", "tank_level": "Tank Level"}.items():
        value = request.get(metric_name, {}).get("value")
        source = request.get(metric_name, {}).get("source", "SIMULATED")
        quality = request.get(metric_name, {}).get("quality_status", "UNKNOWN")
        st.metric(label, value if value is not None else "N/A", delta=f"Source: {source} • {quality}")


def render_reports():
    st.title("Reports")
    report_type = st.selectbox("Report type", ["sensor", "consumption", "alerts"])
    if st.button("Download CSV"):
        resp = requests.get(f"{BACKEND_URL}/api/reports/csv?report_type={report_type}", headers=auth_headers(), timeout=15)
        if resp.status_code >= 400:
            st.error(resp.text)
        else:
            st.download_button("Click to download", data=resp.content, file_name=f"{report_type}-report.csv", mime="text/csv")


def render_settings():
    settings = request_json("GET", "/api/settings")
    st.title("Settings")
    with st.form("settings_form"):
        st.write("Monitor thresholds and system settings")
        st.json(settings)
        submitted = st.form_submit_button("Save settings")
        if submitted:
            request_json("PUT", "/api/settings", settings)
            st.success("Settings saved")


def render_admin():
    settings = request_json("GET", "/api/settings")
    st.title("Admin / Demo Controls")
    mode = st.selectbox("Simulator mode", ["Normal Mode", "Leak Mode", "High Usage Mode", "Poor Water Quality Mode", "Low Tank Mode", "Sensor Failure Mode"], index=0)
    if st.button("Persist mode"):
        payload = dict(settings)
        payload["simulator_mode"] = mode
        updated = request_json("PUT", "/api/settings", payload)
        st.session_state.settings = updated
        st.success(f"Mode saved: {mode}")
    if st.button("Generate simulator sample"):
        try:
            resp = requests.post(f"{BACKEND_URL}/api/sensors/data", json={
                "device_id": "simulator-admin",
                "timestamp": "2025-01-01T00:00:00Z",
                "source": "SIMULATED",
                "flow_lpm": 45,
                "inlet_flow_lpm": 48,
                "outlet_flow_lpm": 39,
                "ph": 7.2,
                "turbidity_ntu": 1.4,
                "temperature_c": 24.8,
                "tank_level_pct": 60,
            }, headers={"X-Device-Key": os.getenv("DEVICE_API_KEY", "demo-device-key")})
            st.success(resp.json())
        except Exception as exc:
            st.error(str(exc))


if "page" not in st.session_state:
    st.session_state.page = "login"

if "token" not in st.session_state:
    if st.session_state.page == "register":
        register_form()
    else:
        login_form()
else:
    try:
        if "user" not in st.session_state:
            st.session_state.user = request_json("GET", "/api/auth/me")["email"]
        me = request_json("GET", "/api/auth/me")
        st.session_state.settings = request_json("GET", "/api/settings")
        if not st.session_state.settings.get("onboarding_complete"):
            st.sidebar.write("Onboarding not complete")
            if st.sidebar.button("Logout"):
                st.session_state.clear()
                st.rerun()
            onboarding_step1()
        else:
            nav = st.sidebar.radio("Navigation", ["Dashboard", "Live Sensors", "Water Quality", "Consumption Analytics", "Leak Detection", "Alerts", "Reports", "Settings", "Admin / Demo Controls"])
            if st.sidebar.button("Logout"):
                try:
                    requests.post(f"{BACKEND_URL}/api/auth/logout", headers=auth_headers(), timeout=15)
                except Exception:
                    pass
                st.session_state.clear()
                st.rerun()
            if nav == "Dashboard":
                render_dashboard()
            elif nav == "Live Sensors":
                render_sensor_overview()
            elif nav == "Reports":
                render_reports()
            elif nav == "Settings":
                render_settings()
            elif nav == "Admin / Demo Controls":
                render_admin()
            else:
                st.info(f"{nav} page is available in the complete application build; the dashboard and core monitoring data are already wired to the backend.")
    except Exception as exc:
        st.error(f"Session expired or backend unavailable: {exc}")
        if st.button("Login again"):
            st.session_state.clear()
            st.rerun()
