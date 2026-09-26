"""Normalized observations and immutable research records."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from app.db.database import Base


def timestamp():
    return Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(String(64), primary_key=True)
    source = Column(String(200), nullable=False)
    created_at = timestamp()
    row_count = Column(Integer, nullable=False)
    start = Column(Date, nullable=False)
    end = Column(Date, nullable=False)
    quality = Column(JSON, nullable=False)


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")


class AssetPrice(Base):
    __tablename__ = "asset_prices"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(ForeignKey("datasets.id"), nullable=False, index=True)
    asset_id = Column(ForeignKey("assets.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    adjusted_close = Column(Numeric(20, 8), nullable=False)
    __table_args__ = (
        UniqueConstraint("dataset_id", "asset_id", "date"),
        CheckConstraint(
            "adjusted_close > 0 AND low > 0 AND high >= low AND open >= low AND open <= high AND close >= low AND close <= high"
        ),
    )


class BenchmarkPrice(Base):
    __tablename__ = "benchmark_prices"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(ForeignKey("datasets.id"), nullable=False, index=True)
    asset_id = Column(ForeignKey("assets.id"), nullable=False)
    date = Column(Date, nullable=False)
    adjusted_close = Column(Numeric(20, 8), nullable=False)
    __table_args__ = (
        UniqueConstraint("dataset_id", "asset_id", "date"),
        CheckConstraint("adjusted_close > 0"),
    )


class RiskFreeRate(Base):
    __tablename__ = "risk_free_rates"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(ForeignKey("datasets.id"), nullable=False)
    date = Column(Date, nullable=False)
    rate = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint("dataset_id", "date"), CheckConstraint("rate > -1"))


class Factor(Base):
    __tablename__ = "factors"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)


class FactorReturn(Base):
    __tablename__ = "factor_returns"
    id = Column(Integer, primary_key=True)
    dataset_id = Column(ForeignKey("datasets.id"), nullable=False, index=True)
    factor_id = Column(ForeignKey("factors.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    value = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint("dataset_id", "factor_id", "date"),)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    dataset_id = Column(ForeignKey("datasets.id"), nullable=False)
    created_at = timestamp()


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(ForeignKey("portfolios.id"), nullable=False, index=True)
    asset_id = Column(ForeignKey("assets.id"), nullable=False)
    weight = Column(Numeric(18, 10), nullable=False)
    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id"),
        CheckConstraint("weight >= 0 AND weight <= 1"),
    )


class ResearchRun(Base):
    __tablename__ = "research_runs"
    id = Column(String(36), primary_key=True)
    kind = Column(String(32), nullable=False)
    dataset_id = Column(ForeignKey("datasets.id"), nullable=False, index=True)
    parameters = Column(JSON, nullable=False)
    results = Column(JSON, nullable=False)
    methodology = Column(String(32), nullable=False, default="1.0.0")
    created_at = timestamp()


class AnalyticsResult(Base):
    __tablename__ = "analytics_results"
    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey("research_runs.id"), nullable=False, index=True)
    result = Column(JSON, nullable=False)


class Backtest(Base):
    __tablename__ = "backtests"
    id = Column(Integer, primary_key=True)
    run_id = Column(ForeignKey("research_runs.id"), nullable=False, unique=True)
    strategy = Column(String(40), nullable=False)
    parameters = Column(JSON, nullable=False)


class BacktestReturn(Base):
    __tablename__ = "backtest_returns"
    id = Column(Integer, primary_key=True)
    backtest_id = Column(ForeignKey("backtests.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    gross = Column(Float, nullable=False)
    net = Column(Float, nullable=False)
    turnover = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint("backtest_id", "date"),)
