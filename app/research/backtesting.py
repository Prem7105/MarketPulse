import numpy as np
import pandas as pd

from app.research.portfolio import rebalance_mask, simulate
from app.research.returns import simple_returns

STRATEGIES = ["buy_hold", "equal_weight", "momentum", "moving_average", "volatility_target"]


def backtest(
    prices,
    strategy="momentum",
    lookback=60,
    frequency="monthly",
    cost_bps=10.0,
    target_vol=0.15,
    periods=252,
    annual_rf=0.0,
):
    if strategy not in STRATEGIES or lookback < 2 or target_vol <= 0:
        raise ValueError("Invalid strategy, lookback or target volatility")
    returns = simple_returns(prices)
    if strategy not in {"buy_hold", "equal_weight"} and len(prices) < lookback + 3:
        raise ValueError("Insufficient history for lookback plus execution delay")
    equal = pd.DataFrame(1 / prices.shape[1], index=prices.index, columns=prices.columns)
    if strategy in {"buy_hold", "equal_weight"}:
        desired = equal
    elif strategy == "momentum":
        positive = (prices / prices.shift(lookback) - 1).clip(lower=0)
        desired = positive.div(positive.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    elif strategy == "moving_average":
        desired = equal * (prices > prices.rolling(lookback).mean())
    else:
        vol = returns.mean(axis=1).rolling(lookback).std(ddof=1) * np.sqrt(periods)
        scale = (target_vol / vol.replace(0, np.nan)).clip(upper=1).reindex(prices.index).fillna(0)
        desired = equal.mul(scale, axis=0)
    # close t observation → close t+1 execution → interval ending t+2 return.
    targets = desired.shift(2).reindex(returns.index).copy()
    mask = rebalance_mask(targets.index, "none" if strategy == "buy_hold" else frequency)
    # Fixed allocations are chosen before sample begins and require no price-derived signal.
    if strategy in {"buy_hold", "equal_weight"}:
        targets = equal.reindex(returns.index).copy()
    targets.loc[~mask] = np.nan
    result = simulate(prices, targets, cost_bps, annual_rf, periods)
    result["signals"] = desired
    return result
