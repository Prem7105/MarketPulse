# Database dictionary

PostgreSQL is the target database; SQLite is a local test/demo fallback. Migration aa73ee260666 creates the schema. All observations are versioned by dataset. Foreign keys prevent orphaned records; aggregate portfolio weights are validated in the application.

## datasets

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | VARCHAR(64) | True | primary key;  |
| source | VARCHAR(200) | True |  |
| created_at | DATETIME | True |  |
| row_count | INTEGER | True |  |
| start | DATE | True |  |
| end | DATE | True |  |
| quality | JSON | True |  |

Constraints:

## assets

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| symbol | VARCHAR(32) | True |  |
| name | VARCHAR(120) | True |  |
| currency | VARCHAR(3) | True |  |

Constraints:

## asset_prices

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| dataset_id | VARCHAR(64) | True | datasets.id |
| asset_id | INTEGER | True | assets.id |
| date | DATE | True |  |
| open | NUMERIC(20, 8) | True |  |
| high | NUMERIC(20, 8) | True |  |
| low | NUMERIC(20, 8) | True |  |
| close | NUMERIC(20, 8) | True |  |
| adjusted_close | NUMERIC(20, 8) | True |  |

Constraints: UniqueConstraint(Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<asset_prices>, nullable=False), Column('asset_id', Integer(), ForeignKey('assets.id'), table=<asset_prices>, nullable=False), Column('date', Date(), table=<asset_prices>, nullable=False)); CheckConstraint(<sqlalchemy.sql.elements.TextClause object at 0x7f9107c32db0>, table=Table('asset_prices', MetaData(), Column('id', Integer(), table=<asset_prices>, primary_key=True, nullable=False), Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<asset_prices>, nullable=False), Column('asset_id', Integer(), ForeignKey('assets.id'), table=<asset_prices>, nullable=False), Column('date', Date(), table=<asset_prices>, nullable=False), Column('open', Numeric(precision=20, scale=8), table=<asset_prices>, nullable=False), Column('high', Numeric(precision=20, scale=8), table=<asset_prices>, nullable=False), Column('low', Numeric(precision=20, scale=8), table=<asset_prices>, nullable=False), Column('close', Numeric(precision=20, scale=8), table=<asset_prices>, nullable=False), Column('adjusted_close', Numeric(precision=20, scale=8), table=<asset_prices>, nullable=False), schema=None))

## benchmark_prices

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| dataset_id | VARCHAR(64) | True | datasets.id |
| asset_id | INTEGER | True | assets.id |
| date | DATE | True |  |
| adjusted_close | NUMERIC(20, 8) | True |  |

Constraints: UniqueConstraint(Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<benchmark_prices>, nullable=False), Column('asset_id', Integer(), ForeignKey('assets.id'), table=<benchmark_prices>, nullable=False), Column('date', Date(), table=<benchmark_prices>, nullable=False)); CheckConstraint(<sqlalchemy.sql.elements.TextClause object at 0x7f9107c33980>, table=Table('benchmark_prices', MetaData(), Column('id', Integer(), table=<benchmark_prices>, primary_key=True, nullable=False), Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<benchmark_prices>, nullable=False), Column('asset_id', Integer(), ForeignKey('assets.id'), table=<benchmark_prices>, nullable=False), Column('date', Date(), table=<benchmark_prices>, nullable=False), Column('adjusted_close', Numeric(precision=20, scale=8), table=<benchmark_prices>, nullable=False), schema=None))

## risk_free_rates

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| dataset_id | VARCHAR(64) | True | datasets.id |
| date | DATE | True |  |
| rate | FLOAT | True |  |

Constraints: UniqueConstraint(Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<risk_free_rates>, nullable=False), Column('date', Date(), table=<risk_free_rates>, nullable=False)); CheckConstraint(<sqlalchemy.sql.elements.TextClause object at 0x7f9107a94140>, table=Table('risk_free_rates', MetaData(), Column('id', Integer(), table=<risk_free_rates>, primary_key=True, nullable=False), Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<risk_free_rates>, nullable=False), Column('date', Date(), table=<risk_free_rates>, nullable=False), Column('rate', Float(), table=<risk_free_rates>, nullable=False), schema=None))

## factors

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| name | VARCHAR(64) | True |  |

Constraints: UniqueConstraint(Column('name', String(length=64), table=<factors>, nullable=False))

## factor_returns

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| dataset_id | VARCHAR(64) | True | datasets.id |
| factor_id | INTEGER | True | factors.id |
| date | DATE | True |  |
| value | FLOAT | True |  |

Constraints: UniqueConstraint(Column('dataset_id', String(length=64), ForeignKey('datasets.id'), table=<factor_returns>, nullable=False), Column('factor_id', Integer(), ForeignKey('factors.id'), table=<factor_returns>, nullable=False), Column('date', Date(), table=<factor_returns>, nullable=False))

## portfolios

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| name | VARCHAR(120) | True |  |
| dataset_id | VARCHAR(64) | True | datasets.id |
| created_at | DATETIME | True |  |

Constraints:

## portfolio_positions

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| portfolio_id | INTEGER | True | portfolios.id |
| asset_id | INTEGER | True | assets.id |
| weight | NUMERIC(18, 10) | True |  |

Constraints: UniqueConstraint(Column('portfolio_id', Integer(), ForeignKey('portfolios.id'), table=<portfolio_positions>, nullable=False), Column('asset_id', Integer(), ForeignKey('assets.id'), table=<portfolio_positions>, nullable=False)); CheckConstraint(<sqlalchemy.sql.elements.TextClause object at 0x7f9107a95e50>, table=Table('portfolio_positions', MetaData(), Column('id', Integer(), table=<portfolio_positions>, primary_key=True, nullable=False), Column('portfolio_id', Integer(), ForeignKey('portfolios.id'), table=<portfolio_positions>, nullable=False), Column('asset_id', Integer(), ForeignKey('assets.id'), table=<portfolio_positions>, nullable=False), Column('weight', Numeric(precision=18, scale=10), table=<portfolio_positions>, nullable=False), schema=None))

## research_runs

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | VARCHAR(36) | True | primary key;  |
| kind | VARCHAR(32) | True |  |
| dataset_id | VARCHAR(64) | True | datasets.id |
| parameters | JSON | True |  |
| results | JSON | True |  |
| methodology | VARCHAR(32) | True |  |
| created_at | DATETIME | True |  |

Constraints:

## analytics_results

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| run_id | VARCHAR(36) | True | research_runs.id |
| result | JSON | True |  |

Constraints:

## backtests

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| run_id | VARCHAR(36) | True | research_runs.id |
| strategy | VARCHAR(40) | True |  |
| parameters | JSON | True |  |

Constraints: UniqueConstraint(Column('run_id', String(length=36), ForeignKey('research_runs.id'), table=<backtests>, nullable=False))

## backtest_returns

| Column | Type | Required | Key / reference |
|---|---|---|---|
| id | INTEGER | True | primary key;  |
| backtest_id | INTEGER | True | backtests.id |
| date | DATE | True |  |
| gross | FLOAT | True |  |
| net | FLOAT | True |  |
| turnover | FLOAT | True |  |
| cost | FLOAT | True |  |

Constraints: UniqueConstraint(Column('backtest_id', Integer(), ForeignKey('backtests.id'), table=<backtest_returns>, nullable=False), Column('date', Date(), table=<backtest_returns>, nullable=False))
