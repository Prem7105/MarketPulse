import hashlib
import io
import logging
from pathlib import Path
from typing import Protocol

import pandas as pd
from sqlalchemy import insert, select

from app.db.models import (
    Asset,
    AssetPrice,
    BenchmarkPrice,
    Dataset,
    Factor,
    FactorReturn,
    RiskFreeRate,
)
from app.services.validation import validate_prices

logger = logging.getLogger(__name__)


class MarketDataProvider(Protocol):
    source: str

    def read(self) -> pd.DataFrame: ...


class CSVProvider:
    def __init__(self, source: str | Path | io.StringIO, label="user CSV"):
        self.path = source
        self.source = label

    def read(self):
        return pd.read_csv(self.path, dtype={"symbol": str, "date": str})


def ingest(db, provider: MarketDataProvider, factors=None, risk_free=None, benchmark="SPY"):
    from app.core.config import settings

    if "SYNTHETIC" in provider.source.upper() and not settings().allow_synthetic_data:
        raise ValueError("Synthetic data is disabled. Import real provider observations.")
    clean, quality = validate_prices(provider.read())
    if clean.empty:
        raise ValueError(f"No valid rows: {quality.to_dict()}")
    auxiliary = []
    for panel in [factors, risk_free]:
        if panel is not None:
            if panel.index.has_duplicates or not isinstance(panel.index, pd.DatetimeIndex):
                raise ValueError("Auxiliary observations need unique DatetimeIndex")
            if (
                panel.isna().any().any()
                or not pd.DataFrame(panel).map(lambda x: isinstance(x, (int, float))).all().all()
            ):
                raise ValueError("Auxiliary observations must be complete numeric data")
            import numpy as np

            if not np.isfinite(panel.to_numpy()).all():
                raise ValueError("Auxiliary observations must be finite")
            if not panel.index.isin(clean.date.unique()).all():
                raise ValueError("Auxiliary dates must belong to price dataset")
            auxiliary.append(panel.sort_index().to_csv(float_format="%.17g"))
    if risk_free is not None and (risk_free <= -1).any():
        raise ValueError("Daily risk-free return must exceed -1")
    clean = clean.round(8)
    if (clean[["open", "high", "low", "close", "adjusted_close"]] <= 0).any().any():
        raise ValueError("Price falls below database precision of eight decimal places")
    canonical = clean.to_csv(index=False, date_format="%Y-%m-%d", float_format="%.8f")
    digest = hashlib.sha256(
        (
            canonical + "\n" + "\n".join(auxiliary) + "\n" + provider.source + "\n" + str(benchmark)
        ).encode()
    ).hexdigest()
    if db.get(Dataset, digest):
        return digest, quality.to_dict()
    try:
        db.add(
            Dataset(
                id=digest,
                source=provider.source,
                row_count=len(clean),
                start=clean.date.min().date(),
                end=clean.date.max().date(),
                quality={
                    **quality.to_dict(),
                    "provider_metadata": getattr(provider, "metadata", {}),
                },
            )
        )
        db.flush()
        asset_map = {a.symbol: a.id for a in db.scalars(select(Asset)).all()}
        for symbol in clean.symbol.unique():
            if symbol not in asset_map:
                asset = Asset(symbol=symbol, name=symbol, currency="USD")
                db.add(asset)
                db.flush()
                asset_map[symbol] = asset.id
        rows = clean.to_dict("records")
        for row in rows:
            row["dataset_id"] = digest
            row["asset_id"] = asset_map[row.pop("symbol")]
            row["date"] = row["date"].date()
        for offset in range(0, len(rows), 2000):
            db.execute(insert(AssetPrice), rows[offset : offset + 2000])
        if benchmark in asset_map:
            b_rows = [
                {k: r[k] for k in ["dataset_id", "asset_id", "date", "adjusted_close"]}
                for r in rows
                if r["asset_id"] == asset_map[benchmark]
            ]
            if b_rows:
                db.execute(insert(BenchmarkPrice), b_rows)
        if factors is not None:
            for name in factors.columns:
                factor = db.scalar(select(Factor).where(Factor.name == name))
                if factor is None:
                    factor = Factor(name=name)
                    db.add(factor)
                    db.flush()
                db.execute(
                    insert(FactorReturn),
                    [
                        {
                            "dataset_id": digest,
                            "factor_id": factor.id,
                            "date": d.date(),
                            "value": float(v),
                        }
                        for d, v in factors[name].items()
                    ],
                )
        if risk_free is not None:
            db.execute(
                insert(RiskFreeRate),
                [
                    {"dataset_id": digest, "date": d.date(), "rate": float(v)}
                    for d, v in risk_free.items()
                ],
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info(
        "ingestion dataset=%s accepted=%s rejected=%s",
        digest,
        quality.rows_accepted,
        quality.rows_rejected,
    )
    return digest, quality.to_dict()
