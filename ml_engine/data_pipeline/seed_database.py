import argparse
import logging
import sys
import time
from typing import List, Dict, Any
import requests

from fetch_market_data import fetch_real_market_data, generate_all_synthetic_market_data
from fetch_port_data import generate_port_telemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("seed-database")


def check_backend_health(base_url: str) -> bool:
    """Verifies that the FastAPI backend service is reachable."""
    health_url = f"{base_url.rstrip('/')}/api/v1/health"
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            logger.info(f"Backend health check passed at {health_url}: {response.json()}")
            return True
        else:
            logger.warning(f"Backend health check returned status code {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Cannot reach backend at {health_url}. Error: {e}")
        return False


def seed_market_data(base_url: str, days: int = 180, delay: float = 0.02) -> int:
    """Fetches real/synthetic market data and POSTs to backend."""
    logger.info(f"--- Fetching Market Telemetry for past {days} days ---")
    market_url = f"{base_url.rstrip('/')}/api/v1/market-data"

    try:
        market_records = fetch_real_market_data(days=days)
    except Exception as e:
        logger.warning(f"Real market data fetch encountered an error: {e}. Switching to synthetic generator.")
        market_records = generate_all_synthetic_market_data(days=days)

    if not market_records:
        logger.warning("No market records found. Generating synthetic fallback...")
        market_records = generate_all_synthetic_market_data(days=days)

    logger.info(f"Seeding {len(market_records)} market data telemetry points to {market_url}...")

    success_count = 0
    failure_count = 0
    session = requests.Session()
    bulk_url = f"{market_url}/bulk"

    # Fast bulk batch ingestion
    batch_size = 100
    use_bulk = True
    for i in range(0, len(market_records), batch_size):
        batch = market_records[i:i + batch_size]
        if use_bulk:
            try:
                resp = session.post(bulk_url, json=batch, timeout=30)
                if resp.status_code == 201:
                    success_count += len(batch)
                    logger.info(f"Bulk ingested {success_count}/{len(market_records)} market records...")
                    continue
                else:
                    logger.warning(f"Bulk returned status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"Bulk ingestion failed ({e}), falling back to single-record...")
                use_bulk = False

        for idx, record in enumerate(batch, start=i + 1):
            for attempt in range(3):
                try:
                    resp = session.post(market_url, json=record, timeout=15)
                    if resp.status_code == 201:
                        success_count += 1
                        break
                    else:
                        if attempt == 2:
                            failure_count += 1
                except Exception as err:
                    if attempt == 2:
                        failure_count += 1
                    time.sleep(0.5)

    logger.info(f"Market Data Seeding Complete. Success: {success_count}, Failed: {failure_count}")
    return success_count


def seed_port_data(base_url: str) -> int:
    """Generates port draft constraints and waiting times and POSTs to backend."""
    logger.info("--- Generating Indian Port Draft Limits & Congestion Telemetry ---")
    port_url = f"{base_url.rstrip('/')}/api/v1/port-data"

    ports = generate_port_telemetry(include_anomalies=True)
    logger.info(f"Seeding {len(ports)} port constraint records to {port_url}...")

    success_count = 0
    failure_count = 0
    session = requests.Session()

    for idx, port in enumerate(ports, start=1):
        for attempt in range(3):
            try:
                response = session.post(port_url, json=port, timeout=10)
                if response.status_code in (200, 201):
                    success_count += 1
                    break
                else:
                    if attempt == 2:
                        failure_count += 1
                        logger.warning(f"Failed to seed port {port.get('port_name')}: {response.status_code} {response.text}")
            except Exception as e:
                if attempt == 2:
                    failure_count += 1
                    logger.error(f"Error seeding port {port.get('port_name')}: {e}")
                time.sleep(0.5)

    logger.info(f"Port Data Seeding Complete. Success: {success_count}/{len(ports)}")
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Master Seeding Script for Freight DSS")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the FastAPI backend (default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        help="Number of days of historical market data to ingest (default: 180)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.01,
        help="Delay in seconds between HTTP POST requests (default: 0.01)"
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip backend health check before seeding"
    )

    args = parser.parse_args()

    logger.info("==================================================")
    logger.info(" SIH26006 Freight DSS - Data Ingestion & Seeding")
    logger.info("==================================================")

    if not args.skip_health_check:
        if not check_backend_health(args.api_url):
            logger.error(
                f"Backend is not responding at {args.api_url}. "
                "Ensure FastAPI is running (`cd backend && uvicorn main:app --port 8000`)."
            )
            sys.exit(1)

    # 1. Seed Market Telemetry
    seed_market_data(base_url=args.api_url, days=args.days, delay=args.delay)

    # 2. Seed Port Telemetry
    seed_port_data(base_url=args.api_url)

    logger.info("All data ingestion and database seeding tasks completed successfully!")


if __name__ == "__main__":
    main()
