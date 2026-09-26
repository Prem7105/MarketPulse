import numpy as np
import pandas as pd

from app.research.drawdown import drawdown


def rolling_metrics(returns, benchmark=None, window=60, periods=252, annual_rf=0):
    if window < 2:
        raise ValueError("Window must be at least two")
    roll = returns.rolling(window)
    rf = (1 + annual_rf) ** (1 / periods) - 1
    sd = roll.std(ddof=1).replace(0, np.nan)
    result = pd.DataFrame(
        {
            "return": roll.apply(lambda x: np.prod(1 + x) - 1, raw=True),
            "volatility": roll.std(ddof=1) * np.sqrt(periods),
            "sharpe": (roll.mean() - rf) / sd * np.sqrt(periods),
            "drawdown": roll.apply(lambda x: drawdown(x).min()),
        }
    )
    if benchmark is not None:
        result["beta"] = roll.cov(benchmark) / benchmark.rolling(window).var().replace(0, np.nan)
        result["correlation"] = roll.corr(benchmark)
        result["excess_return"] = roll.apply(
            lambda x: np.prod(1 + x) - 1, raw=True
        ) - benchmark.rolling(window).apply(lambda x: np.prod(1 + x) - 1, raw=True)
    return result
