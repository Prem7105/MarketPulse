import numpy as np
import pandas as pd
import statsmodels.api as sm

from app.research.returns import validate_series


def regress(returns, factors, risk_free=0.0, periods=252, hac_lags=5):
    validate_series(returns)
    validate_series(factors)
    if not returns.index.equals(factors.index):
        raise ValueError("Factor dates must exactly match return dates; missing factor data")
    if isinstance(risk_free, pd.Series) and (
        not returns.index.equals(risk_free.index) or risk_free.isna().any()
    ):
        raise ValueError("Risk-free dates must exactly match returns")
    design = sm.add_constant(factors, has_constant="add")
    if (
        len(returns) < max(20, 3 * design.shape[1])
        or np.linalg.matrix_rank(design) < design.shape[1]
    ):
        raise ValueError("Insufficient observations or rank-deficient factor design")
    model = sm.OLS(returns - risk_free, design).fit(
        cov_type="HAC", cov_kwds={"maxlags": min(hac_lags, len(returns) - 1)}
    )
    intervals = model.conf_int()
    return {
        "observations": int(model.nobs),
        "alpha_daily": float(model.params["const"]),
        "alpha_annual_arithmetic": float(model.params["const"] * periods),
        "r_squared": float(model.rsquared),
        "residual_volatility": float(model.resid.std(ddof=1) * np.sqrt(periods)),
        "covariance": "HAC",
        "coefficients": {
            name: {
                "beta": float(model.params[name]),
                "t": float(model.tvalues[name]),
                "p": float(model.pvalues[name]),
                "ci_low": float(intervals.loc[name, 0]),
                "ci_high": float(intervals.loc[name, 1]),
            }
            for name in model.params.index
        },
    }
