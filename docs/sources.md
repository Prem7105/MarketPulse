# Primary implementation references

These sources informed framework integration and regression covariance conventions. Project formulas and conventions are documented independently in mathematics.md, including choices that differ between vendors.

- FastAPI SQL databases: https://fastapi.tiangolo.com/tutorial/sql-databases/
- statsmodels HAC covariance: https://www.statsmodels.org/dev/generated/statsmodels.stats.sandwich_covariance.cov_hac.html
- SQLAlchemy: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/en/latest/
- Streamlit testing: https://docs.streamlit.io/develop/api-reference/app-testing

Use requirements.lock for the resolved dependencies rather than assuming the documentation's latest version is the installed version.
