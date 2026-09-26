import io

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.schemas import (
    BacktestRequest,
    FactorRequest,
    IngestRequest,
    PortfolioRequest,
    ResearchRequest,
)
from app.core.config import settings
from app.db.database import get_db
from app.db.models import (
    Asset,
    AssetPrice,
    Backtest,
    BacktestReturn,
    Dataset,
    Portfolio,
    PortfolioPosition,
    ResearchRun,
)
from app.research.backtesting import backtest
from app.research.drawdown import drawdown
from app.research.factors import regress
from app.research.portfolio import validate_weights
from app.research.returns import simple_returns
from app.research.risk import metrics
from app.services.ingestion import CSVProvider, ingest
from app.services.market_data import TwelveDataProvider, symbols_list
from app.services.portfolio import analyze_portfolio
from app.services.reporting import render_report, research_case
from app.services.research import (
    asset_analysis,
    compare,
    factor_panel,
    price_panel,
    records,
    require_dataset,
    save_run,
)

router = APIRouter()


class MarketRefreshRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=20)
    observations: int = Field(756, ge=3, le=5000)
    benchmark: str = "SPY"


@router.get("/market/status")
def market_status():
    return {
        "provider": settings().market_data_provider,
        "configured": bool(settings().twelvedata_api_key.get_secret_value()),
    }


@router.post("/market/refresh")
def refresh_market(request: MarketRefreshRequest, db=Depends(get_db)):
    symbols = symbols_list(request.symbols + [request.benchmark])
    provider = TwelveDataProvider(symbols, request.observations)
    dataset_id, quality = ingest(db, provider, benchmark=request.benchmark.upper())
    return {"dataset_id": dataset_id, "quality": quality, "provider_metadata": provider.metadata}


@router.get("/market/quotes")
def market_quotes(symbols: str = Query(..., max_length=660)):
    return TwelveDataProvider(symbols.split(",")).quotes()


def panel_for(db, request):
    symbols = list(
        dict.fromkeys(request.symbols + ([request.benchmark] if request.benchmark else []))
    )
    return price_panel(db, request.dataset_id, symbols, request.start, request.end)


@router.get("/datasets")
def datasets(db=Depends(get_db)):
    return [
        {
            "id": d.id,
            "source": d.source,
            "rows": d.row_count,
            "start": d.start,
            "end": d.end,
            "quality": d.quality,
        }
        for d in db.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
        if settings().allow_synthetic_data or "SYNTHETIC" not in d.source.upper()
    ]


@router.post("/ingest")
def import_csv(request: IngestRequest, db=Depends(get_db)):
    factors = (
        pd.read_csv(io.StringIO(request.factors_csv), index_col="date", parse_dates=True)
        if request.factors_csv
        else None
    )
    rf = (
        pd.read_csv(
            io.StringIO(request.risk_free_csv), index_col="date", parse_dates=True
        ).risk_free
        if request.risk_free_csv
        else None
    )
    dataset_id, quality = ingest(
        db, CSVProvider(io.StringIO(request.csv), request.source), factors, rf, request.benchmark
    )
    return {"dataset_id": dataset_id, "quality": quality}


@router.get("/assets")
def assets(dataset_id: str | None = None, db=Depends(get_db)):
    query = select(Asset).join(AssetPrice).join(Dataset).distinct()
    if not settings().allow_synthetic_data:
        query = query.where(~Dataset.source.ilike("%SYNTHETIC%"))
    if dataset_id:
        query = query.where(AssetPrice.dataset_id == dataset_id)
    return [
        {"id": a.id, "symbol": a.symbol, "name": a.name, "currency": a.currency}
        for a in db.scalars(query).all()
    ]


@router.get("/assets/{symbol}")
def asset(symbol: str, db=Depends(get_db)):
    result = db.scalar(select(Asset).where(Asset.symbol == symbol.upper()))
    if result is None:
        raise LookupError("Asset not found")
    return {
        "id": result.id,
        "symbol": result.symbol,
        "name": result.name,
        "currency": result.currency,
    }


@router.get("/assets/{symbol}/prices")
def prices(symbol: str, dataset_id: str, db=Depends(get_db)):
    return records(price_panel(db, dataset_id, [symbol.upper()]))


@router.post("/research/asset")
def research_asset(request: ResearchRequest, db=Depends(get_db)):
    panel = panel_for(db, request)
    result = asset_analysis(
        panel,
        request.symbols[0],
        request.benchmark,
        request.periods,
        request.annual_rf,
        request.confidence,
        request.window,
    )
    return save_run(db, "asset", request.dataset_id, request.model_dump(), result)


@router.get("/assets/{symbol}/metrics")
@router.get("/assets/{symbol}/risk")
@router.get("/assets/{symbol}/drawdown")
def asset_metrics(
    symbol: str,
    dataset_id: str,
    benchmark: str | None = "SPY",
    periods: int = Query(252, ge=1, le=366),
    db=Depends(get_db),
):
    return research_asset(
        ResearchRequest(
            dataset_id=dataset_id, symbols=[symbol], benchmark=benchmark, periods=periods
        ),
        db,
    )


@router.post("/research/compare")
def comparison(request: ResearchRequest, db=Depends(get_db)):
    panel = panel_for(db, request)
    return save_run(
        db,
        "comparison",
        request.dataset_id,
        request.model_dump(),
        compare(
            panel,
            request.symbols,
            request.benchmark,
            request.periods,
            request.annual_rf,
            request.confidence,
            request.ranking,
        ),
    )


@router.post("/research/factor-analysis")
def factors(request: FactorRequest, db=Depends(get_db)):
    panel = panel_for(db, request)
    returns = simple_returns(panel)
    f, rf = factor_panel(db, request.dataset_id, returns.index, request.factors)
    result = {
        s: regress(returns[s], f, rf, request.periods, request.hac_lags) for s in request.symbols
    }
    return save_run(db, "factors", request.dataset_id, request.model_dump(), result)


@router.post("/portfolios")
def create_portfolio(request: PortfolioRequest, db=Depends(get_db)):
    panel = panel_for(db, request)
    weights = (
        request.weights
        if request.weights is not None
        else {s: 1 / len(request.symbols) for s in request.symbols}
    )
    validate_weights(weights, request.symbols)
    result = analyze_portfolio(
        panel,
        request.symbols,
        weights,
        request.benchmark,
        request.frequency,
        request.cost_bps,
        request.periods,
        request.annual_rf,
        request.confidence,
    )
    obj = Portfolio(name=request.name, dataset_id=request.dataset_id)
    db.add(obj)
    db.flush()
    asset_map = {
        a.symbol: a.id for a in db.scalars(select(Asset).where(Asset.symbol.in_(request.symbols)))
    }
    for symbol, weight in weights.items():
        db.add(PortfolioPosition(portfolio_id=obj.id, asset_id=asset_map[symbol], weight=weight))
    params = request.model_dump()
    params["portfolio_id"] = obj.id
    params["weights"] = weights
    run = save_run(db, "portfolio", request.dataset_id, params, result)
    return {"portfolio_id": obj.id, **run}


@router.get("/portfolios/{portfolio_id}")
@router.get("/portfolios/{portfolio_id}/analytics")
@router.get("/portfolios/{portfolio_id}/attribution")
def portfolio_result(portfolio_id: int, db=Depends(get_db)):
    obj = db.get(Portfolio, portfolio_id)
    if not obj:
        raise LookupError("Portfolio not found")
    require_dataset(db, obj.dataset_id)
    runs = db.scalars(
        select(ResearchRun)
        .where(ResearchRun.kind == "portfolio")
        .order_by(ResearchRun.created_at.desc())
    ).all()
    run = next((r for r in runs if r.parameters.get("portfolio_id") == portfolio_id), None)
    if run is None:
        raise LookupError("Portfolio research run not found")
    return {
        "portfolio_id": obj.id,
        "name": obj.name,
        "run_id": run.id,
        "parameters": run.parameters,
        "results": run.results,
    }


@router.post("/backtests")
def create_backtest(request: BacktestRequest, db=Depends(get_db)):
    panel = panel_for(db, request)
    sim = backtest(
        panel[request.symbols],
        request.strategy,
        request.lookback,
        request.frequency,
        request.cost_bps,
        request.target_vol,
        request.periods,
        request.annual_rf,
    )
    b = simple_returns(panel)[request.benchmark] if request.benchmark else None
    result = {
        "metrics": metrics(
            sim["path"].net, b, request.periods, request.annual_rf, request.confidence
        ),
        "path": records(sim["path"]),
        "weights": records(sim["weights"]),
        "drawdown": records(drawdown(sim["path"].net)),
        "signals": records(sim["signals"]),
        "timing": "close t signal; close t+1 execution; return ending t+2",
    }
    run = save_run(db, "backtest", request.dataset_id, request.model_dump(), result, commit=False)
    obj = Backtest(
        run_id=run["run_id"], strategy=request.strategy, parameters=request.model_dump(mode="json")
    )
    db.add(obj)
    db.flush()
    db.add_all(
        [
            BacktestReturn(
                backtest_id=obj.id,
                date=d.date(),
                gross=row.gross,
                net=row.net,
                turnover=row.turnover,
                cost=row.cost,
            )
            for d, row in sim["path"].iterrows()
        ]
    )
    db.commit()
    return {"backtest_id": obj.id, **run}


@router.get("/backtests/{backtest_id}")
def get_backtest(backtest_id: int, db=Depends(get_db)):
    obj = db.get(Backtest, backtest_id)
    if not obj:
        raise LookupError("Backtest not found")
    run = db.get(ResearchRun, obj.run_id)
    require_dataset(db, run.dataset_id)
    return {
        "backtest_id": obj.id,
        "run_id": obj.run_id,
        "results": run.results,
        "parameters": obj.parameters,
    }


@router.post("/reports")
def create_report(request: ResearchRequest, db=Depends(get_db)):
    panel = panel_for(db, request)
    dataset = db.get(Dataset, request.dataset_id)
    result = research_case(db, request, panel, dataset.quality, dataset.source)
    return save_run(db, "report", request.dataset_id, request.model_dump(), result)


@router.get("/research/runs")
def runs(db=Depends(get_db)):
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "dataset_id": r.dataset_id,
            "created_at": r.created_at,
            "parameters": r.parameters,
        }
        for r in db.scalars(
            select(ResearchRun)
            .join(Dataset)
            .where(
                True if settings().allow_synthetic_data else ~Dataset.source.ilike("%SYNTHETIC%")
            )
            .order_by(ResearchRun.created_at.desc())
            .limit(100)
        )
    ]


@router.get("/reports/{run_id}", response_class=PlainTextResponse)
def report(run_id: str, db=Depends(get_db)):
    run = db.get(ResearchRun, run_id)
    if not run or run.kind != "report":
        raise LookupError("Report not found")
    require_dataset(db, run.dataset_id)
    return render_report(run)
