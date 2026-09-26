# Research methodology

## Question and experimental design

“How do selected large-cap equities compare on return, risk, drawdown, diversification and factor exposure over a defined period?” This is the intended real-data research question. The bundled case exercises that workflow with **fictional synthetic prices**, so it cannot answer the empirical question about actual large-cap equities.

Choose universe, benchmark, currency, adjusted-return convention, period, annualization and risk-free assumptions before ranking outcomes. Record those choices in the run. Inspect rejected rows and retained warnings. Verify that all series share daily trading dates; do not bridge different horizons by silently dropping missing observations. Our strict complete-panel rule trades convenience for comparability.

## Interpretation

Cumulative return answers what happened to invested capital. Annualized return normalizes the observation horizon but can exaggerate short-sample results. Volatility measures symmetric dispersion, not every investment risk. Sharpe estimates compensation per unit of excess-return variability; Sortino emphasizes target shortfalls. Neither is a universal manager score.

Drawdown asks about peak-to-trough loss along this realized path; another ordering of the same returns changes it. VaR is a quantile, not worst possible loss. ES describes the observed tail past that quantile, which can be based on very few events. Confidence level is a modeling choice; it is not confidence that the future risk estimate is correct.

Covariance matters because portfolio outcomes depend on simultaneous asset behavior. Correlations can change in stress, and uncorrelated assets are not necessarily independent. Component volatility contributions are local covariance measures, not guaranteed future risk allocations.

Benchmark analysis separates relative from absolute performance. A high beta can explain strong market-period returns. Positive alpha can reflect noise, missing factors or selected periods; factor coefficients are descriptive exposures. HAC errors account for certain residual dependence, not causality or omitted variables. Report effect sizes, uncertainty, observations and economic meaning together.

## Strategy research integrity

Fix lookbacks, rebalance frequency and costs before examining evaluation results. Price-derived signals at close t first influence the return ending t+2. Fixed buy-and-hold/equal weights need no price-derived warmup. Momentum allocates proportionally to positive trailing returns; nonpositive candidates hold cash. Trend is equal-weight per asset when above its moving average. Volatility targeting scales equal weights by target/trailing realized volatility, bounded at one. There is no leverage.

Compare on matched dates, explicitly include warmup cash and entry costs. Cash return and costs affect net performance. These strategies have not been validated out of sample. A credible next experiment uses a chronological train/validation/test split or walk-forward design, a point-in-time universe, realistic costs and a research log of every attempted variant. Do not select the best full-sample Sharpe and call it a discovery.

## Biases and missing real-world features

Static universes suffer survivorship and selection bias. Providers may retrospectively revise adjusted prices. Using today's index constituents or revised fundamentals in the past leaks knowledge. A two-bar delay protects a specific execution mechanism, not every possible data leak. Snapshot hashing does not make an untrustworthy provider point-in-time accurate.

The engine does not model exchange holidays, overnight/intraday separation, bid/ask spreads, market impact, limited liquidity, settlement, tax, corporate-action processing, FX, delistings or borrow. Uniform bps costs are sensitivity assumptions. The six demo factors are fictional. A demonstration p-value is not evidence about an actual security.

## Reproducibility and neutral reporting

Each analysis run stores a UUID, UTC time, source dataset hash, selected assets, benchmark, dates, parameters, methodology and JSON-safe output. Immutable application imports preserve earlier data versions; privileged SQL updates remain an operational responsibility. A repeated seed reproduces the same dataset, and the same version plus parameters reproduces numerical outputs within floating-point tolerance.

Reports distinguish observed results, regression inference, assumptions and limitations. Undefined ratios are null and are excluded from rank calculations. A ranking displays the metric direction and tie method; it is never a BUY recommendation. The report's portfolio uses monthly equal weights and zero cost; strategy comparison uses 10 bps. Both are disclosed so different cost assumptions are not confused with strategy skill.

## Performance engineering

SQL filters dataset, dates and symbols using indexed columns before Pandas pivots. Groupby and NumPy operations replace row-wise arithmetic. A time loop is retained for path-dependent holdings because each period depends on previous holdings; the loop operates across an asset vector. Rolling maximum drawdown is currently O(T×window), appropriate for the bounded research demo; profile and replace with an efficient rolling algorithm before large-universe deployment. JSON storage duplicates some calculated paths to favor auditability; object storage and normalized run metrics are sensible next steps at scale.
