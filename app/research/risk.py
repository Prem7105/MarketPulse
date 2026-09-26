import numpy as np
import pandas as pd

from app.research.drawdown import drawdown, episodes
from app.research.returns import annualized_return, validate_series


def safe_ratio(numerator, denominator):
    return (
        float(numerator / denominator)
        if np.isfinite(denominator) and abs(denominator) > 1e-14
        else None
    )


def metrics(returns, benchmark=None, periods=252, annual_rf=0.0, confidence=0.95):
    validate_series(returns)
    if periods <= 0 or annual_rf <= -1 or not 0 < confidence < 1:
        raise ValueError("Invalid annualization, risk-free rate or confidence")
    daily_rf = (1 + annual_rf) ** (1 / periods) - 1
    excess = returns - daily_rf
    sd = returns.std(ddof=1)
    downside = np.sqrt(np.minimum(excess, 0).pow(2).mean())
    loss = -returns
    var = float(loss.quantile(confidence))
    dd = float(drawdown(returns).min())
    cagr = annualized_return(returns, periods)
    result = {
        "observations": len(returns),
        "cumulative_return": float((1 + returns).prod() - 1),
        "annualized_return": cagr,
        "volatility": float(sd),
        "annualized_volatility": float(sd * np.sqrt(periods)),
        "sharpe": safe_ratio(excess.mean() * np.sqrt(periods), excess.std(ddof=1)),
        "sortino": safe_ratio(excess.mean() * np.sqrt(periods), downside),
        "downside_deviation": float(downside * np.sqrt(periods)),
        "max_drawdown": dd,
        "drawdown_duration": max([e["duration"] for e in episodes(returns)], default=0),
        "calmar": safe_ratio(cagr, abs(dd)),
        "var": var,
        "cvar": float(loss[loss >= var].mean()),
    }
    if benchmark is not None:
        validate_series(benchmark)
        if not returns.index.equals(benchmark.index):
            raise ValueError("Benchmark dates must match exactly")
        active = returns - benchmark
        beta = safe_ratio(returns.cov(benchmark), benchmark.var(ddof=1))
        result.update(
            beta=beta,
            tracking_error=float(active.std(ddof=1) * np.sqrt(periods)),
            information_ratio=safe_ratio(active.mean() * np.sqrt(periods), active.std(ddof=1)),
            active_return=float((1 + returns).prod() - (1 + benchmark).prod()),
            alpha=(
                None
                if beta is None
                else float((excess.mean() - beta * (benchmark - daily_rf).mean()) * periods)
            ),
        )
        for label, mask in [("upside_capture", benchmark > 0), ("downside_capture", benchmark < 0)]:
            result[label] = (
                None
                if not mask.any()
                else safe_ratio(
                    (1 + returns[mask]).prod() ** (1 / mask.sum()) - 1,
                    (1 + benchmark[mask]).prod() ** (1 / mask.sum()) - 1,
                )
            )
    return result


def covariance_risk(returns: pd.DataFrame, weights, periods=252):
    validate_series(returns)
    w = np.asarray(weights, dtype=float)
    if (
        len(w) != returns.shape[1]
        or not np.isfinite(w).all()
        or not np.isclose(w.sum(), 1)
        or (w < 0).any()
    ):
        raise ValueError("Weights must be finite, nonnegative, match assets and sum to one")
    cov = returns.cov().to_numpy() * periods
    variance = float(w @ cov @ w)
    volatility = np.sqrt(max(variance, 0))
    contributions = w * (cov @ w) / volatility if volatility > 1e-14 else np.zeros_like(w)
    return {
        "variance": variance,
        "volatility": float(volatility),
        "risk_contribution": dict(zip(returns.columns, contributions.tolist())),
    }
