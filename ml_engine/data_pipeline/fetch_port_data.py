import logging
import random
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("port-data-generator")

PORT_CONFIGS = [
    {
        "port_name": "Paradip",
        "max_draft_meters": 14.5,
        "max_loa_meters": 260.0,
        "max_beam_meters": 43.0,
        "cargo_handling_rate_tpd": 45000.0,
        "base_waiting": 36.0,
    },
    {
        "port_name": "Visakhapatnam",
        "max_draft_meters": 16.5,
        "max_loa_meters": 280.0,
        "max_beam_meters": 45.0,
        "cargo_handling_rate_tpd": 35000.0,
        "base_waiting": 24.0,
    },
    {
        "port_name": "Gangavaram",
        "max_draft_meters": 20.0,
        "max_loa_meters": 320.0,
        "max_beam_meters": 50.0,
        "cargo_handling_rate_tpd": 40000.0,
        "base_waiting": 16.0,
    },
    {
        "port_name": "Gopalpur",
        "max_draft_meters": 13.5,
        "max_loa_meters": 230.0,
        "max_beam_meters": 33.0,
        "cargo_handling_rate_tpd": 20000.0,
        "base_waiting": 30.0,
    },
    {
        "port_name": "Dhamra",
        "max_draft_meters": 18.0,
        "max_loa_meters": 315.0,
        "max_beam_meters": 48.0,
        "cargo_handling_rate_tpd": 45000.0,
        "base_waiting": 18.0,
    },
    {
        "port_name": "Sagar- Sandheads",
        "max_draft_meters": 18.5,
        "max_loa_meters": 330.0,
        "max_beam_meters": 55.0,
        "cargo_handling_rate_tpd": 25000.0,
        "base_waiting": 12.0,
    },
    {
        "port_name": "Haldia",
        "max_draft_meters": 12.0,
        "max_loa_meters": 220.0,
        "max_beam_meters": 32.3,
        "cargo_handling_rate_tpd": 15000.0,
        "base_waiting": 48.0,
    },
    # Preserved for backward compatibility
    {
        "port_name": "Mormugao",
        "max_draft_meters": 14.1,
        "max_loa_meters": 240.0,
        "max_beam_meters": 38.0,
        "cargo_handling_rate_tpd": 25000.0,
        "base_waiting": 28.0,
    },
    {
        "port_name": "Jaigad",
        "max_draft_meters": 18.5,
        "max_loa_meters": 310.0,
        "max_beam_meters": 48.0,
        "cargo_handling_rate_tpd": 35000.0,
        "base_waiting": 20.0,
    },
]


def generate_port_telemetry(include_anomalies: bool = True) -> List[Dict[str, Any]]:
    """
    Generates realistic port constraints, draft limits, LOA, Beam, cargo handling rates,
    and congestion waiting times for major Indian steel raw material import ports.
    """
    port_records: List[Dict[str, Any]] = []

    for port in PORT_CONFIGS:
        port_name = port["port_name"]
        max_draft = port["max_draft_meters"]
        max_loa = port["max_loa_meters"]
        max_beam = port["max_beam_meters"]
        handling_rate = port["cargo_handling_rate_tpd"]
        base_waiting = port["base_waiting"]

        # Standard congestion fluctuation (12 to 72 hours)
        waiting_time = base_waiting + random.uniform(-8.0, 16.0)
        waiting_time = max(12.0, min(72.0, waiting_time))

        # 20% chance of a severe weather / congestion anomaly spiking up to 120 hours
        if include_anomalies and random.random() < 0.20:
            anomaly_spike = random.uniform(75.0, 120.0)
            logger.info(
                f"Simulating congestion/weather alert at {port_name}: Waiting time spiked to {anomaly_spike:.1f} hrs."
            )
            waiting_time = anomaly_spike

        port_records.append({
            "port_name": port_name,
            "max_draft_meters": round(float(max_draft), 1),
            "max_loa_meters": round(float(max_loa), 1),
            "max_beam_meters": round(float(max_beam), 1),
            "cargo_handling_rate_tpd": round(float(handling_rate), 0),
            "current_waiting_time_hours": round(float(waiting_time), 1),
        })

    return port_records


if __name__ == "__main__":
    ports = generate_port_telemetry()
    print("Generated Port Constraints & Telemetry:")
    for p in ports:
        print(f" - {p['port_name']}: Max Draft = {p['max_draft_meters']}m, Waiting Time = {p['current_waiting_time_hours']}h")
