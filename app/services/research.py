"""Dataset queries and persisted, JSON-safe research results."""

import json
import logging
import uuid
from datetime import date, datetime

import numpy as np
import pandas as pd
from sqlalchemy import select

from app.db.models import (
    AnalyticsResult,
    Asset,
    AssetPrice,
    Dataset,
    Factor,
    FactorReturn,
    ResearchRun,
    RiskFreeRate,
)
from app.research.drawdown import drawdown, episodes
from app.research.returns import period_returns, simple_returns
from app.research.risk import metrics
from app.research.rolling import rolling_metrics
from app.research.statistics import diagnostics

METHODOLOGY = "1.0.0"


def clean_json(value):
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean_json(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def records(frame):
    if isinstance(frame, pd.Series):
        frame = frame.to_frame("value")
    return clean_json(frame.rename_axis("date").reset_index().to_dict("records"))


def require_dataset(db, dataset_id):
    from app.core.config import settings

    dataset = db.get(Dataset, dataset_id)
    if dataset is None or (
        "SYNTHETIC" in dataset.source.upper() and not settings().allow_synthetic_data
    ):
        raise LookupError("Dataset not available; load real market data")
    return dataset


def price_panel(db, dataset_id, symbols, start=None, end=None):
    require_dataset(db, dataset_id)
    query = (
        select(AssetPrice.date, Asset.symbol, AssetPrice.adjusted_close)
        .join(Asset)
        .where(AssetPrice.dataset_id == dataset_id, Asset.symbol.in_(symbols))
    )
    if start:
        query = query.where(AssetPrice.date >= start)
    if end:
        query = query.where(AssetPrice.date <= end)
    frame = pd.DataFrame(db.execute(query).all(), columns=["date", "symbol", "price"])
    if frame.empty or set(frame.symbol) != set(symbols):
        raise ValueError("Selected assets have no data in this dataset/date range")
    frame.date = pd.to_datetime(frame.date)
    panel = (
        frame.pivot(index="date", columns="symbol", values="price")
        .astype(float)
        .sort_index()
        .reindex(columns=symbols)
    )
    if panel.isna().any().any():
        raise ValueError(
            "Selected price calendars differ. Supply a common complete calendar; no implicit filling/dropping"
        )
    if len(panel) < 3:
        raise ValueError("At least three complete price observations required")
    return panel


def factor_panel(db, dataset_id, index, names):
    rows = db.execute(
        select(FactorReturn.date, Factor.name, FactorReturn.value)
        .join(Factor)
        .where(FactorReturn.dataset_id == dataset_id, Factor.name.in_(names))
    ).all()
    if not rows:
        raise ValueError("No factors in this dataset; import factor CSV first")
    frame = pd.DataFrame(rows, columns=["date", "name", "value"])
    frame.date = pd.to_datetime(frame.date)
    panel = frame.pivot(index="date", columns="name", values="value").reindex(
        index=index, columns=names
    )
    rates = db.execute(
        select(RiskFreeRate.date, RiskFreeRate.rate).where(RiskFreeRate.dataset_id == dataset_id)
    ).all()
    rf = pd.Series({pd.Timestamp(d): float(r) for d, r in rates}).reindex(index)
    if rf.isna().any():
        raise ValueError("Complete daily risk-free data required for factor analysis")
    return panel, rf


def save_run(db, kind, dataset_id, parameters, results, commit=True):
    result = clean_json(results)
    json.dumps(result, allow_nan=False)
    run = ResearchRun(
        id=str(uuid.uuid4()),
        kind=kind,
        dataset_id=dataset_id,
        parameters=clean_json(parameters),
        results=result,
        methodology=METHODOLOGY,
    )
    db.add(run)
    db.flush()
    db.add(AnalyticsResult(run_id=run.id, result=result))
    if commit:
        db.commit()
    logging.getLogger(__name__).info("research kind=%s run=%s dataset=%s", kind, run.id, dataset_id)
    return {
        "run_id": run.id,
        "dataset_id": dataset_id,
        "methodology": METHODOLOGY,
        "parameters": run.parameters,
        "results": result,
    }


def asset_analysis(panel, symbol, benchmark, periods, annual_rf, confidence, window):
    returns = simple_returns(panel)
    r, b = returns[symbol], returns[benchmark] if benchmark else None
    result = {
        "metrics": metrics(r, b, periods, annual_rf, confidence),
        "prices": records(panel[symbol]),
        "returns": records(r),
        "equity": records((1 + r).cumprod()),
        "drawdown": records(drawdown(r)),
        "drawdown_table": episodes(r),
        "rolling": records(rolling_metrics(r, b, window, periods, annual_rf)),
        "statistics": diagnostics(r),
        "period_returns": {k: records(v) for k, v in period_returns(r).items()},
    }
    if b is not None:
        relative = (1 + r) / (1 + b) - 1
        result["benchmark_equity"] = records((1 + b).cumprod())
        result["relative_drawdown"] = records(drawdown(relative))
    return result


RANK_DIRECTIONS = {
    "sharpe": False,
    "sortino": False,
    "annualized_volatility": True,
    "max_drawdown": False,
    "cvar": True,
    "annualized_return": False,
}


def compare(panel, symbols, benchmark, periods=252, annual_rf=0, confidence=0.95, ranking="sharpe"):
    if ranking not in RANK_DIRECTIONS:
        raise ValueError("Unsupported ranking metric")
    returns = simple_returns(panel)
    summary = pd.DataFrame(
        {
            s: metrics(
                returns[s],
                returns[benchmark] if benchmark else None,
                periods,
                annual_rf,
                confidence,
            )
            for s in symbols
        }
    ).T
    summary["rank"] = summary[ranking].rank(
        ascending=RANK_DIRECTIONS[ranking], method="average", na_option="keep"
    )
    return {
        "summary": clean_json(summary.reset_index(names="symbol").to_dict("records")),
        "correlation": clean_json(returns[symbols].corr().to_dict()),
        "covariance": clean_json((returns[symbols].cov() * periods).to_dict()),
        "ranking": {
            "metric": ranking,
            "ascending": RANK_DIRECTIONS[ranking],
            "ties": "average",
            "undefined": "excluded",
        },
    }
