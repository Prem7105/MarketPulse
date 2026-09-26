"""Reproducible end-to-end research case through the same services as the API."""

import argparse
from pathlib import Path

from sqlalchemy import select

from app.api.routes import create_report
from app.api.schemas import ResearchRequest
from app.db.database import SessionLocal
from app.db.models import Dataset, ResearchRun
from app.services.reporting import render_report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset")
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT"])
    parser.add_argument("--output", default="reports/sample_research.md")
    args = parser.parse_args()
    with SessionLocal() as db:
        dataset = args.dataset or db.scalar(
            select(Dataset.id)
            .where(~Dataset.source.ilike("%SYNTHETIC%"))
            .order_by(Dataset.created_at.desc())
        )
        if not dataset:
            parser.error(
                "No real dataset. Configure the API key and run scripts.ingest_market_data first"
            )
        request = ResearchRequest(dataset_id=dataset, symbols=args.symbols, annual_rf=0.03)
        result = create_report(request, db)
        report = render_report(db.get(ResearchRun, result["run_id"]))
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report)
        print(f"Report: {output}; run: {result['run_id']}; dataset: {dataset}")
