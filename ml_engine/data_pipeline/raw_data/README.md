# 📦 Kaggle Dataset Directory: Global Supply Chain & Trade Disruptions (25 Years)

Place the downloaded CSV files from the Kaggle dataset **"Global Supply Chain & Trade Disruptions 25 years"** into this directory:

### Required Files:
1. **`shipping_rates.csv`**:
   - Monthly historical shipping indices (specifically `date` / `Date` and `baltic_dry_index` / `BDI`) covering 2000–2024.
   - Used by the long-term **Prophet / Additive Seasonal Trend** model to learn 25-year macroeconomic steel cycles.

2. **`disruption_events.csv`**:
   - Historical maritime and global trade disruption events (e.g. Suez Canal Blockage, Red Sea Crisis, COVID Supply Shocks, Major Port Congestions).
   - Used by `fetch_disruptions.py` and the **"What-If" Disruption Simulator** to apply historical shock multipliers to freight rates.

### Kaggle Download Link & Instructions:
- Search Kaggle for: `"Global Supply Chain & Trade Disruptions 25 years"`
- Download and extract:
  - `shipping_rates.csv` -> `ml_engine/data_pipeline/raw_data/shipping_rates.csv`
  - `disruption_events.csv` -> `ml_engine/data_pipeline/raw_data/disruption_events.csv`
- Run seeding or forecasting: `python ml_engine/data_pipeline/seed_database.py`
