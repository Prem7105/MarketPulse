"""Path-dependent holdings; weights drift between scheduled rebalances."""

import numpy as np
import pandas as pd

from app.research.returns import simple_returns


def validate_weights(weights, columns):
    if set(weights) != set(columns):
        raise ValueError("Provide exactly one weight per selected asset")
    values = np.array([weights[c] for c in columns], float)
    if (
        not np.isfinite(values).all()
        or (values < 0).any()
        or not np.isclose(values.sum(), 1, atol=1e-8, rtol=0)
    ):
        raise ValueError("Long-only weights must be finite, nonnegative and sum to one")
    return values


def rebalance_mask(index, frequency):
    if frequency not in {"daily", "monthly", "quarterly", "none"}:
        raise ValueError("Invalid rebalancing frequency")
    mask = np.zeros(len(index), dtype=bool)
    if len(index):
        mask[0] = True
    if frequency == "daily":
        mask[:] = True
    elif frequency in {"monthly", "quarterly"}:
        groups = index.to_period("M" if frequency == "monthly" else "Q")
        mask[1:] = groups[1:] != groups[:-1]
    return mask


def simulate(prices, targets, cost_bps=0.0, annual_rf=0.0, periods=252):
    """Targets are beginning-interval weights; NaN row means keep holdings.

    Strategy callers must lag close-derived signals before passing targets.
    A proportional cost c reduces wealth before the holding return: (1-c)(1+r).
    """
    returns = simple_returns(prices)
    if not targets.index.equals(returns.index) or list(targets.columns) != list(returns.columns):
        raise ValueError("Target dates and assets must match return panel")
    if not 0 <= cost_bps <= 1000 or annual_rf <= -1 or periods <= 0:
        raise ValueError("Invalid cost, risk-free rate or annualization")
    values = targets.to_numpy(float)
    valid = ~np.isnan(values).all(axis=1)
    if (
        not np.isfinite(values[valid]).all()
        or (values[valid] < 0).any()
        or (values[valid].sum(axis=1) > 1 + 1e-8).any()
    ):
        raise ValueError("Targets must be complete long-only rows with exposure at most one")
    daily_rf = (1 + annual_rf) ** (1 / periods) - 1
    weights = np.zeros(returns.shape[1])
    cash, wealth = 1.0, 1.0
    records, holdings, contributions = [], [], []
    for i, (date, row) in enumerate(returns.iterrows()):
        turnover = 0.0
        if valid[i]:
            target = values[i]
            turnover = float(np.abs(target - weights).sum())
            weights = target.copy()
            cash = max(0.0, 1 - weights.sum())
        cost = turnover * cost_bps / 10000
        asset_contrib = weights * row.to_numpy()
        cash_contrib = cash * daily_rf
        gross = float(asset_contrib.sum() + cash_contrib)
        net = (1 - cost) * (1 + gross) - 1
        holdings.append(weights.copy())
        contributions.append(
            [
                *(wealth * (1 - cost) * asset_contrib),
                wealth * (1 - cost) * cash_contrib,
                -wealth * cost,
            ]
        )
        wealth *= 1 + net
        records.append([gross, net, turnover, cost, wealth])
        if 1 + gross <= 0:
            raise ValueError("Portfolio wealth exhausted")
        weights = weights * (1 + row.to_numpy()) / (1 + gross)
        cash = cash * (1 + daily_rf) / (1 + gross)
    return {
        "path": pd.DataFrame(
            records, index=returns.index, columns=["gross", "net", "turnover", "cost", "wealth"]
        ),
        "weights": pd.DataFrame(holdings, index=returns.index, columns=returns.columns),
        "contributions": pd.DataFrame(
            contributions, index=returns.index, columns=[*returns.columns, "cash", "cost"]
        ),
    }


def portfolio(prices, weights, frequency="monthly", cost_bps=0.0, annual_rf=0.0, periods=252):
    vector = validate_weights(weights, prices.columns)
    targets = pd.DataFrame(np.nan, index=prices.index[1:], columns=prices.columns)
    targets.loc[rebalance_mask(targets.index, frequency)] = vector
    return simulate(prices, targets, cost_bps, annual_rf, periods)
