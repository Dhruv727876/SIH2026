# SIH2026 Freight DSS — Production Cloud Deployment Guide

This guide provides step-by-step instructions for deploying the **Decision Support System for Intelligent Freight Forecasting and Optimized Vessel Chartering** to production using:
- **Neon DB** (Serverless PostgreSQL Database)
- **Render** (FastAPI Backend Web Service)
- **Vercel** (Next.js 14 Frontend Application)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Vercel (Frontend)                         │
│   Next.js 14 (App Router) + Tailwind CSS + Lucide Icons     │
│   Environment: NEXT_PUBLIC_API_URL                          │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / JSON REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Render (Backend)                          │
│   FastAPI + Uvicorn + PuLP MILP + LightGBM / Prophet        │
│   Environment: DATABASE_URL, ALLOWED_ORIGINS, PORT          │
└──────────────────────────────┬──────────────────────────────┘
                               │ SSL Encrypted TCP (Port 5432)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Neon DB (Database)                          │
│   Serverless PostgreSQL with SSL (sslmode=require)          │
│   Tables auto-initialized by SQLAlchemy lifespan            │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Database Setup on Neon DB

1. Sign in to [Neon Console](https://console.neon.tech/) (or Supabase).
2. Create a new project:
   - **Project name**: `freight-dss`
   - **Database name**: `neondb` (or `freight_dss`)
   - **Region**: Choose the region closest to your Render service (e.g., `us-east-1` or `eu-central-1`).
3. Under **Connection Details**, select **PostgreSQL** and copy the connection string.
4. Ensure your connection string includes `sslmode=require`. Example:
   ```text
   postgresql://username:password@ep-cool-cloud-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   > **Note**: If your provider gives you a URL starting with `postgres://`, our backend's `database.py` automatically normalizes it to `postgresql://` for SQLAlchemy compatibility.

---

## Step 2: Backend Deployment on Render

1. Sign in to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository containing the SIH2026 code.
4. Configure the service settings:
   - **Name**: `freight-dss-backend` (or your chosen name)
   - **Region**: Same region as your Neon database (e.g., Ohio / Oregon / Frankfurt)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (root) OR enter `backend` depending on how you configure:
     - **Option A (Recommended - Root context)**:
       - **Root Directory**: `.` (leave empty)
       - **Build Command**: `pip install -r backend/requirements.txt`
       - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Option B (Procfile context)**:
       - **Root Directory**: `backend`
       - **Build Command**: `pip install -r requirements.txt`
       - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT` *(Render will automatically detect `backend/Procfile`)*
   - **Instance Type**: Free or Starter
5. Under **Environment Variables**, add the following:

| Variable Name | Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://<user>:<password>@<neon-host>/<db>?sslmode=require` | Neon / PostgreSQL connection string |
| `ALLOWED_ORIGINS` | `https://<your-vercel-app>.vercel.app,http://localhost:3000` | Comma-separated list of allowed frontend domains for CORS |
| `PYTHON_VERSION` | `3.11.8` | Recommended Python runtime version |

6. Click **Create Web Service**.
7. Once deployed, note down your Render service URL (e.g., `https://freight-dss-backend.onrender.com`).

---

## Step 3: Frontend Deployment on Vercel

1. Sign in to [Vercel](https://vercel.com/).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. Configure the project:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click `Edit` and select `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)
5. Under **Environment Variables**, add:

| Variable Name | Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://<your-backend-app>.onrender.com/api/v1` | URL of your deployed Render backend |

6. Click **Deploy**.
7. Once deployment finishes, copy your Vercel production URL (e.g., `https://freight-dss.vercel.app`).
8. **Important**: Go back to Render → your backend service → **Environment** and update `ALLOWED_ORIGINS` to include this Vercel production domain!

---

## Environment Variables Reference Summary

### For Render (Backend):
```ini
# Required
DATABASE_URL=postgresql://<user>:<pass>@<host>/<dbname>?sslmode=require
ALLOWED_ORIGINS=https://freight-dss.vercel.app,http://localhost:3000

# Automatically provided by Render
PORT=10000

# Optional runtime specification
PYTHON_VERSION=3.11.8
```

### For Vercel (Frontend):
```ini
# Required (points to Render backend)
NEXT_PUBLIC_API_URL=https://freight-dss-backend.onrender.com/api/v1
```

---

## Local Development Setup

To run the application locally with development fallbacks:

### Backend:
```bash
cd backend

# Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend (falls back to local SQLite if PostgreSQL is not running)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

### Frontend:
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
- UI: `http://localhost:3000`

---

## Troubleshooting & Verification Checklist

- [ ] **Health Endpoint**: Test `https://<backend-url>/api/v1/health`. Should return `{"status": "healthy"}`.
- [ ] **OpenAPI Docs**: Visit `https://<backend-url>/docs` to view and test interactive endpoints.
- [ ] **CORS Errors in Browser Console**: If the frontend shows `Access to fetch at ... has been blocked by CORS policy`, verify `ALLOWED_ORIGINS` on Render contains your Vercel domain without trailing slash (e.g. `https://my-app.vercel.app`).
- [ ] **Render Free Tier Cold Starts**: Render free instances spin down after 15 minutes of inactivity and take 30–50 seconds to boot on the first incoming request.
- [ ] **Neon Connection Timeout**: `database.py` is configured with `pool_pre_ping=True` and `pool_recycle=300` to automatically recover and refresh idle serverless connections.
- [ ] **SQLite Zero-Downtime Fallback**: If PostgreSQL credentials are misconfigured or the database is starting up, the backend logs a warning and gracefully serves requests using local SQLite storage without crashing.
