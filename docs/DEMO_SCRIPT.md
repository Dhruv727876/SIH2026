# ⏱️ SIH26006: 3-Minute Winning Hackathon Pitch Script

> **Title**: Intelligent Freight Forecasting & Vessel Chartering Decision Support System (DSS)  
> **Problem Statement ID**: SIH26006  
> **Target Audience**: Jury panel representing Ministry of Steel, SAIL, RINL, NMDC, and Academic Evaluators.  
> **Presenter Setup**: Screen sharing [http://localhost:3000](http://localhost:3000) on full screen.

---

## 🎯 Pitch Timeline Overview
- **Minute 1 [0:00 – 1:00]**: The Real-World Crisis — Why Steel PSUs Lose Hundreds of Crores on Freight & Demurrage.
- **Minute 2 [1:00 – 2:00]**: The AI Solution — Hybrid 60-Day Freight Forecasting Engine (LightGBM + Prophet).
- **Minute 3 [2:00 – 3:00]**: The "Wow" Moment — MILP Constraint Solver, Port Draft Rejection, and Measurable ROI.

---

## 🎬 Minute 1: The Problem (0:00 – 1:00)

**[SCREEN ACTION: Point to Top Header & Context Strip on the Dashboard]**

> **Speaker**:  
> *"Respected Judges, India is the second-largest crude steel producer in the world. To sustain our blast furnaces, PSUs like SAIL, RINL, and NMDC import over 70 million tonnes of coking coal every year from Australia, South Africa, and Brazil.*  
> 
> *Yet, despite being a core strategic operation, ocean chartering is still largely managed through intuition, legacy spreadsheets, and reactive spot booking.*  
> 
> *This creates two massive financial bleeds:*
> 1. **Freight Market Volatility**: Baltic Capesize and Panamax indices swing by up to **40% in single-month cycles**, driven by bunker fuel spikes and fleet availability.
> 2. **Port Bottlenecks & Demurrage**: When vessels arrive during congestion or exceed channel draft limits, Indian PSUs pay demurrage penalties exceeding **$25,000 per vessel per day**!
> 
> *Our solution, **Freight DSS**, is the first unified, AI-driven Decision Support System built specifically to eliminate this guesswork and protect national procurement budgets."*

---

## 🔬 Minute 2: The AI Solution (1:00 – 2:00)

**[SCREEN ACTION: Scroll down to the Freight Forecast Chart. Switch index dropdown from BCI to BPI to BUNKER_SIN]**

> **Speaker**:  
> *"Here is our core Machine Learning engine in action.*  
> 
> *Rather than relying on naive single-model extrapolations, we engineered a **two-tier Hybrid Forecasting Architecture**:*
> 
> 1. **T+1 to T+15 (Short-Horizon Volatility)**: We deploy a **LightGBM gradient-boosted regression model** that ingests multi-day lag structures, 7-day rolling standard deviation, and macro fuel covariance between Brent Crude and Singapore Marine Bunker Fuel (VLSFO).
> 2. **T+16 to T+60 (Medium-Horizon Trend)**: We seamlessly blend into a **decomposed additive seasonal model (Prophet/Holt-Winters)** to capture structural macroeconomic cycles.
> 
> *Notice this shaded region on the chart: that is our **80% Statistical Confidence Envelope**. Procurement managers at SAIL do not just see a single point forecast; they see quantitative risk boundaries to make hedge and charter timing decisions with absolute statistical clarity."*

---

## ⚡ Minute 3: The "Wow" Moment & Optimization Impact (2:00 – 3:00)

**[SCREEN ACTION: In the Optimization Panel, select 'Haldia' as Target Port, set Volume to '150,000 MT', and click 'Run MILP Optimization Model']**

> **Speaker**:  
> *"Now, here is our core differentiator: **Forecasting alone does not book ships; Operations Research does.**  
> 
> Watch what happens when we schedule a 150,000 MT raw material shipment for **Haldia Port**:  
> 
> *Haldia has a shallow riverine draft limit of **12.0 meters**. A naive logistics manager might try booking a cheaper Capesize bulker requiring 17.0 meters.  
> 
> Our **Mixed-Integer Linear Programming (MILP) Solver**, powered by PuLP CBC, instantly recognizes the 12.0m threshold:*
> - It **automatically disqualifies Capesize and Panamax vessels**.
> - It parcels the cargo into **3 Supramax bulkers (50,000 MT each)**.
> - It strategically staggers their departure dates to capture the lowest forecast rate dip while respecting berth congestion limits.
> 
> **[POINT TO THE GREEN KPI CARD]**  
> *Look at the bottom line: The system delivers **100% demand satisfaction**, avoids catastrophic grounding and deadfreight penalties, and secures a net savings of **$416,000 (over ₹3.45 Crore)** compared to naive spot booking!*
> 
> *In summary, **Freight DSS** bridges AI prediction with mathematical execution — delivering resilience, transparency, and measurable savings to India's steel industry. Thank you!"*

---

## 🏆 Presentation Tips for the Team
1. **Pacing**: Speak at a steady, authoritative tempo. Do not rush through the numbers.
2. **Highlight Indian Context**: Mention SAIL Durgapur/Bhilai, RINL Visakhapatnam, and specific ports (Paradip, Vizag, Haldia, Dhamra).
3. **Keep the Servers Running**: Ensure FastAPI on `:8000` and Next.js on `:3000` are active in background tabs before walking up to the jury.
