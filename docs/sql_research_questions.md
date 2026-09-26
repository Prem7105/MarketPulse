# PostgreSQL research exercises

Use SQLAlchemy `text(query)` with bound `dataset`, `portfolio` or `asset` parameters; never substitute untrusted strings. Replace named parameters with psql variables when using psql. Queries with window returns assume complete consistently spaced daily observations.

## 1. List the asset universe

```sql
SELECT symbol, name, currency FROM assets ORDER BY symbol;
```

Asset metadata is distinct from observations.

## 2. Filter USD assets

```sql
SELECT symbol FROM assets WHERE currency = 'USD' ORDER BY symbol;
```

String literals use single quotes.

## 3. Show latest datasets

```sql
SELECT id, source, row_count, created_at FROM datasets ORDER BY created_at DESC LIMIT 10;
```

Ingestion time is different from market observation date.

## 4. Select a date interval

```sql
SELECT * FROM asset_prices WHERE dataset_id = :dataset AND date BETWEEN DATE '2023-01-01' AND DATE '2023-12-31';
```

Always specify a version before querying price history.

## 5. Join prices with tickers

```sql
SELECT a.symbol, p.date, p.adjusted_close FROM asset_prices p JOIN assets a ON a.id=p.asset_id WHERE p.dataset_id=:dataset ORDER BY a.symbol,p.date;
```

The FK avoids storing ticker strings on every observation.

## 6. Count observations per asset

```sql
SELECT asset_id, COUNT(*) AS n FROM asset_prices WHERE dataset_id=:dataset GROUP BY asset_id ORDER BY n DESC;
```

Counts reveal differing histories, not their causes.

## 7. Find short histories with HAVING

```sql
SELECT asset_id, COUNT(*) AS n FROM asset_prices WHERE dataset_id=:dataset GROUP BY asset_id HAVING COUNT(*) < 252;
```

HAVING filters groups after aggregation.

## 8. Find assets absent from a dataset

```sql
SELECT a.symbol FROM assets a LEFT JOIN asset_prices p ON p.asset_id=a.id AND p.dataset_id=:dataset WHERE p.id IS NULL;
```

Dataset filter belongs in ON to preserve unmatched assets.

## 9. Get daily lagged prices

```sql
SELECT asset_id,date,adjusted_close,LAG(adjusted_close) OVER(PARTITION BY asset_id ORDER BY date) AS previous FROM asset_prices WHERE dataset_id=:dataset;
```

LAG returns the preceding observed price; gaps still require quality checks.

## 10. Calculate daily simple returns

```sql
WITH p AS (SELECT asset_id,date,adjusted_close,LAG(adjusted_close) OVER(PARTITION BY asset_id ORDER BY date) AS previous FROM asset_prices WHERE dataset_id=:dataset) SELECT asset_id,date,adjusted_close/NULLIF(previous,0)-1 AS return FROM p ORDER BY asset_id,date;
```

NULLIF prevents division by zero. First return remains null.

## 11. Inspect next observation with LEAD

```sql
SELECT asset_id,date,LEAD(date) OVER(PARTITION BY asset_id ORDER BY date) AS next_date FROM asset_prices WHERE dataset_id=:dataset;
```

LEAD is for diagnostics here, never a historical trading signal.

## 12. Find latest row per asset

```sql
WITH ranked AS (SELECT *,ROW_NUMBER() OVER(PARTITION BY asset_id ORDER BY date DESC) AS rn FROM asset_prices WHERE dataset_id=:dataset) SELECT asset_id,date,adjusted_close FROM ranked WHERE rn=1;
```

ROW_NUMBER selects one deterministic date in this unique-key table.

## 13. Find duplicates

```sql
SELECT dataset_id,asset_id,date,COUNT(*) FROM asset_prices GROUP BY dataset_id,asset_id,date HAVING COUNT(*)>1;
```

Should return zero rows because of the unique constraint.

## 14. Detect missing weekdays

```sql
WITH bounds AS (SELECT asset_id,MIN(date) lo,MAX(date) hi FROM asset_prices WHERE dataset_id=:dataset GROUP BY asset_id), expected AS (SELECT b.asset_id,d::date AS date FROM bounds b CROSS JOIN LATERAL generate_series(b.lo,b.hi,INTERVAL '1 day') d WHERE EXTRACT(ISODOW FROM d)<6) SELECT e.* FROM expected e LEFT JOIN asset_prices p ON p.asset_id=e.asset_id AND p.date=e.date AND p.dataset_id=:dataset WHERE p.id IS NULL;
```

This flags exchange holidays too; a proper calendar is a separate dataset.

## 15. Calculate a 20-observation moving average

```sql
SELECT asset_id,date,AVG(adjusted_close) OVER(PARTITION BY asset_id ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma20,COUNT(*) OVER(PARTITION BY asset_id ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS n FROM asset_prices WHERE dataset_id=:dataset;
```

Require n=20 before using a full-window value.

## 16. Calculate rolling return volatility

```sql
WITH r AS (SELECT asset_id,date,adjusted_close/LAG(adjusted_close) OVER(PARTITION BY asset_id ORDER BY date)-1 AS ret FROM asset_prices WHERE dataset_id=:dataset) SELECT asset_id,date,STDDEV_SAMP(ret) OVER(PARTITION BY asset_id ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)*SQRT(252) AS vol20 FROM r;
```

This query assumes daily data and N=252; require complete window counts.

## 17. Rank assets by observation count

```sql
WITH n AS (SELECT asset_id,COUNT(*) observations FROM asset_prices WHERE dataset_id=:dataset GROUP BY asset_id) SELECT *,RANK() OVER(ORDER BY observations DESC) FROM n;
```

RANK leaves gaps after ties; it is not an investment ranking.

## 18. Use DENSE_RANK

```sql
WITH n AS (SELECT asset_id,COUNT(*) observations FROM asset_prices WHERE dataset_id=:dataset GROUP BY asset_id) SELECT *,DENSE_RANK() OVER(ORDER BY observations DESC) FROM n;
```

DENSE_RANK does not leave gaps after ties.

## 19. Find assets above average history length

```sql
WITH n AS (SELECT asset_id,COUNT(*) observations FROM asset_prices WHERE dataset_id=:dataset GROUP BY asset_id) SELECT * FROM n WHERE observations>(SELECT AVG(observations) FROM n);
```

CTE makes the aggregate reusable.

## 20. Query a portfolio with its weights

```sql
SELECT p.id,p.name,a.symbol,h.weight FROM portfolios p JOIN portfolio_positions h ON h.portfolio_id=p.id JOIN assets a ON a.id=h.asset_id WHERE p.id=:portfolio;
```

These are initial target weights, not daily drifted weights.

## 21. Audit portfolio weight sums

```sql
SELECT portfolio_id,SUM(weight) AS total FROM portfolio_positions GROUP BY portfolio_id HAVING ABS(SUM(weight)-1)>0.00000001;
```

Cross-row aggregate validation is enforced in application logic.

## 22. Calculate portfolio sector-free weighted one-period return

```sql
WITH r AS (SELECT asset_id,date,adjusted_close/LAG(adjusted_close) OVER(PARTITION BY asset_id ORDER BY date)-1 AS ret FROM asset_prices WHERE dataset_id=:dataset) SELECT r.date,SUM(h.weight*r.ret) AS target_weight_return FROM r JOIN portfolio_positions h ON h.asset_id=r.asset_id WHERE h.portfolio_id=:portfolio GROUP BY r.date ORDER BY r.date;
```

Only valid for target weights, no missing assets, no costs/cash; this is not buy-and-hold drift.

## 23. Summarize backtest trading

```sql
SELECT backtest_id,SUM(turnover) AS traded_exposure,SUM(cost) AS sum_cost_fractions,AVG(net) AS mean_net,STDDEV_SAMP(net) AS sd_net FROM backtest_returns GROUP BY backtest_id;
```

Summed cost fractions are not total compounded wealth drag.

## 24. Compound net backtest return

```sql
SELECT backtest_id,EXP(SUM(LN(1+net)))-1 AS total_return FROM backtest_returns WHERE net>-1 GROUP BY backtest_id;
```

Only use after verifying all returns exceed -1; do not silently exclude bankrupt periods.

## 25. Compute historical 95% VaR

```sql
SELECT backtest_id,percentile_cont(0.95) WITHIN GROUP(ORDER BY -net) AS var95 FROM backtest_returns GROUP BY backtest_id;
```

Signed losses and interpolation match the Python convention.

## 26. Compute historical ES

```sql
WITH q AS (SELECT backtest_id,percentile_cont(.95) WITHIN GROUP(ORDER BY -net) AS threshold FROM backtest_returns GROUP BY backtest_id) SELECT r.backtest_id,AVG(-r.net) AS es95 FROM backtest_returns r JOIN q USING(backtest_id) WHERE -r.net>=q.threshold GROUP BY r.backtest_id;
```

Boundary ties are included.

## 27. Inspect research parameter JSON

```sql
SELECT id,kind,parameters->>'benchmark' AS benchmark,methodology FROM research_runs ORDER BY created_at DESC;
```

PostgreSQL JSON operators expose audit parameters.

## 28. Find all runs on a dataset

```sql
SELECT id,kind,created_at,methodology FROM research_runs WHERE dataset_id=:dataset ORDER BY created_at;
```

A source revision is a new dataset, not a silent overwrite.

## 29. Join factor observations

```sql
SELECT f.name,r.date,r.value FROM factor_returns r JOIN factors f ON f.id=r.factor_id WHERE r.dataset_id=:dataset ORDER BY r.date,f.name;
```

Daily factor return units must be decimals; market factor is excess return.

## 30. Count factor coverage

```sql
SELECT f.name,COUNT(*) AS n,MIN(r.date),MAX(r.date) FROM factor_returns r JOIN factors f ON f.id=r.factor_id WHERE r.dataset_id=:dataset GROUP BY f.name;
```

Matching counts alone do not prove matching dates.

## 31. Calculate SQL drawdown

```sql
WITH wealth AS (SELECT backtest_id,date,EXP(SUM(LN(1+net)) OVER(PARTITION BY backtest_id ORDER BY date)) AS w FROM backtest_returns), peaks AS (SELECT *,GREATEST(1,MAX(w) OVER(PARTITION BY backtest_id ORDER BY date)) AS peak FROM wealth) SELECT backtest_id,date,w/peak-1 AS drawdown FROM peaks ORDER BY backtest_id,date;
```

Assumes every net return exceeds -1. Initial peak 1 captures first-period losses.

## 32. Inspect a query plan

```sql
EXPLAIN (ANALYZE,BUFFERS) SELECT date,adjusted_close FROM asset_prices WHERE dataset_id=:dataset AND asset_id=:asset AND date>=DATE '2023-01-01' ORDER BY date;
```

ANALYZE executes the query. Compare estimated/actual rows, scans and buffer reads before adding indexes.