# SIH26006: Intelligent Freight Forecasting Model for Optimized Vessel Chartering

[![Smart India Hackathon 2026](https://img.shields.io/badge/SIH-2026-orange.svg)](https://www.sih.gov.in/)
[![Ministry of Steel](https://img.shields.io/badge/Ministry-Ministry%20of%20Steel-blue.svg)](https://steel.gov.in/)
[![Tech Stack](https://img.shields.io/badge/Stack-Next.js14%20|%20FastAPI%20|%20TimescaleDB%20|%20PuLP%20MILP-emerald.svg)]()

> **Decision Support System (DSS)** designed for the **Ministry of Steel, Government of India**, and Central Public Sector Undertakings (**SAIL, RINL, NMDC**) to forecast dry bulk shipping freight rates and mathematically optimize vessel chartering schedules under Indian port draft and berth demurrage constraints.

---

## 📌 Problem Statement (ID: SIH26006)
India's steel manufacturers import over **70+ Million Tonnes (MT)** of coking coal and raw materials annually via maritime bulk corridors (Australia, South Africa, Brazil, Indonesia to Indian Eastern Ports like Paradip, Visakhapatnam, Haldia, Dhamra, and Gangavaram). 

### Key Industry Bottlenecks:
1. **Extreme Freight Volatility**: Baltic Dry Indices (BCI, BPI, BSI) can swing by 30–50% within a month due to bunker fuel spikes, geopolitical tensions, and vessel availability.
2. **Heavy Port Demurrage Penalties**: Severe congestion and waiting periods (24–72 hours) cost PSUs up to **$20,000–$35,000/day** per stranded vessel in demurrage.
3. **Physical Channel Draft Restrictions**: Port draft limits (e.g., Haldia's shallow 12.0m riverine draft) strictly disqualify deep-draft Capesize bulkers. Suboptimal charter allocations lead to deadfreight penalties and multimillion-dollar inefficiencies.
4. **Manual & Fragmented Charter Planning**: Procurement teams lack a unified, mathematical decision engine that bridges forward market forecasting with operational port constraints.

---

## 💡 Solution Overview
**Freight DSS** combines **hybrid machine learning** with **Mixed-Integer Linear Programming (MILP)** to transform bulk shipping procurement:

1. **Multi-Source Market Ingestion**: Ingests real-world 25-year Kaggle datasets, live market indices (BCI, BPI, BSI), Brent Crude Oil, Singapore Marine Bunker Fuel (VLSFO), and USD/INR exchange rates into a time-series database.
2. **Hybrid ML Forecasting Engine**:
   - **Days 1–15 (Short-Horizon)**: Multi-lag LightGBM volatility model trained on rolling mean, rolling standard deviation, and macro fuel covariance.
   - **Days 16–60 (Medium-Horizon)**: Decomposed additive seasonal model (Prophet / Holt) trained on **25 years of real Kaggle Baltic Dry Index trends** with 80% statistical confidence intervals.
   - **Disruption Shock Multipliers**: Integrates historical disruption events (Suez, Red Sea, COVID, Panama drought) to stress-test rate projections.
3. **Operations Research MILP Solver (PuLP CBC)**:
   - Formulates a rigorous cost-minimization objective function combining voyage freight, vessel fixed mobilization, fuel surcharges, and port demurrage costs.
   - Enforces physical constraints: Port maximum allowable draft, daily berth handling capacities, demand satisfaction, and discrete integer vessel parcel counts.
4. **Interactive Command Center**: Next.js 14 enterprise dashboard featuring forward forecast envelopes, "What-If" disruption stress testing, and vessel dispatch scheduling.

---

## 📦 Kaggle Dataset Integration ("Global Supply Chain & Trade Disruptions 25 Years")

To utilize real 25-year historical shipping data and historical disruption shocks:

1. Search Kaggle for the dataset: **`Global Supply Chain & Trade Disruptions 25 years`**.
2. Download and place the following two CSV files into `ml_engine/data_pipeline/raw_data/`:
   - `shipping_rates.csv` (Contains 2000–2024 monthly `baltic_dry_index` data)
   - `disruption_events.csv` (Contains historical shocks: Suez Canal, Red Sea, COVID, Panama drought)
3. Run the database seeding pipeline:
   ```bash
   python ml_engine/data_pipeline/seed_database.py
   ```
> *Note: Built-in starter samples and graceful synthetic generators are included out of the box so the pipeline executes seamlessly even before downloading the full archive.*

---

## 🏗️ System Architecture

```text
+--------------------------------------------------------------------------------------------------+
|                                    EXTERNAL DATA SOURCES                                         |
|    Kaggle 25-Yr BDI & Disruption CSVs  |  Baltic Indices (BCI, BPI, BSI)  |  Brent Crude & VLSFO |
|    Port Telemetry (Paradip, Vizag, Haldia, Dhamra, Gangavaram Draft & Waiting Times)             |
+--------------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+--------------------------------------------------------------------------------------------------+
|                              DATA INGESTION & STORAGE LAYER                                      |
|    Python Ingestion Pipeline (`ml_engine/data_pipeline`)                                         |
|    PostgreSQL 15 + TimescaleDB Hypertables / Resilient SQLite Engine                             |
+--------------------------------------------------------------------------------------------------+
                                               │
                                               ▼
+--------------------------------------------------------------------------------------------------+
|                               FASTAPI ASYNCHRONOUS BACKEND                                       |
|    Port: 8000  |  SQLAlchemy 2.0 ORM  |  Pydantic V2 Schemas                                     |
|    Endpoints: /api/v1/market-data  |  /api/v1/forecasts/{index}  |  /api/v1/optimize  |  /disruptions
+--------------------------------------------------------------------------------------------------+
                    │                                                      │
                    ▼                                                      ▼
+---------------------------------------+             +--------------------------------------------+
|        HYBRID ML FORECASTER           |             |            MILP OPTIMIZER                  |
|  - LightGBM (T+1 to T+15 Volatility)  |             |  - PuLP CBC Branch-and-Cut Solver          |
|  - Prophet (T+16 to T+60 25-Yr Trend) |  ─────────► |  - Draft Threshold Exclusion Logic         |
|  - Historical Disruption Multipliers  |             |  - Total Landed Cost Minimization          |
+---------------------------------------+             +--------------------------------------------+
                                                                   │
                                                                   ▼
+--------------------------------------------------------------------------------------------------+
|                                NEXT.JS 14 ENTERPRISE DASHBOARD                                   |
|    Port: 3000  |  TypeScript  |  Tailwind CSS  |  Recharts Visualization                         |
|    - 60-Day Forward Rate Curve & Volatility Envelope                                             |
|    - "What-If" Maritime Disruption Stress Testing (Monsoon, Siltation, Mega-Imports)             |
|    - Optimal Charter Dispatch Table & Landed Cost Breakdown (USD $ and ₹ Crore)                  |
+--------------------------------------------------------------------------------------------------+
```

---

## 🛠️ Technology Stack

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, Lucide Icons | Data-dense, responsive command center dashboard |
| **API Backend** | FastAPI (Python 3.11), Uvicorn, SQLAlchemy 2.0, Pydantic V2 | High-throughput asynchronous REST API & validation |
| **ML & Analytics** | LightGBM, Prophet, Statsmodels, Pandas, NumPy, Scikit-Learn | Short- and medium-horizon freight rate forecasting |
| **Optimization** | PuLP (CBC Solver - Mixed-Integer Linear Programming) | Constrained cost-minimization & vessel fleet scheduling |
| **Database** | PostgreSQL 15 + TimescaleDB / Resilient SQLite Engine | Time-series hypertable market indices & port telemetry |
| **DevOps / Infra** | Docker, Docker Compose | Containerized local & cloud deployments |

---

## 🚀 Quickstart & Setup Instructions

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) (Optional, auto-falls back to local SQLite if Docker is stopped)
- [Python 3.11+](https://www.python.org/)
- [Node.js 18+ & npm](https://nodejs.org/)

---

### Step 1: Start Database (PostgreSQL + TimescaleDB)
```bash
# From project root directory (Optional)
docker-compose up -d
```

---

### Step 2: Set Up & Seed Backend & ML Engine
```bash
# 1. Create and activate Python virtual environment
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Seed historical market data and Kaggle 25-year BDI dataset
python ml_engine/data_pipeline/seed_database.py

# 4. Start the FastAPI server
python -m uvicorn backend.main:app --reload --port 8000
```
*API Documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).*

---

### Step 3: Set Up & Start Next.js Frontend
```bash
# In a new terminal window:
cd frontend
npm install
npm run dev
```
*Access the Web Command Center at [http://localhost:3000](http://localhost:3000).*

---

## 📡 Core API Reference

| Method | Endpoint | Description | Request / Query Sample |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | System health check & DB status | - |
| `GET` | `/api/v1/market-data` | Retrieve historical time-series indices | `?index_name=BDI_KAGGLE&limit=180` |
| `POST` | `/api/v1/market-data` | Ingest market data record | `{"index_name": "BCI", "value": 2450.0, "recorded_at": "2026-08-27"}` |
| `GET` | `/api/v1/port-data` | Retrieve Indian port draft & congestion telemetry | `?port_name=Paradip` |
| `GET` | `/api/v1/forecasts/{index}` | Generate 60-day ML forecast with 80% CI | `GET /api/v1/forecasts/BCI` |
| `GET` | `/api/v1/disruptions` | List historical maritime disruption shocks | - |
| `GET` | `/api/v1/disruptions/{type}/multiplier` | Compute BDI spike multiplier for an event | `GET /api/v1/disruptions/SUEZ/multiplier` |
| `POST` | `/api/v1/optimize` | Run MILP vessel chartering cost optimization | `{"required_cargo_mt": 300000, "target_port": "Paradip", "planning_horizon_days": 30}` |
