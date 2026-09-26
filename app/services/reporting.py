import json

from app.research.backtesting import STRATEGIES, backtest
from app.research.factors import regress
from app.research.returns import simple_returns
from app.research.risk import metrics
from app.services.portfolio import analyze_portfolio
from app.services.research import clean_json, compare, factor_panel


def research_case(db, request, panel, quality, source):
    args = request
    weights = {s: 1 / len(args.symbols) for s in args.symbols}
    comparison = compare(
        panel,
        args.symbols,
        args.benchmark,
        args.periods,
        args.annual_rf,
        args.confidence,
        args.ranking,
    )
    allocation = analyze_portfolio(
        panel,
        args.symbols,
        weights,
        args.benchmark,
        periods=args.periods,
        annual_rf=args.annual_rf,
        confidence=args.confidence,
    )
    returns = simple_returns(panel)
    factors = {}
    for symbol in args.symbols:
        try:
            f, rf = factor_panel(
                db, args.dataset_id, returns.index, ["market", "size", "value", "momentum"]
            )
            factors[symbol] = regress(returns[symbol], f, rf, args.periods)
        except ValueError as exc:
            factors[symbol] = {"unavailable": str(exc)}
    strategies = {}
    for name in STRATEGIES:
        try:
            sim = backtest(
                panel[args.symbols],
                strategy=name,
                lookback=args.window,
                periods=args.periods,
                annual_rf=args.annual_rf,
            )
            strategies[name] = metrics(
                sim["path"].net,
                returns[args.benchmark] if args.benchmark else None,
                args.periods,
                args.annual_rf,
                args.confidence,
            )
        except ValueError as exc:
            strategies[name] = {"unavailable": str(exc)}
    return clean_json(
        {
            "source": source,
            "comparison": comparison,
            "portfolio": allocation,
            "factor_exposure": factors,
            "strategies": strategies,
            "data_quality": quality,
        }
    )


def render_report(run):
    result = run.results
    sections = [
        f"# MarketPulse research report\n\nRun: {run.id}\n\nDataset: {run.dataset_id}\n\nMethodology: {run.methodology}\n\nCreated: {run.created_at.isoformat()}",
        "## Executive Summary\n\nThis report compares observed return, risk, diversification and factor exposure for the selected dataset. Rankings are descriptive and depend on the chosen period. No BUY/SELL recommendation is generated.",
        f"## 1. Asset / Portfolio Overview\n\nSource: {result.get('source','See dataset metadata')}\n\nParameters:\n```json\n{json.dumps(run.parameters,indent=2)}\n```",
    ]
    mapping = [
        ("2. Historical Performance", result.get("comparison", {}).get("summary", [])),
        ("3. Risk Analysis", result.get("portfolio", {}).get("metrics", {})),
        ("4. Drawdown Analysis", result.get("portfolio", {}).get("drawdown_table", [])),
        ("5. Benchmark Comparison", result.get("portfolio", {}).get("active_contribution", {})),
        ("6. Correlation Analysis", result.get("comparison", {}).get("correlation", {})),
        ("7. Factor Exposure — statistical inference", result.get("factor_exposure", {})),
        ("8. Attribution", result.get("portfolio", {}).get("attribution", {})),
        ("9. Backtest Results", result.get("strategies", {})),
        ("10. Data Quality", result.get("data_quality", {})),
    ]
    for title, content in mapping:
        sections.append(f"## {title}\n\n```json\n{json.dumps(content,indent=2)}\n```")
    sections += [
        "## 11. Methodology — assumptions\n\nAdjusted-close simple returns; configurable periods per year; sample standard deviation; historical loss quantile VaR and conditional tail ES. Long-only monthly equal-weight portfolio with drifting holdings. Portfolio example has zero cost; strategies use 10 bps per risky dollar traded. Signals formed at close t execute at close t+1 and earn return ending t+2. Fixed allocations are predetermined. Regression uses excess returns and HAC errors. Undefined statistics are null. Attribution is linked in initial-capital units, including cash and costs.",
        "## 12. Limitations\n\nSynthetic sources are fictional examples, not real historical performance. Fixed universes may suffer survivorship bias. Closing-bar execution, constant proportional costs and no market impact are approximations. Holidays, taxes, currencies, delistings and settlement are outside this model. Factor significance is not causality; multiple testing and in-sample selection can overstate evidence. Backtests do not guarantee future returns.",
    ]
    return "\n\n".join(sections) + "\n"
