import argparse

import pandas as pd

from app.db.database import SessionLocal
from app.services.ingestion import CSVProvider, ingest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import adjusted daily CSV prices as an immutable dataset"
    )
    parser.add_argument("csv")
    parser.add_argument("--source", required=True)
    parser.add_argument("--factors")
    parser.add_argument("--risk-free")
    parser.add_argument("--benchmark", default="SPY")
    args = parser.parse_args()
    factors = (
        pd.read_csv(args.factors, index_col="date", parse_dates=True) if args.factors else None
    )
    rf = (
        pd.read_csv(args.risk_free, index_col="date", parse_dates=True).risk_free
        if args.risk_free
        else None
    )
    with SessionLocal() as db:
        print(ingest(db, CSVProvider(args.csv, args.source), factors, rf, args.benchmark))
