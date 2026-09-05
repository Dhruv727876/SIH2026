import logging
import random
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("port-data-generator")

PORT_CONFIGS = [
    {"port_name": "Paradip", "max_draft_meters": 14.5, "base_waiting": 36.0},
    {"port_name": "Visakhapatnam", "max_draft_meters": 16.5, "base_waiting": 24.0},
    {"port_name": "Haldia", "max_draft_meters": 12.0, "base_waiting": 48.0},
    {"port_name": "Dhamra", "max_draft_meters": 18.0, "base_waiting": 18.0},
    {"port_name": "Gangavaram", "max_draft_meters": 20.0, "base_waiting": 16.0},
]


def generate_port_telemetry(include_anomalies: bool = True) -> List[Dict[str, Any]]:
    """
    Generates realistic port constraints, draft limits, and congestion waiting times
    for major Indian steel raw material import ports.
    """
    port_records: List[Dict[str, Any]] = []

    for port in PORT_CONFIGS:
        port_name = port["port_name"]
        max_draft = port["max_draft_meters"]
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
            "current_waiting_time_hours": round(float(waiting_time), 1),
        })

    return port_records


if __name__ == "__main__":
    ports = generate_port_telemetry()
    print("Generated Port Constraints & Telemetry:")
    for p in ports:
        print(f" - {p['port_name']}: Max Draft = {p['max_draft_meters']}m, Waiting Time = {p['current_waiting_time_hours']}h")
