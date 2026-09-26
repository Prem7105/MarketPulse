# Two-minute project pitch

I built MarketPulse as an investment research and risk analytics workbench. The question is how a selected universe compares on return, drawdown, diversification and factor exposure, and how those characteristics change when assets are combined into a portfolio.

The workflow starts with CSV market data. I validate dates, prices, duplicate observations and OHLC consistency, then flag suspicious returns without silently deleting them. Each import becomes a versioned database snapshot. Every research run records the snapshot, assets, dates, methodology and parameters, so the result can be explained and reproduced.

The Python research layer calculates compounded returns, Sharpe and Sortino, historical VaR and expected shortfall, drawdown episodes, benchmark statistics and covariance-based portfolio risk. I also implemented factor regressions with HAC standard errors and portfolio attribution that reconciles back to actual simulated wealth.

The main engineering challenge was getting timing and accounting right. Buy-and-hold weights drift; fixed weights imply trading. Price-derived strategy signals are delayed before execution, and transaction costs and cash are included explicitly. Tests check hand-calculated examples, contribution reconciliation and whether changing future prices alters earlier results.

FastAPI exposes those calculations and Streamlit provides ten research views. The bundled prices and factors are synthetic, so I use them to demonstrate the workflow, not make claims about actual securities or profitable predictions. My next priorities are licensed point-in-time data, exchange calendars and realistic out-of-sample strategy evaluation.
