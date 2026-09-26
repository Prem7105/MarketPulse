from app.research.attribution import linked_contribution
from app.research.drawdown import drawdown, episodes
from app.research.portfolio import portfolio
from app.research.returns import simple_returns
from app.research.risk import covariance_risk, metrics
from app.services.research import clean_json, records


def analyze_portfolio(
    panel,
    symbols,
    weights,
    benchmark=None,
    frequency="monthly",
    cost_bps=0,
    periods=252,
    annual_rf=0,
    confidence=0.95,
):
    simulation = portfolio(panel[symbols], weights, frequency, cost_bps, annual_rf, periods)
    r = simulation["path"].net
    b = simple_returns(panel)[benchmark] if benchmark else None
    result = {
        "metrics": metrics(r, b, periods, annual_rf, confidence),
        "path": records(simulation["path"]),
        "weights": records(simulation["weights"]),
        "attribution": clean_json(linked_contribution(simulation).to_dict()),
        "drawdown": records(drawdown(r)),
        "drawdown_table": episodes(r),
        "target_weight_risk": covariance_risk(
            simple_returns(panel[symbols]), [weights[s] for s in symbols], periods
        ),
        "correlation": clean_json(simple_returns(panel[symbols]).corr().to_dict()),
    }
    if b is not None:
        result["benchmark_equity"] = records((1 + b).cumprod())
        # Wealth-linked portfolio less benchmark contribution reconciles to active terminal wealth.
        active = dict(result["attribution"])
        active["benchmark"] = -float((1 + b).prod() - 1)
        result["active_contribution"] = active
    return result
