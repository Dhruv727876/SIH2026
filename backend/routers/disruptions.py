import os
import sys
from typing import List, Dict, Any
from fastapi import APIRouter

# Ensure ml_engine is accessible in path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ml_engine_dir = os.path.join(root_dir, "ml_engine")
if ml_engine_dir not in sys.path:
    sys.path.insert(0, ml_engine_dir)

from data_pipeline.fetch_disruptions import list_all_disruptions, get_disruption_shock_multiplier

router = APIRouter(prefix="/api/v1/disruptions", tags=["Disruptions"])


@router.get(
    "",
    summary="List all historical maritime supply chain disruption events and shock multipliers",
)
def get_disruptions() -> List[Dict[str, Any]]:
    """
    Returns historical supply chain shocks from Kaggle dataset (e.g. Suez, Red Sea, COVID, Panama drought).
    """
    return list_all_disruptions()


@router.get(
    "/{event_type}/multiplier",
    summary="Get freight rate shock multiplier for a disruption type",
)
def get_multiplier(event_type: str) -> Dict[str, Any]:
    """
    Computes the historical BDI freight rate spike multiplier for the given disruption.
    """
    multiplier = get_disruption_shock_multiplier(event_type)
    return {
        "event_type": event_type,
        "freight_shock_multiplier": multiplier,
        "spike_percentage": round((multiplier - 1.0) * 100, 1),
    }
