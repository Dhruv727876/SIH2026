import logging
import os
import urllib.parse
from typing import Any, Dict, List, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("disruptions-fetcher")

# Master verified historical and recent maritime disruption catalog
CURATED_DISRUPTIONS: List[Dict[str, Any]] = [
    {
        "event_id": 1,
        "event_type": "IRAN_US_STRAIT_HORMUZ",
        "event_name": "Iran-US Conflict & Strait of Hormuz Chokepoint Risk",
        "category": "Geopolitical & Conflict",
        "affected_region": "Middle East / Persian Gulf / Strait of Hormuz",
        "bdi_impact_pct": 28.0,
        "freight_shock_multiplier": 1.28,
        "date": "2024-04-14",
        "description": "Direct missile/drone strikes and naval seizures in the Strait of Hormuz trigger war-risk insurance premiums (+400%), bunker fuel price surges, and bulk vessel route diversions.",
    },
    {
        "event_id": 2,
        "event_type": "RUSSIA_UKRAINE_WAR",
        "event_name": "Russia-Ukraine War & Black Sea Bulk Blockade",
        "category": "Geopolitical & Conflict",
        "affected_region": "Black Sea / Europe / Global Coal Routes",
        "bdi_impact_pct": 24.0,
        "freight_shock_multiplier": 1.24,
        "date": "2022-02-24",
        "description": "Black Sea navigation closures and sanctions against Russian coal force Indian steel mills to source metallurgical coal from distant Australian and North American ports (+30% ton-miles).",
    },
    {
        "event_id": 3,
        "event_type": "RED_SEA_HOUTHI",
        "event_name": "Red Sea & Bab el-Mandeb Houthi Vessel Strikes",
        "category": "Geopolitical & Conflict",
        "affected_region": "Red Sea / Gulf of Aden / Bab el-Mandeb",
        "bdi_impact_pct": 22.0,
        "freight_shock_multiplier": 1.22,
        "date": "2023-12-18",
        "description": "Armed attacks on commercial shipping forcing bulkers around Africa's Cape of Good Hope, adding 12–16 voyage days and tightening global bulk vessel supply.",
    },
    {
        "event_id": 4,
        "event_type": "COVID_PANDEMIC",
        "event_name": "COVID-19 Global Port Quarantine & Labor Crisis",
        "category": "Pandemic & Health",
        "affected_region": "Global Major Hubs (China, India, Singapore)",
        "bdi_impact_pct": 35.0,
        "freight_shock_multiplier": 1.35,
        "date": "2020-03-11",
        "description": "14-day mandatory ship quarantines, severe dock labor shortages, and post-lockdown commodity restock cycles creating historic bulk freight rate peaks.",
    },
    {
        "event_id": 5,
        "event_type": "SUEZ_BLOCKAGE",
        "event_name": "Ever Given Suez Canal 6-Day Blockage",
        "category": "Maritime Chokepoint",
        "affected_region": "Suez Canal / Mediterranean / Global",
        "bdi_impact_pct": 20.0,
        "freight_shock_multiplier": 1.20,
        "date": "2021-03-23",
        "description": "Canal obstruction stranding 360+ bulkers and container vessels, causing acute cascading port queue delays and regional bulk charter rate spikes.",
    },
    {
        "event_id": 6,
        "event_type": "CYCLONE_MICHAUNG",
        "event_name": "Cyclone Michaung & Bay of Bengal Monsoon Swells",
        "category": "Climate & Natural",
        "affected_region": "Indian East Coast (Paradip, Vizag, Dhamra)",
        "bdi_impact_pct": 16.0,
        "freight_shock_multiplier": 1.16,
        "date": "2023-12-04",
        "description": "Torrential cyclonic storms and heavy swell surges halting berth discharge operations, spiking vessel anchorage waiting queues to 96+ hours and escalating demurrage penalties.",
    },
    {
        "event_id": 7,
        "event_type": "PANAMA_DROUGHT",
        "event_name": "Panama Canal El Niño Transit Drought Restrictions",
        "category": "Climate & Natural",
        "affected_region": "Panama / Transpacific Bulk Corridors",
        "bdi_impact_pct": 15.0,
        "freight_shock_multiplier": 1.15,
        "date": "2023-11-01",
        "description": "Severe Gatun Lake drought reducing daily vessel transit reservations from 36 to 22 ships, forcing dry bulk carriers onto long-haul diversion routes around South America.",
    },
    {
        "event_id": 8,
        "event_type": "HALDIA_SILTATION",
        "event_name": "Haldia Riverine Draft Siltation & Draft Drop",
        "category": "Port Constraint",
        "affected_region": "Hooghly River / Haldia Dock Complex",
        "bdi_impact_pct": 25.0,
        "freight_shock_multiplier": 1.25,
        "date": "2024-08-15",
        "description": "Monsoon siltation dropping allowable river draft below 11.5m, disqualifying standard Panamax ships and demanding costly transshipment/lighterage.",
    },
    {
        "event_id": 9,
        "event_type": "HURRICANE_KATRINA",
        "event_name": "Hurricane Katrina US Gulf Export Terminal Disruption",
        "category": "Climate & Natural",
        "affected_region": "US Gulf Coast / Mississippi River Terminals",
        "bdi_impact_pct": 18.0,
        "freight_shock_multiplier": 1.18,
        "date": "2005-08-29",
        "description": "Severe hurricane destroying Mississippi River grain and coal bulk loading elevators, paralyzing Atlantic basin shipments and spiking freight rates.",
    },
    {
        "event_id": 10,
        "event_type": "TOHOKU_EARTHQUAKE",
        "event_name": "Tohoku Earthquake & Tsunami Port Infrastructure Shock",
        "category": "Climate & Natural",
        "affected_region": "Japan / North Pacific Bulk Terminals",
        "bdi_impact_pct": 14.0,
        "freight_shock_multiplier": 1.14,
        "date": "2011-03-11",
        "description": "Catastrophic earthquake and tsunami damaging steel mill deepwater discharge ports, causing severe congestion and supply chain rerouting across the Pacific.",
    },
    {
        "event_id": 11,
        "event_type": "SARS_OUTBREAK",
        "event_name": "SARS Epidemic Far East Shipping Congestion",
        "category": "Pandemic & Health",
        "affected_region": "East Asia / Pacific Trade Corridor",
        "bdi_impact_pct": 8.0,
        "freight_shock_multiplier": 1.08,
        "date": "2003-04-01",
        "description": "Port health checks, reduced dock labor, and regional trade slowdown across major Pacific bulk loading terminals.",
    },
]

# Quick lookup map by normalized key
MULTIPLIER_MAP: Dict[str, float] = {
    d["event_type"]: d["freight_shock_multiplier"] for d in CURATED_DISRUPTIONS
}


def load_disruption_events(
    csv_path: str = "ml_engine/data_pipeline/raw_data/disruption_events.csv",
) -> List[Dict[str, Any]]:
    """
    Returns structured disruption shock events, prioritizing curated real-world & recent events
    while merging any additional events from the Kaggle dataset.
    """
    # Start with our curated list
    results = list(CURATED_DISRUPTIONS)
    existing_types = {d["event_type"].upper() for d in results}

    if not os.path.exists(csv_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(base_dir, "raw_data", "disruption_events.csv")
        if os.path.exists(alt_path):
            csv_path = alt_path

    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for idx, row in df.iterrows():
                # Derive event_type
                raw_type = str(row.get("event_type", "") or row.get("disruption_type", "")).strip()
                raw_name = str(row.get("event_name", "")).strip()
                
                derived_key = raw_name.upper().replace(" ", "_").replace("-", "_").replace("—", "_")
                if not raw_name:
                    continue

                # Skip if already represented in curated set
                if any(k in derived_key for k in ["IRAN", "UKRAINE", "RUSSIA", "RED_SEA", "COVID", "SUEZ", "MICHAUNG", "PANAMA", "KATRINA", "TOHOKU"]):
                    continue

                # Calculate multiplier
                freight_pct = row.get("freight_rate_shock_pct") or row.get("bdi_shock_pct") or 10.0
                try:
                    freight_pct_val = abs(float(freight_pct))
                    if freight_pct_val == 0:
                        freight_pct_val = 10.0
                except (ValueError, TypeError):
                    freight_pct_val = 10.0

                multiplier = round(1.0 + (freight_pct_val / 100.0), 2)
                event_code = f"HIST_{idx+12}"

                results.append({
                    "event_id": len(results) + 1,
                    "event_type": event_code,
                    "event_name": raw_name,
                    "category": str(row.get("disruption_type", "Geopolitical")).capitalize(),
                    "affected_region": str(row.get("region_affected", "Global")),
                    "bdi_impact_pct": freight_pct_val,
                    "freight_shock_multiplier": multiplier,
                    "date": str(row.get("date", "2020-01-01")),
                    "description": f"Historical {raw_name} event affecting {row.get('region_affected', 'Global')} with an estimated {freight_pct_val}% freight rate spike.",
                })
        except Exception as e:
            logger.error(f"Error merging Kaggle disruption CSV: {e}")

    return results


def get_disruption_shock_multiplier(event_key: str) -> float:
    """
    Returns the distinct freight rate shock multiplier (e.g. 1.28 for +28% spike)
    for a given disruption event identifier, name, or keyword.
    """
    if not event_key:
        return 1.0

    # Clean and decode URL-encoded keys
    decoded_key = urllib.parse.unquote(event_key).strip().upper().replace(" ", "_").replace("-", "_")

    # 1. Exact match in curated dictionary
    if decoded_key in MULTIPLIER_MAP:
        return MULTIPLIER_MAP[decoded_key]

    # 2. Search curated records by substring in event_type or event_name
    for item in CURATED_DISRUPTIONS:
        t = item["event_type"].upper()
        n = item["event_name"].upper().replace(" ", "_").replace("-", "_")
        if decoded_key in t or t in decoded_key or decoded_key in n:
            return float(item["freight_shock_multiplier"])

    # 3. Keyword heuristics for recent and major shocks
    if "IRAN" in decoded_key or "HORMUZ" in decoded_key:
        return 1.28
    elif "UKRAINE" in decoded_key or "RUSSIA" in decoded_key:
        return 1.24
    elif "RED_SEA" in decoded_key or "HOUTHI" in decoded_key:
        return 1.22
    elif "SUEZ" in decoded_key:
        return 1.20
    elif "COVID" in decoded_key or "PANDEMIC" in decoded_key or "QUARANTINE" in decoded_key:
        return 1.35
    elif "MICHAUNG" in decoded_key or "MONSOON" in decoded_key or "CYCLONE" in decoded_key:
        return 1.16
    elif "PANAMA" in decoded_key or "DROUGHT" in decoded_key:
        return 1.15
    elif "HALDIA" in decoded_key or "SILT" in decoded_key:
        return 1.25
    elif "KATRINA" in decoded_key or "HURRICANE" in decoded_key:
        return 1.18
    elif "TOHOKU" in decoded_key or "TSUNAMI" in decoded_key or "EARTHQUAKE" in decoded_key:
        return 1.14
    elif "SARS" in decoded_key:
        return 1.08

    # 4. Search in full merged list
    all_events = load_disruption_events()
    for ev in all_events:
        t = str(ev.get("event_type", "")).upper()
        n = str(ev.get("event_name", "")).upper()
        if decoded_key in t or decoded_key in n:
            return float(ev.get("freight_shock_multiplier", 1.12))

    return 1.12  # Moderate default shock if unrecognized


def list_all_disruptions() -> List[Dict[str, Any]]:
    """
    Returns the comprehensive structured list of all disruption scenarios.
    """
    return load_disruption_events()


if __name__ == "__main__":
    for ev in ["IRAN_US_STRAIT_HORMUZ", "RUSSIA_UKRAINE_WAR", "RED_SEA_HOUTHI", "COVID_PANDEMIC", "CYCLONE_MICHAUNG", "PANAMA_DROUGHT"]:
        print(f"Event: {ev} -> Multiplier: {get_disruption_shock_multiplier(ev)}")
