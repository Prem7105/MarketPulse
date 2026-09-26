# Python research interview examples

## Lists, tuples, sets and dictionaries

A list preserves ordered asset selection: `symbols=['AAPL','MSFT']`. A tuple can represent an immutable observation key `(dataset_id,asset_id,date)`. A set finds missing symbols, `set(requested)-set(observed)`, but loses ordering. A dict maps tickers to target weights. Before NumPy conversion, always construct `[weights[s] for s in panel.columns]`; dict insertion order alone does not prove alignment with a DataFrame.

## Generators and iterators

An iterator yields observations on demand; a generator implements that protocol with `yield`. For large provider files use `pd.read_csv(path,chunksize=100_000)` to iterate over DataFrame chunks. Our current CSV provider reads the bounded file and persistence inserts batches. True streaming validation across chunk boundaries would also need duplicate detection and prior-price state across chunks.

## Context managers

`with SessionLocal() as db:` guarantees session cleanup. It does not automatically commit successful work; services choose transaction boundaries explicitly and rollback failed ingestion. A context manager's `__exit__` runs even if an exception occurs.

## Decorators

FastAPI route decorators register endpoint functions. `@lru_cache` caches the environment Settings instance; changing environment variables after it is loaded will not refresh it automatically. Streamlit's `@st.cache_data` caches read responses temporarily; changing a dataset or query must change the cache key.

## Classes, protocols and dataclasses

SQLAlchemy model classes map rows and columns. A `MarketDataProvider` Protocol defines a structural contract: `.source` plus `.read()`. A future vendor provider need not inherit a concrete base class if it implements the contract. `DataQualityReport` is a dataclass with `default_factory=list`/dict; a mutable shared default would leak warnings between runs.

## Type hints and validation

Hints document shapes conceptually, but `pd.DataFrame` does not encode column names. Pydantic checks request fields at runtime; numerical functions also check finite values, dimensions and exact indexes. A float can still be NaN, so “it has the correct Python type” is insufficient validation.

## Exceptions

Raise ValueError for invalid research input, LookupError for missing resources. The HTTP boundary maps those to 422 and 404. Unexpected errors return a generic 500 and log the exception type/path without credentials or request bodies. Do not swallow every exception and return a fake zero result.

## Virtual environments and packages

Use a virtual environment so a project does not depend on accidental global packages. `pyproject.toml` declares supported version ranges; requirements.lock and requirements-dev.lock pin the resolved Python 3.12 environments. Install the project editable in development after dependencies; the Docker image installs the package normally. A reproducible dataset alone is not a fully reproducible runtime.

## Pandas alignment

Pandas aligns labels during arithmetic. `asset_returns - benchmark_returns` can introduce nulls if dates differ. MarketPulse requires exact calendars rather than allowing silent alignment. `pct_change(fill_method=None)` prevents a missing price being implicitly filled into a false zero return.

## NumPy vectorization

`w @ cov @ w` computes portfolio variance. A slow alternative is a nested Python sum over `w[i]*cov[i,j]*w[j]`; both are O(n²), but NumPy removes interpreter overhead. Vectorization changes constants, not necessarily asymptotic complexity. Test the same weights/order/dtype and compare within floating-point tolerance.

## Complexity and memory

A dense return panel is O(T×A) memory; covariance is O(A²) output, and covariance estimation broadly O(T×A²). Path simulation is O(T×A), with sequential dependence over time. The simple rolling drawdown routine is O(T×window). Do not cache unlimited full output panels in server memory.

## Views and copies

Avoid mutating a caller's DataFrame unexpectedly: ingestion starts with a copy, normalization is explicit, and targets are copied before drift. Pandas views/copy-on-write behavior can vary by version; direct assignment with `.loc` or `.iloc` is clearer than chained assignment. Read warnings instead of suppressing them indiscriminately.

## Floating point

Binary floating arithmetic is approximate. Use `np.isclose` with a chosen tolerance for weights/reconciliation. Prices are persisted with decimal precision, then calculated with float64 arrays. Exact equality is appropriate for identifiers/dates, not most computed financial values.

## Testing approach

Hand-derived values catch formula mistakes that a second copy of the implementation would miss. Property tests include future perturbation invariance, sum-of-contributions reconciliation, and no exposure above one. Integration tests check routes/persistence. SQLite success does not validate PostgreSQL dialect behavior.

## Optimization exercise

Time an identical covariance projection using a Python nested loop and `w @ cov @ w` over a moderate universe. Assert numerical agreement first, warm both paths, then use `timeit.repeat`. Report universe size, environment and elapsed time; do not invent a speedup. Profile the full research request because database reads or serialization may dominate numerical work.
