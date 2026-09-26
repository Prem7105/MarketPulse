import numpy as np
from scipy import stats

from app.research.returns import validate_series


def diagnostics(returns):
    validate_series(returns)
    constant = returns.std() < 1e-14
    jb = stats.jarque_bera(returns) if len(returns) >= 8 and not constant else None
    qq = stats.probplot(returns, dist="norm", fit=False)
    return {
        "mean": float(returns.mean()),
        "median": float(returns.median()),
        "variance": float(returns.var()),
        "std": float(returns.std()),
        "skew": None if constant or len(returns) < 3 else float(stats.skew(returns, bias=False)),
        "excess_kurtosis": (
            None if constant or len(returns) < 4 else float(stats.kurtosis(returns, bias=False))
        ),
        "percentiles": {
            str(q): float(returns.quantile(q)) for q in [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
        },
        "jarque_bera": (
            None if jb is None else {"statistic": float(jb.statistic), "p_value": float(jb.pvalue)}
        ),
        "qq": {"theoretical": np.asarray(qq[0]).tolist(), "observed": np.asarray(qq[1]).tolist()},
    }
