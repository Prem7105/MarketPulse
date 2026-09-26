# Five-minute technical deep dive

## 0:00–0:45 — Question and boundary

Explain that the platform measures realized risk/performance and supports investigation. State explicitly that the bundled series and six factors are synthetic. The project is designed around correctness and reproducibility rather than a BUY prediction. Open Overview and show dataset source/date/hash.

## 0:45–1:30 — Data and storage

Show the provider contract and quality report. Invalid dates/nonpositive prices/impossible OHLC are rejected; extreme valid moves are retained and flagged. Normalized symbols resolve formatting differences. Versioned dataset/asset/date uniqueness separates corrections from previous snapshots. Explain why transactions and FKs matter, and why matching row counts does not prove matching calendars.

## 1:30–2:30 — Numerical reasoning

Write 100→110→99 and derive −1% compounded return. Explain sample volatility and matching risk-free frequency in Sharpe. Draw initial wealth one and a first-period loss to demonstrate the drawdown edge case. Use covariance to show why average asset volatility is not portfolio volatility. Explain signed historical loss VaR and sparse-tail ES uncertainty.

## 2:30–3:30 — Portfolio and strategy integrity

Show drifting weights between rebalances and wealth-linked attribution. Explain the execution timeline: signal at t, close execution t+1, first return ending t+2. Fixed allocations need no signal. Discuss entry costs, risky turnover and cash. Open the perturbation test: modifying future prices must leave earlier results unchanged. State that this test does not cure survivorship bias or a revised historical data source.

## 3:30–4:15 — Factors and inference

Show OLS excess-return regression, factor betas, R², HAC uncertainty and confidence intervals. Explain rank-deficient input rejection. Distinguish association from causation and arithmetic annual alpha from CAGR. The fictional factors validate plumbing and known coefficient recovery, not an empirical factor discovery.

## 4:15–5:00 — Architecture, verification and next work

Show pure research modules, services, validated API and Streamlit client. Review the test audit honestly, including deployment checks that could not run in the build environment. Explain that a local functional application still needs authentication/authorization, rate limits, TLS and operational monitoring before public production use. Prioritize point-in-time data and walk-forward research over adding infrastructure or prediction models prematurely.
