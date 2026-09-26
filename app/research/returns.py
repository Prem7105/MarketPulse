import numpy as np


def validate_series(values, minimum=2):
    if (
        len(values) < minimum
        or values.isna().any().any()
        or not np.isfinite(values.to_numpy()).all()
    ):
        raise ValueError(f"Need at least {minimum} complete finite observations")
    if values.index.has_duplicates or not values.index.is_monotonic_increasing:
        raise ValueError("Observation index must be unique and increasing")


def simple_returns(prices):
    validate_series(prices)
    if (prices <= 0).any().any():
        raise ValueError("Prices must be positive")
    return prices.pct_change(fill_method=None).iloc[1:]


def log_returns(prices):
    return np.log1p(simple_returns(prices))


def equity(returns):
    validate_series(returns, 1)
    if (returns < -1).any().any():
        raise ValueError("Unlevered returns cannot be less than -100%")
    return (1 + returns).cumprod()


def annualized_return(returns, periods=252):
    if periods <= 0:
        raise ValueError("Periods per year must be positive")
    return float(equity(returns).iloc[-1] ** (periods / len(returns)) - 1)


def period_returns(returns):
    return {
        name: ((1 + returns).resample(freq).prod(min_count=1) - 1)
        for name, freq in [("daily", "D"), ("weekly", "W-FRI"), ("monthly", "ME"), ("yearly", "YE")]
    }
