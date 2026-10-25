# AquaGuard 360

AquaGuard 360 is a smart water monitoring, quality detection, and conservation management application built with Streamlit, FastAPI, SQLAlchemy, and Plotly.

## Features

- Secure registration and login
- Two-step onboarding wizard
- Dashboard with live sensor summaries
- Hybrid data source labeling
- pH, turbidity, flow, tank-level and leak analytics
- Alerts and notifications
- CSV export reports
- Simulator modes for demo and testing

## Quick start

1. Create a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and update values.
4. Start the backend:
   `uvicorn aquaguard360.backend.main:app --host 0.0.0.0 --port 8000`
5. Start the Streamlit frontend:
   `streamlit run aquaguard360/frontend/app.py --server.port 8501`
6. Start the simulator:
   `python aquaguard360/simulator/simulator.py --mode normal`

## Demo credentials

Use the register flow in the UI to create a demo account.

## Security note

The app stores password hashes and never stores plain-text secrets in frontend code.
