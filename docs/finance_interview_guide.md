# Finance interview reference

| Concept | Explain it in an interview | Relevant limitation |
|---|---|---|
| Stock | An ownership claim on a company, with uncertain future cash flows and residual value. | Price movement is not the same as business quality. |
| Bond | A contractual debt claim with coupons/principal and credit/interest-rate risks. | MarketPulse does not yet model duration, convexity or default cash flows. |
| ETF | A traded fund share representing a portfolio or strategy. | Tracking difference, fees and tradability matter. |
| Index | A rules-based representation of a market universe. | Often not directly investable; constituent history matters. |
| Benchmark | A relevant comparison portfolio for the investment mandate. | An inappropriate benchmark can mislead alpha/relative risk. |
| Risk-free rate | A reference return for the relevant currency and horizon. | A constant annual assumption is a simplification. |
| Return | Change in wealth including the chosen price adjustment/cash-flow convention. | Our provider must supply properly adjusted prices. |
| Volatility | Dispersion of returns, commonly sample standard deviation. | Ignores liquidity, leverage and some tail/path risks. |
| Sharpe | Mean excess return per unit of excess-return variability. | Historical estimate; zero variance makes it undefined. |
| Sortino | Mean target excess return per unit of downside deviation. | Depends on target and denominator convention. |
| Beta | Linear sensitivity to benchmark excess returns. | Not a total risk measure or causal coefficient. |
| Alpha | Regression intercept conditional on the included factors. | May reflect noise, omitted factors or selection. |
| CAPM | Expected excess return linked to market beta in an equilibrium model. | Strong assumptions; a fitted regression is not proof of CAPM. |
| Factor model | Explains returns using exposures to specified systematic return drivers. | Construction, timing and correlated factors affect interpretation. |
| Diversification | Combining exposures whose joint returns reduce concentration in risk sources. | Correlations may rise in stress. |
| Correlation | Standardized covariance bounded between −1 and 1 for defined finite-variance series. | Zero correlation does not generally mean independence. |
| Covariance | Joint variation of two returns; enters portfolio variance. | Sensitive to estimation window and regime. |
| Drawdown | Loss relative to a prior wealth peak along a path. | Backward-looking and path-dependent. |
| VaR | Loss quantile at a stated confidence and horizon. | Not maximum loss; interpolation and sample choices matter. |
| CVaR / ES | Average sampled loss beyond the VaR threshold in this implementation. | Sparse historical tails make estimates unstable. |
| Tracking error | Volatility of portfolio-minus-benchmark return. | High tracking error is not automatically good or bad. |
| Information ratio | Mean active return divided by active-return variability. | Requires consistent horizon and a defensible benchmark. |
| Active return | Portfolio return relative to benchmark; cumulative difference is explicitly defined. | Difference in terminal wealth is not relative wealth ratio. |
| Portfolio construction | Choosing exposures under objectives and constraints. | Equal weights are a baseline, not an optimized solution. |
| Rebalancing | Trading to restore a target allocation at chosen times. | Affects turnover, taxes, costs and realized path. |
| Transaction costs | Economic loss from trading, modeled here as bps on risky turnover. | Does not include market impact, bid/ask dynamics or illiquidity. |
| Risk contribution | Component contribution to a specified portfolio risk measure. | Covariance volatility contribution is not a universal decomposition of risk. |
| Brinson attribution | Allocation, selection and interaction relative to benchmark categories. | Our function is single-period; multi-period linking needs additional methodology. |
| Momentum | A rule allocating to assets with positive trailing relative performance. | Strong in-sample results may fail after costs or regime change. |
| Volatility targeting | Scaling exposure inversely to estimated recent volatility. | Lagged estimates can react after a shock and induce turnover. |

A defensible answer states the definition, formula, units, assumptions and one situation where the metric is misleading. Use docs/mathematics.md for calculations and tests/unit/test_math.py for hand-checkable examples.
