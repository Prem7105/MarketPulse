# MarketPulse interview guide

Answers describe this implementation, including its limits. Practice explaining the formula and one counterexample, not memorizing slogans.

## 1. [Architecture] What problem does MarketPulse solve?

It makes an asset/portfolio research workflow inspectable and repeatable: validate a dataset, quantify performance and risk, explain exposures, and save the assumptions and results. It does not forecast profitable trades.

## 2. [Architecture] Why PostgreSQL instead of just CSV?

CSV is a useful interchange format but does not enforce foreign keys, transactions or unique observation keys. PostgreSQL gives consistent snapshots, indexed filtering and shared access; CSV remains a provider boundary.

## 3. [Architecture] Why separate research from API code?

Pure functions can be tested on hand-calculated vectors without HTTP or a database. Services orchestrate persistence and the API validates requests; Streamlit consumes the same results.

## 4. [Architecture] Why FastAPI?

Pydantic validation and generated OpenAPI make parameters explicit. The calculation services remain synchronous CPU work; an async endpoint alone would not make NumPy faster.

## 5. [Architecture] Why Streamlit?

It delivers interactive research controls and Plotly visualizations quickly in Python. The trade-off is rerun state and less UI flexibility than a custom frontend.

## 6. [Python] Why Pandas?

Labeled indexes simplify date alignment, pivots and rolling windows. Alignment is powerful but can silently introduce NaNs, so MarketPulse validates exact calendars before calculating returns.

## 7. [Python] Why NumPy?

Portfolio covariance and factor design operations benefit from contiguous arrays and vectorized arithmetic. Column order must be fixed before converting labeled data to arrays.

## 8. [Python] What is vectorization?

Apply an array operation to many values rather than interpreting a Python operation for each row. For example prices.pct_change(fill_method=None) calculates returns while preserving labels; vectorization can still allocate large temporaries.

## 9. [Python] When is a loop appropriate?

Holdings drift depends on the previous period, so simulation loops over time and vectorizes across assets. Removing the loop at the expense of correct state transitions is not an optimization.

## 10. [Python] How would you reduce memory?

Filter dates and assets in SQL, select only needed columns, process ingestion in chunks and avoid repeated copies of large panels. Measure memory before changing numeric precision.

## 11. [Python] Why type hints and Pydantic?

Hints help tools and readers; Pydantic enforces runtime constraints at the API boundary. The numerical layer still checks shape, dates and finite values because it can be called without the API.

## 12. [SQL] What uniquely identifies a price?

The dataset version, asset ID and date together. Different source revisions can coexist without changing earlier research; a duplicate inside one dataset is rejected.

## 13. [SQL] What does a foreign key prevent?

It prevents observations referring to nonexistent assets or datasets. Application validation still checks economic constraints that cannot be expressed as a simple reference.

## 14. [SQL] Why use a transaction during ingestion?

A dataset and its prices/factors must be committed together. If a later insert fails, rollback prevents a partially loaded research snapshot.

## 15. [SQL] Which indexes matter?

Composite unique dataset/asset/date keys support range access within a dataset and asset. Date and dataset indexes support common filters. EXPLAIN ANALYZE should decide further indexes; indexes cost write time and disk.

## 16. [SQL] When is SQL better than Pandas?

Use SQL to filter, join or aggregate data too large to fit comfortably in memory. Use Pandas for a bounded aligned panel and transparent research calculations.

## 17. [Finance] How are simple and log returns different?

Simple returns compound multiplicatively across time and combine linearly across contemporaneous portfolio weights. Log returns add across time for one asset but cannot generally be weight-averaged into portfolio simple return.

## 18. [Finance] How do you calculate annualized volatility?

Sample standard deviation of daily returns times sqrt(N), with N configurable. Independence/weak dependence and a stable horizon are assumptions; serial correlation can invalidate the square-root rule.

## 19. [Finance] How do you calculate Sharpe?

Convert annual risk-free to the matching daily rate, subtract it, divide mean excess return by sample excess-return standard deviation and multiply by sqrt(N). Do not subtract an annual rate directly from a daily mean.

## 20. [Finance] What happens when volatility is zero?

Sharpe is undefined and serialized as null. The platform does not replace an undefined ratio with infinity, zero or a winning rank.

## 21. [Finance] What does Sortino change?

It replaces total dispersion with root-mean-square shortfalls below the selected target. Our denominator averages shortfalls over all observations; other conventions can produce different values.

## 22. [Finance] Why is compounding important?

A gain of 10% followed by a loss of 10% gives 1.1×.9−1=−1%. Summing returns loses this wealth effect.

## 23. [Risk] What is maximum drawdown?

The worst relative loss from a running wealth peak. Initial wealth one must be included, or the first loss is hidden. It depends on the ordering of returns, not only their distribution.

## 24. [Risk] How do you measure drawdown duration?

Count consecutive underwater observations until recovery. The output distinguishes an unrecovered episode; duration is trading observations, not elapsed calendar days.

## 25. [Risk] What is VaR?

A selected quantile of loss over a specified horizon. Our historical 95% VaR uses the empirical one-period loss distribution and linear interpolation. It is not the maximum possible loss.

## 26. [Risk] Why expected shortfall?

It averages sampled losses beyond VaR and therefore describes severity in the tail. Its estimate can be unstable when the tail has very few observations.

## 27. [Portfolio] How do you calculate portfolio volatility?

Use the covariance matrix: sqrt(w transpose Sigma w). An average of individual volatilities ignores cross-asset co-movement.

## 28. [Portfolio] Why do we need covariance?

Portfolio positions experience returns together. Covariance captures whether one tends to offset or amplify another; diversification cannot be inferred from individual volatilities alone.

## 29. [Portfolio] Do weights stay constant in buy-and-hold?

No. Winners become larger positions. Our simulation drifts weights after every return; constant weights imply repeated trading.

## 30. [Portfolio] What is component risk contribution?

For volatility, weight_i times (Sigma w)_i divided by portfolio volatility. Components sum to total volatility, assuming the same covariance and annualization conventions.

## 31. [Benchmark] What is beta?

Covariance with benchmark divided by benchmark variance. It measures linear sensitivity, not total risk or causation; a zero-variance benchmark makes it undefined.

## 32. [Benchmark] What is alpha?

The intercept after accounting for selected factor exposures and risk-free return. It can reflect missing variables, selected periods or noise, so a positive intercept is not automatically manager skill.

## 33. [Benchmark] What is tracking error?

Annualized standard deviation of portfolio-minus-benchmark daily returns. It measures variability of relative performance, not average underperformance.

## 34. [Benchmark] What is information ratio?

Mean active return over standard deviation of active return, consistently annualized. Identical benchmark and portfolio returns produce zero denominator and an undefined ratio.

## 35. [Statistics] What does R-squared mean?

The fraction of in-sample outcome variation explained by the regression relative to an intercept-only baseline. A high R-squared does not establish forecasting power or causation.

## 36. [Statistics] What does a p-value tell you?

Under the specified null model and assumptions, how incompatible the observed statistic is with that null. It is not the probability that the null is true or that a trade will succeed.

## 37. [Statistics] Why HAC errors?

Daily regression residuals may be heteroskedastic and serially dependent. HAC changes estimated uncertainty while preserving OLS coefficients, but remains an asymptotic procedure and does not fix biased explanatory variables.

## 38. [Statistics] Why might financial returns be non-normal?

Skew, fat tails, volatility clustering and regime changes can violate a normal model. QQ plots and Jarque–Bera are diagnostics, not definitive distribution selection tools.

## 39. [Factors] What is factor exposure?

A coefficient linking the asset excess return to a defined factor return conditional on other included factors. Units, construction, date alignment and market excess-return convention matter.

## 40. [Factors] What does an insignificant factor coefficient mean?

The sample and model do not precisely distinguish that coefficient from zero at a chosen threshold. It does not prove the economic exposure is absent; intervals, sample size and collinearity matter.

## 41. [Factors] How do you distinguish correlation from causation?

Correlation and regression describe conditional associations. Causality requires a credible identification design and assumptions beyond this observational price model.

## 42. [Factors] How do you handle collinearity?

Reject exactly rank-deficient designs. For near-collinearity, inspect condition numbers and confidence intervals, reconsider redundant factors, and avoid interpreting unstable individual coefficients.

## 43. [Attribution] How do security contributions add up?

One period uses beginning weight times return. Across periods, prior wealth links contributions; cash and cost are included so the total reconciles to terminal net wealth minus initial wealth.

## 44. [Attribution] What is Brinson attribution?

A benchmark-relative decomposition into allocation, selection and interaction over aligned categories. Our implementation is single-period Brinson–Fachler; dashboard cumulative attribution uses security-level wealth linking.

## 45. [Backtesting] How can look-ahead bias occur?

A close-based signal can accidentally trade at the same already-observed close, or a rolling estimator can use future rows. We delay derived signals two price rows and test that changed future prices do not alter earlier results.

## 46. [Backtesting] What is survivorship bias?

Evaluating only assets that survive to today omits failures and delistings. A fixed current universe is not point-in-time historical membership; our delay protection does not solve this.

## 47. [Backtesting] What is your execution timeline?

Observe close t, execute at close t+1, earn the close-to-close return ending t+2. Predetermined fixed allocations can start at the initial sample close because they do not need a price-derived signal.

## 48. [Backtesting] How are transaction costs applied?

Sum absolute risky weight changes times bps, then scale wealth before earning the holding return. Entry is charged, no final liquidation is assumed, and the model excludes liquidity and market impact.

## 49. [Backtesting] How would you validate a strategy properly?

Pre-register choices, use chronological development and held-out evaluation or walk-forward testing, track every attempted variant, include realistic costs and use point-in-time data. This project does not claim that validation has already occurred.

## 50. [Quality] How do you handle missing data?

Report missing weekdays as a heuristic, reject invalid rows and require matching complete price calendars for analysis. No automatic forward filling; obtain an exchange calendar and resolve source gaps explicitly.

## 51. [Quality] What happens to an extreme price move?

Valid extreme adjusted returns are flagged and retained. An extreme move can be real; deletion based on appearance would distort tails. Inspect corporate actions and source before choosing a new dataset.

## 52. [Reproducibility] How can another researcher repeat a run?

Use the dataset ID, parameter JSON, methodology version, sample generator seed and dependency lock. Stored results and immutable application imports preserve the original analysis inputs.

## 53. [System design] How would you scale this system?

Profile first, push filtering to SQL, partition large histories, paginate results, cache immutable computations and move long jobs to a queue only when needed. Preserve source/version identity across those changes.

## 54. [System design] What is not production ready?

Public multi-user identity and authorization, rate/request-size enforcement, monitored deployment, licensed feeds and operational recovery procedures are deferred. Local functional correctness is distinct from production operations.

## 55. [Trade-offs] Why not add deep learning?

The research question requires explainable performance and risk measurement. A prediction model would introduce different validation demands without resolving missing data, execution realism or statistical bias.

## 56. [Optimization] How would you investigate a slow Pandas function?

Profile representative data, separate database/I/O and numerical time, inspect repeated copies and Python apply calls, then compare optimized outputs with the original on edge cases. Benchmark evidence is more useful than blanket vectorization claims.