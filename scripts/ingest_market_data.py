"""Fetch authenticated historical prices and persist a validated research snapshot."""

import argparse

from app.db.database import SessionLocal
from app.services.ingestion import ingest
from app.services.market_data import MarketDataError, TwelveDataProvider

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "SPY"])
    parser.add_argument("--observations", type=int, default=756)
    parser.add_argument("--benchmark", default="SPY")
    args = parser.parse_args()
    try:
        provider = TwelveDataProvider(args.symbols + [args.benchmark], args.observations)
        with SessionLocal() as db:
            dataset_id, quality = ingest(db, provider, benchmark=args.benchmark.upper())
        print(f"Real dataset: {dataset_id}; accepted bars: {quality['rows_accepted']}")
    except (MarketDataError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
