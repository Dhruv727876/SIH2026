# 🏛️ SIH26006: System Architecture & Data Flow Specification

> **Project**: Intelligent Freight Forecasting Model for Optimized Vessel Chartering  
> **Target Entity**: Ministry of Steel (Government of India) & Steel PSUs (SAIL, RINL, NMDC)  
> **Version**: 1.0.0 Enterprise Production Specification

---

## 1. End-to-End System Architecture Overview

The system is architected as a high-performance, modular Decision Support System (DSS) comprising five decoupled layers:

```text
[ Data Ingestion Layer ] ──► [ TimescaleDB Storage ] ──► [ FastAPI Core API ] ──► [ Next.js 14 UI ]
                                                              │       ▲
                                                              ▼       │
                                                    [ ML Forecasting Engine ]
                                                              │
                                                              ▼
                                                    [ PuLP MILP Solver ]
```

---

## 2. Layer-by-Layer Architectural Decomposition

### Layer 1: Data Ingestion Pipeline (`ml_engine/data_pipeline/`)
- **Public & Macro Feeds**:
  - `yfinance` module pulls historical daily closes for global benchmarks (Brent Crude Oil `BZ=F`, USD/INR currency exchange `INR=X`, and Baltic proxy equities).
  - Multi-variate geometric random walk and volatility-drift generator synthesizes official Baltic Exchange indices:
    - **BCI** (Baltic Capesize Index - 150,000+ DWT, iron ore & coking coal)
    - **BPI** (Baltic Panamax Index - 70,000–90,000 DWT, coking coal)
    - **BSI** (Baltic Supramax Index - 50,000–65,000 DWT, geared shallow bulkers)
    - **BUNKER_SIN** (Singapore Very Low Sulfur Fuel Oil - $/MT)
- **Indian Port Telemetry Generator**:
  - Simulates dynamic draft allowances, tidal restrictions, berth counts, and congestion delays across major steel discharge hubs:
    - **Paradip** (14.5m Max Draft, 36h avg queue)
    - **Visakhapatnam** (16.5m Max Draft, 28h avg queue)
    - **Haldia** (12.0m Max Draft riverine channel, 44h avg queue)
    - **Dhamra** (18.0m Deepwater berth, 18h avg queue)
    - **Gangavaram** (20.0m Ultra-deepwater, 12h avg queue)

---

### Layer 2: Persistence & Time-Series Storage (`backend/models/`)
Built on **PostgreSQL 15** with the **TimescaleDB** extension for efficient indexing and continuous aggregates of time-series maritime telemetry.

#### Schema 1: `market_data`
- `id` (Integer, Primary Key)
- `index_name` (String: BCI, BPI, BSI, BRENT_CRUDE, USD_INR, BUNKER_SIN)
- `value` (Float: Rate in points, USD/bbl, USD/MT, or INR)
- `recorded_at` (Date, Indexed: Date of trade close)
- `created_at` (DateTime: System audit timestamp)

#### Schema 2: `port_data`
- `id` (Integer, Primary Key)
- `port_name` (String: Paradip, Visakhapatnam, Haldia, Dhamra, Gangavaram)
- `max_draft_m` (Float: Channel depth in meters)
- `current_waiting_hours` (Float: Average berth waiting delay)
- `berth_capacity` (Integer: Simultaneous bulk discharge berths)
- `recorded_at` (Date)

#### Schema 3: `optimization_logs`
- `id` (Integer, Primary Key)
- `target_port` (String)
- `required_cargo_mt` (Float)
- `planning_horizon_days` (Integer)
- `total_cost_usd` (Float)
- `savings_usd` (Float)
- `vessel_schedule_json` (JSONB)
- `executed_at` (DateTime)

---

### Layer 3: FastAPI Backend Services (`backend/routers/`)
Implements an asynchronous, high-throughput RESTful service layer:
- **`health.py`**: Validates database connection pools and solver readiness.
- **`market_data.py`**: Provides fast time-series queries and bulk ingestion endpoints.
- **`port_data.py`**: Manages dynamic port draft thresholds and congestion telemetry.
- **`forecasts.py`**: Invokes the ML forecasting engine and returns 60-day point estimates and 80% confidence interval bands.
- **`optimization.py`**: Validates procurement constraints, builds the MILP objective matrix, calls the PuLP solver, and computes landed cost savings against spot benchmarks.

---

### Layer 4: Hybrid Machine Learning Engine (`ml_engine/forecasting/`)
A dual-tier predictive framework designed to avoid the pitfalls of naive single-model time-series forecasting:

1. **Short-Horizon Model (Days 1–15)**:
   - **Algorithm**: LightGBM Gradient-Boosted Decision Trees.
   - **Engineered Features**: 1-day, 2-day, 3-day, 7-day, 14-day lagged values; 7-day rolling mean; 7-day rolling standard deviation (volatility proxy); and macro Brent Crude / Bunker fuel covariance.
   - **Target**: Short-term non-linear rate swings and immediate momentum.
2. **Medium-Horizon Model (Days 16–60)**:
   - **Algorithm**: Decomposed Additive Seasonal Model (Prophet / Holt-Winters Exponential Trend).
   - **Confidence Envelope**: Evaluates residual variance to compute **80% Statistical Confidence Intervals** ($[\hat{y}_t - 1.28\sigma_t, \hat{y}_t + 1.28\sigma_t]$).
3. **Transition Smoother**: Employs a linear sigmoid blending bridge between Day 14 and Day 17 to ensure continuous, non-divergent trajectory handover.

---

### Layer 5: MILP Operations Research Optimizer (`ml_engine/optimization/`)
Formulates vessel chartering as a **Mixed-Integer Linear Program (MILP)** solved via the **PuLP CBC Branch-and-Cut** engine.

#### Mathematical Model:

**Sets & Indices**:
- $V = \{\text{Capesize (150k MT)}, \text{Panamax (80k MT)}, \text{Supramax (50k MT)}\}$
- $T = \{1, 2, \dots, H\}$ (Planning horizon days, $H \le 60$)
- $P$ = Target Indian discharge port

**Decision Variables**:
- $x_{v, t} \in \mathbb{Z}_{\ge 0}$: Number of vessels of class $v$ chartered on departure day $t$.

**Objective Function**: Minimize Total Landed Procurement Cost:
$$\min \sum_{t \in T} \sum_{v \in V} \left[ \left( \hat{R}_{v, t} \cdot \text{Cap}_v \right) + C_{\text{mob}, v} + \left( W_P \cdot D_v \right) \right] \cdot x_{v, t}$$

Where:
- $\hat{R}_{v, t}$: Forecasted freight rate $(\$/\text{MT})$ for vessel $v$ on day $t$.
- $\text{Cap}_v$: Vessel nominal capacity in Metric Tonnes.
- $C_{\text{mob}, v}$: Fixed mobilization and port tariff overhead.
- $W_P$: Expected port waiting delay (hours).
- $D_v$: Hourly demurrage penalty rate for vessel class $v$.

**Constraints**:
1. **Demand Satisfaction**:
   $$\sum_{t \in T} \sum_{v \in V} \left( \text{Cap}_v \cdot x_{v, t} \right) \ge \text{Demand}_{\text{required}}$$
2. **Port Draft Restriction**:
   $$x_{v, t} = 0 \quad \forall v \text{ where } \text{Draft}_v > \text{MaxDraft}_P$$
   *(e.g., if $\text{MaxDraft}_{\text{Haldia}} = 12.0\text{m}$, Capesize ($17.0\text{m}$) and Panamax ($14.0\text{m}$) are strictly forced to 0).*
3. **Berth Handling Throughput**:
   $$\sum_{v \in V} x_{v, t} \le \text{MaxDailyArrivals}_P \quad \forall t \in T$$

---

### Layer 6: Enterprise Command Center UI (`frontend/`)
- **Next.js 14 App Router** with TypeScript and Server-Side Rendering (SSR).
- **Styling**: Tailwind CSS configured with a neutral dark graphite palette (`#090a0f`, `#12131a`, `#222430`) compliant with National Command Center and Bloomberg Terminal standards.
- **Data Visualization**: Recharts ComposedChart rendering forward curves, confidence bands, and dual-currency (USD & ₹ Crore) KPI cards.
- **Hydration Safe**: Deterministic formatting with pinned `en-US` and `en-IN` number formatting.

---

## 3. Data Flow Diagram

```text
[ Market Feeds / Port Telemetry ]
               │
               ▼ (fetch_market_data.py / seed_database.py)
[ PostgreSQL + TimescaleDB ]
               │
               ▼ (SQLAlchemy Async Queries)
[ FastAPI Backend /api/v1/ ]
       │                      │
       ▼ (/forecasts/{index}) ▼ (/optimize)
[ Hybrid ML Forecaster ]   [ PuLP CBC MILP Solver ]
       │                      │
       └──────────┬───────────┘
                  ▼
[ Next.js 14 Interactive Dashboard ]
```
