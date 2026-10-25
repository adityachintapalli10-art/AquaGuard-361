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


def request_json(method: str, path: str, payload: dict | None = None) -> Any:
    url = f"{BACKEND_URL}{path}"
    headers = {"Content-Type": "application/json"}
    headers.update(auth_headers())
    response = requests.request(method.upper(), url, json=payload, headers=headers, timeout=20)
    if response.status_code >= 400:
        raise RuntimeError(f"API error {response.status_code}: {response.text}")
    return response.json()


def source_tag(source: str | None) -> str:
    mapping = {
        "REAL SENSOR": "REAL SENSOR",
        "SIMULATED": "SIMULATED",
        "STALE": "STALE",
        "SENSOR OFFLINE": "SENSOR OFFLINE",
    }
    value = (source or "SIMULATED").upper()
    return mapping.get(value, value)


def login_form() -> None:
    st.title("AquaGuard 360")
    st.subheader("Secure water monitoring and quality dashboard")
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
    if st.button("Register new user"):
        st.session_state.page = "register"
        st.rerun()


def register_form() -> None:
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
                st.session_state.page = "setup1"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    if st.button("Back to login"):
        st.session_state.page = "login"
        st.rerun()


def load_session_data() -> None:
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


def onboarding_step1() -> None:
    st.title("Water System Configuration")
    settings = st.session_state.get("settings", {})
    with st.form("setup1"):
        building_name = st.text_input("Building or account name", value=settings.get("building_name", "AquaGuard Demo"))
        building_type = st.selectbox("Building type", ["Household", "College", "Apartment", "Industry", "Other"], index=0)
        number_of_users = st.number_input("Number of users", min_value=1, value=int(settings.get("number_of_users", 8)))
        number_of_tanks = st.number_input("Number of water tanks", min_value=1, value=int(settings.get("number_of_tanks", 1)))
        tank_capacity_l = st.number_input("Tank capacity (L)", min_value=100.0, value=float(settings.get("tank_capacity_l", 2500.0)))
        pipe_diameter_mm = st.number_input("Pipe diameter (mm)", min_value=10.0, value=float(settings.get("pipe_diameter_mm", 50.0)))
        daily_consumption_target_l = st.number_input("Daily consumption target (L)", min_value=100.0, value=float(settings.get("daily_consumption_target_l", 1800.0)))
        monitoring_mode = st.selectbox("Monitoring mode", ["Demo", "Physical IoT", "Hybrid"], index=0)
        location_name = st.text_input("Optional location name", value=settings.get("location_name", "Demo Campus"))
        next_step = st.form_submit_button("Continue to preferences")
        if next_step:
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
            }
            try:
                updated = request_json("PUT", "/api/settings", payload)
                st.session_state.settings = updated
                st.session_state.page = "setup2"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def onboarding_step2() -> None:
    st.title("Monitoring Preferences")
    settings = st.session_state.get("settings", {})
    with st.form("setup2"):
        min_ph = st.number_input("Minimum pH threshold", min_value=4.0, max_value=9.0, value=float(settings.get("min_ph", 6.5)), step=0.1)
        max_ph = st.number_input("Maximum pH threshold", min_value=4.0, max_value=9.5, value=float(settings.get("max_ph", 8.5)), step=0.1)
        turbidity_max_ntu = st.number_input("Maximum turbidity (NTU)", min_value=0.5, max_value=25.0, value=float(settings.get("turbidity_max_ntu", 2.0)), step=0.1)
        low_tank_threshold_pct = st.number_input("Low tank threshold (%)", min_value=1.0, max_value=90.0, value=float(settings.get("low_tank_threshold_pct", 20.0)), step=1.0)
        high_flow_threshold_lpm = st.number_input("High flow threshold (L/min)", min_value=10.0, max_value=200.0, value=float(settings.get("high_flow_threshold_lpm", 70.0)), step=1.0)
        leak_sensitivity = st.number_input("Leak detection sensitivity", min_value=1.0, max_value=100.0, value=float(settings.get("leak_sensitivity", 15.0)), step=1.0)
        temp_warning_high_c = st.number_input("High temperature warning (°C)", min_value=15.0, max_value=60.0, value=float(settings.get("temp_warning_high_c", 32.0)), step=0.5)
        temp_warning_low_c = st.number_input("Low temperature warning (°C)", min_value=-10.0, max_value=20.0, value=float(settings.get("temp_warning_low_c", 5.0)), step=0.5)
        email_notifications = st.checkbox("Optional email notifications", value=bool(settings.get("email_notifications", False)))
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


def _metric_card(title: str, value: str, suffix: str = "", helper: str = "") -> None:
    st.markdown(
        f"<div style='padding:1rem; border:1px solid #dfe7ed; border-radius:12px; background:#f5f9fb; margin-bottom:1rem;'>"
        f"<div style='font-size:0.75rem; color:#4a6572;'>{title}</div>"
        f"<div style='font-size:2rem; font-weight:700; color:#0a3142;'>{value}<span style='font-size:0.8rem; color:#4a6572;'>{suffix}</span></div>"
        f"<div style='font-size:0.75rem; color:#5a7280;'>{helper}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    load_session_data()
    settings = st.session_state.get("settings", {})
    latest = st.session_state.get("latest", {})
    alerts = st.session_state.get("alerts", [])

    st.title(f"Welcome, {settings.get('building_name', 'AquaGuard User')}")
    st.caption(f"Monitoring mode: {settings.get('monitoring_mode', 'Demo')} • Latest sensor timestamp: {latest.get('ph', {}).get('timestamp') or 'No data'}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card("Flow rate", f"{latest.get('flow', {}).get('value') if latest.get('flow', {}).get('value') is not None else 0:.1f}", " L/min", source_tag(latest.get('flow', {}).get('source')))
    with col2:
        _metric_card("Tank level", f"{latest.get('tank_level', {}).get('value') if latest.get('tank_level', {}).get('value') is not None else 0:.0f}", "%", "Estimated volume")
    with col3:
        _metric_card("pH", f"{latest.get('ph', {}).get('value') if latest.get('ph', {}).get('value') is not None else 7.2:.2f}", "", "Configured range 6.5–8.5")
    with col4:
        _metric_card("Turbidity", f"{latest.get('turbidity', {}).get('value') if latest.get('turbidity', {}).get('value') is not None else 1.4:.2f}", " NTU", source_tag(latest.get('turbidity', {}).get('source')))

    history = request_json("GET", "/api/sensors/history?measurement_type=ph&limit=40")
    if history:
        df = pd.DataFrame(history)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["value"], mode="lines+markers", name="pH"))
        fig.update_layout(title="Live pH trend", xaxis_title="Timestamp", yaxis_title="pH")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No pH history yet. Generate simulator data or ingest sensor readings to populate the graph.")

    st.subheader("Alerts")
    if alerts:
        for alert in alerts[:5]:
            st.warning(f"{alert['alert_type']} [{alert['severity']}]: {alert['explanation']}")
    else:
        st.success("No active alerts.")


def render_live_sensors() -> None:
    latest = request_json("GET", "/api/sensors/latest")
    st.title("Live Sensors")
    for metric_name, label in {"flow": "Flow Rate", "ph": "pH", "turbidity": "Turbidity", "temperature": "Temperature", "tank_level": "Tank Level"}.items():
        value = latest.get(metric_name, {}).get("value")
        source = latest.get(metric_name, {}).get("source", "SIMULATED")
        quality = latest.get(metric_name, {}).get("quality_status", "UNKNOWN")
        st.metric(label, value if value is not None else "N/A", delta=f"Source: {source_tag(source)} • {quality}")


def render_water_quality() -> None:
    st.title("Water Quality")
    history = request_json("GET", "/api/sensors/history?measurement_type=ph&limit=40")
    if history:
        df = pd.DataFrame(history)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["value"], mode="lines+markers", name="pH"))
        fig.add_hline(y=6.5, line_dash="dash", line_color="red", annotation_text="Min reference")
        fig.add_hline(y=8.5, line_dash="dash", line_color="orange", annotation_text="Max reference")
        fig.update_layout(title="pH trend with configured thresholds", xaxis_title="Timestamp", yaxis_title="pH")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No pH history available yet.")

    turbidity = request_json("GET", "/api/sensors/history?measurement_type=turbidity&limit=40")
    if turbidity:
        df_t = pd.DataFrame(turbidity)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_t["timestamp"], y=df_t["value"], mode="lines+markers", name="Turbidity"))
        fig2.update_layout(title="Turbidity trend", xaxis_title="Timestamp", yaxis_title="NTU")
        st.plotly_chart(fig2, use_container_width=True)


def render_consumption() -> None:
    st.title("Consumption Analytics")
    data = request_json("GET", "/api/consumption/daily")
    if not data:
        st.info("No consumption history available yet.")
        return
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["consumption_l"], mode="lines+markers", name="Consumption"))
    fig.update_layout(title="Daily consumption", xaxis_title="Timestamp", yaxis_title="Litres")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df.tail(10), use_container_width=True)


def render_leak_detection() -> None:
    st.title("Leak Detection")
    alerts = request_json("GET", "/api/alerts")
    if alerts:
        leak_rows = [a for a in alerts if "leak" in a["alert_type"].lower() or "flow" in a["alert_type"].lower()]
        if leak_rows:
            st.table(leak_rows[:10])
        else:
            st.info("No leak or abnormal flow alerts detected yet.")
    else:
        st.info("No alerts available yet.")


def render_alerts() -> None:
    st.title("Alerts")
    alerts = request_json("GET", "/api/alerts")
    if not alerts:
        st.info("No alerts recorded yet.")
        return
    for alert in alerts:
        st.warning(f"[{alert['severity']}] {alert['alert_type']} — {alert['explanation']}")
        st.caption(f"Suggested action: {alert['suggested_action']}")


def render_reports() -> None:
    st.title("Reports")
    report_type = st.selectbox("Report type", ["sensor", "consumption", "alerts"])
    if st.button("Download CSV"):
        response = requests.get(f"{BACKEND_URL}/api/reports/csv?report_type={report_type}", headers=auth_headers(), timeout=20)
        if response.status_code >= 400:
            st.error(response.text)
        else:
            st.download_button("Download report", data=response.content, file_name=f"{report_type}-report.csv", mime="text/csv")


def render_settings() -> None:
    settings = request_json("GET", "/api/settings")
    st.title("Settings")
    st.json(settings)
    if st.button("Refresh settings"):
        st.rerun()


def render_admin() -> None:
    st.title("Admin / Demo Controls")
    settings = request_json("GET", "/api/settings")
    mode = st.selectbox("Simulator mode", ["Normal Mode", "Leak Mode", "High Usage Mode", "Poor Water Quality Mode", "Low Tank Mode", "Sensor Failure Mode"], index=0)
    if st.button("Persist mode"):
        payload = dict(settings)
        payload["simulator_mode"] = mode
        updated = request_json("PUT", "/api/settings", payload)
        st.session_state.settings = updated
        st.success(f"Simulator mode saved: {mode}")
    if st.button("Send sample sensor reading"):
        payload = {
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
        }
        try:
            response = requests.post(f"{BACKEND_URL}/api/sensors/data", json=payload, headers={"X-Device-Key": os.getenv("DEVICE_API_KEY", "demo-device-key")}, timeout=15)
            if response.status_code >= 400:
                st.error(response.text)
            else:
                st.success("Sample reading accepted.")
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
        st.session_state.user = request_json("GET", "/api/auth/me")
        st.session_state.settings = request_json("GET", "/api/settings")
        if not st.session_state.settings.get("onboarding_complete"):
            if st.sidebar.button("Logout"):
                st.session_state.clear(); st.rerun()
            if st.session_state.page == "setup2":
                onboarding_step2()
            else:
                onboarding_step1()
        else:
            nav = st.sidebar.radio("Navigation", ["Dashboard", "Live Sensors", "Water Quality", "Consumption Analytics", "Leak Detection", "Alerts", "Reports", "Settings", "Admin / Demo Controls"])
            if st.sidebar.button("Logout"):
                try:
                    requests.post(f"{BACKEND_URL}/api/auth/logout", headers=auth_headers(), timeout=15)
                except Exception:
                    pass
                st.session_state.clear(); st.rerun()
            if nav == "Dashboard":
                render_dashboard()
            elif nav == "Live Sensors":
                render_live_sensors()
            elif nav == "Water Quality":
                render_water_quality()
            elif nav == "Consumption Analytics":
                render_consumption()
            elif nav == "Leak Detection":
                render_leak_detection()
            elif nav == "Alerts":
                render_alerts()
            elif nav == "Reports":
                render_reports()
            elif nav == "Settings":
                render_settings()
            elif nav == "Admin / Demo Controls":
                render_admin()
    except Exception as exc:
        st.error(f"Session expired or backend unavailable: {exc}")
        if st.button("Login again"):
            st.session_state.clear(); st.rerun()
