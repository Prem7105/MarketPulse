from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    dataset_id: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]+$")
    symbols: list[str] = Field(min_length=1, max_length=50)
    benchmark: str | None = "SPY"
    start: date | None = None
    end: date | None = None
    periods: int = Field(252, ge=1, le=366)
    annual_rf: float = Field(0.0, gt=-1, le=1)
    confidence: float = Field(0.95, gt=0.5, lt=1)
    window: int = Field(60, ge=2, le=1000)
    ranking: Literal[
        "sharpe", "sortino", "annualized_volatility", "max_drawdown", "cvar", "annualized_return"
    ] = "sharpe"

    @field_validator("symbols")
    @classmethod
    def symbols_valid(cls, values):
        import re

        normalized = [v.strip().upper() for v in values]
        if len(set(normalized)) != len(values) or any(
            not re.fullmatch(r"[A-Z0-9.^-]{1,32}", v) for v in normalized
        ):
            raise ValueError("Symbols must be unique valid tickers")
        return normalized

    @model_validator(mode="after")
    def dates_valid(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("Start must be on or before end")
        return self


class PortfolioRequest(ResearchRequest):
    name: str = Field("Research portfolio", min_length=1, max_length=120)
    weights: dict[str, float] | None = None
    frequency: Literal["none", "daily", "monthly", "quarterly"] = "monthly"
    cost_bps: float = Field(0.0, ge=0, le=1000)


class BacktestRequest(ResearchRequest):
    strategy: Literal[
        "buy_hold", "equal_weight", "momentum", "moving_average", "volatility_target"
    ] = "momentum"
    lookback: int = Field(60, ge=2, le=1000)
    frequency: Literal["none", "daily", "monthly", "quarterly"] = "monthly"
    cost_bps: float = Field(10.0, ge=0, le=1000)
    target_vol: float = Field(0.15, gt=0, le=1)


class FactorRequest(ResearchRequest):
    factors: list[str] = Field(
        default_factory=lambda: ["market", "size", "value", "momentum"], min_length=1, max_length=10
    )
    hac_lags: int = Field(5, ge=0, le=60)

    @field_validator("factors")
    @classmethod
    def unique_factors(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Factor names must be unique")
        return values


class IngestRequest(BaseModel):
    csv: str = Field(min_length=1, max_length=5_000_000)
    source: str = Field(min_length=1, max_length=200)
    benchmark: str = "SPY"
    factors_csv: str | None = Field(None, max_length=2_000_000)
    risk_free_csv: str | None = Field(None, max_length=1_000_000)
