# 👨‍⚖️ Grand Finale Judges' Guide: Freight DSS (SIH26006)

Welcome, esteemed evaluators and domain experts from the **Ministry of Steel** and **Smart India Hackathon 2024**!

This guide points you directly to the key evaluation artifacts and architectural defenses of our platform.

---

## 📑 Core Documentation Index

1. **[Complete Evaluation Q&A & Technical Defenses](./docs/JUDGE_QA.md)**  
   * Detailed breakdown on why Mixed-Integer Linear Programming (MILP) outperforms heuristic RL.
   * Rationale for the two-tier LightGBM (15-day) + Prophet (180-day) hybrid forecasting.
   * Integration specifications with PSU ERP systems (SAP S/4HANA & MSTC e-Procurement).
   * Lighterage economics at Sandheads STS transshipment for Haldia Dock Complex.

2. **[Live Demonstration Script & Walkthrough](./docs/DEMO_SCRIPT.md)**  
   * 10-minute presentation guide with exact inputs, timestamp benchmarks, and UI focus areas.

3. **[System Architecture & Data Pipelines](./docs/architecture.md)**  
   * End-to-end data ingestion pipelines from Kaggle 25-Year historicals and live Yahoo Finance feeds into TimescaleDB and FastAPI.

4. **[Production Cloud Deployment Guide](./DEPLOYMENT.md)**  
   * Verification of live deployment environments on Vercel and Render.

---

## ⚡ Quick Evaluation Cheat Sheet

| Feature to Test | Where to Test | Key Expected Metric / Visual Indicator |
| :--- | :--- | :--- |
| **Mid-Sea Lighterage Engine** | Optimizer View: Haldia, 150k MT | Amber warning badge + $3.50/MT daughter vessel STS charge |
| **Spot vs. COA Strategic Hedging** | Optimizer View: Paradip, 300k MT | Contango curve detection + Bloomberg-style COA lock-in card |
| **Geopolitical Stress Testing** | Disruption View: Red Sea Crisis | Instant landed cost recalculation with +1.35x rate multiplier |
| **Mathematical Optimality** | PuLP CBC Solver | Zero draft violations, strict demand fulfillment, sub-second execution |
