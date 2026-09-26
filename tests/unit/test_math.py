import numpy as np
import pandas as pd
import pytest

from app.research.attribution import brinson, linked_contribution
from app.research.backtesting import STRATEGIES, backtest
from app.research.drawdown import drawdown, episodes
from app.research.factors import regress
from app.research.portfolio import portfolio, validate_weights
from app.research.returns import equity, log_returns, period_returns, simple_returns
from app.research.risk import covariance_risk, metrics
from app.research.rolling import rolling_metrics
from app.research.statistics import diagnostics


def series(values):
    return pd.Series(values, index=pd.bdate_range("2024-01-01", periods=len(values)))


@pytest.mark.parametrize(
    "prices,expected",
    [([100, 110, 99], [0.1, -0.1]), ([10, 10, 10], [0, 0]), ([10, 5, 10], [-0.5, 1])],
)
def test_returns(prices, expected):
    r = simple_returns(series(prices))
    np.testing.assert_allclose(r, expected, atol=1e-14)
    np.testing.assert_allclose(log_returns(series(prices)), np.log1p(expected), atol=1e-14)
    assert equity(r).iloc[-1] == pytest.approx(prices[-1] / prices[0])


@pytest.mark.parametrize("values", [[], [1], [1, np.nan, 3], [1, 0, 3], [1, -1, 3], [1, np.inf, 3]])
def test_invalid_prices(values):
    with pytest.raises(ValueError):
        simple_returns(series(values))


def test_bad_index():
    with pytest.raises(ValueError):
        simple_returns(pd.Series([1, 2, 3], index=[1, 1, 2]))


def test_hand_metrics():
    r = series([0.1, -0.1, 0.05, -0.02])
    result = metrics(r, periods=4)
    wealth = 1.1 * 0.9 * 1.05 * 0.98
    expected = {
        "cumulative_return": wealth - 1,
        "annualized_return": wealth - 1,
        "annualized_volatility": np.std(r, ddof=1) * 2,
        "sharpe": np.mean(r) / np.std(r, ddof=1) * 2,
        "sortino": np.mean(r) / np.sqrt((0.1**2 + 0.02**2) / 4) * 2,
        "downside_deviation": np.sqrt((0.1**2 + 0.02**2) / 4) * 2,
        "max_drawdown": -0.1,
        "calmar": (wealth - 1) / 0.1,
        "var": np.quantile(-r, 0.95),
        "cvar": 0.1,
    }
    for key, value in expected.items():
        assert result[key] == pytest.approx(value)


@pytest.mark.parametrize("annual_rf", [0, 0.03, -0.01])
def test_sharpe_rf(annual_rf):
    r = series([0.01, 0.02, -0.01, 0.005])
    rf = (1 + annual_rf) ** (1 / 252) - 1
    assert metrics(r, annual_rf=annual_rf)["sharpe"] == pytest.approx(
        (r - rf).mean() / (r - rf).std() * np.sqrt(252)
    )


def test_zero_volatility():
    result = metrics(series([0, 0, 0]), series([0, 0, 0]))
    for key in [
        "sharpe",
        "sortino",
        "calmar",
        "beta",
        "information_ratio",
        "alpha",
        "upside_capture",
        "downside_capture",
    ]:
        assert result[key] is None
    assert result["max_drawdown"] == result["var"] == 0


def test_initial_drawdown_and_recovery():
    r = series([-0.2, 0.25, -0.1, 0])
    np.testing.assert_allclose(drawdown(r), [-0.2, 0, -0.1, -0.1], atol=1e-14)
    dd = episodes(r)
    assert dd[0]["peak"] is None
    assert dd[0]["recovery"] == r.index[1]
    assert dd[0]["duration"] == 1
    assert dd[1]["recovered"] is False
    assert dd[1]["duration"] == 2


def test_benchmark():
    b = series([0.01, -0.02, 0.03, -0.01, 0.005])
    r = 0.001 + 1.5 * b
    result = metrics(r, b)
    assert result["beta"] == pytest.approx(1.5)
    assert result["alpha"] == pytest.approx(0.252)
    assert result["tracking_error"] == pytest.approx((r - b).std() * np.sqrt(252))
    assert result["information_ratio"] == pytest.approx(
        (r - b).mean() / (r - b).std() * np.sqrt(252)
    )
    assert result["upside_capture"] is not None
    with pytest.raises(ValueError):
        metrics(r, b.shift(1))


def test_covariance():
    r = pd.DataFrame({"a": series([0.1, -0.1, 0.02]), "b": series([0.04, -0.03, 0.01])})
    w = np.array([0.6, 0.4])
    result = covariance_risk(r, w, 12)
    assert result["variance"] == pytest.approx(w @ r.cov().to_numpy() @ w * 12)
    assert sum(result["risk_contribution"].values()) == pytest.approx(result["volatility"])


def test_factor_recovery():
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2020-01-01", periods=400)
    f = pd.DataFrame(rng.normal(0, 0.01, (400, 2)), index=index, columns=["market", "value"])
    r = (
        0.0002
        + 1.2 * f.market
        - 0.5 * f.value
        + pd.Series(rng.normal(0, 0.00005, 400), index=index)
    )
    result = regress(r, f)
    assert result["coefficients"]["market"]["beta"] == pytest.approx(1.2, abs=0.002)
    assert result["coefficients"]["value"]["beta"] == pytest.approx(-0.5, abs=0.002)
    assert result["alpha_daily"] == pytest.approx(0.0002, abs=0.00001)
    assert result["r_squared"] > 0.99
    for rf, ff in [(r, f.assign(duplicate=f.market)), (r, f.iloc[1:]), (r.iloc[:5], f.iloc[:5])]:
        with pytest.raises(ValueError):
            regress(rf, ff)


def test_portfolio_drift():
    prices = pd.DataFrame(
        {"a": [100, 200, 200], "b": [100, 100, 200]}, index=pd.bdate_range("2024-01-01", periods=3)
    )
    hold = portfolio(prices, {"a": 0.5, "b": 0.5}, frequency="none")
    daily = portfolio(prices, {"a": 0.5, "b": 0.5}, frequency="daily")
    assert hold["path"].wealth.iloc[-1] == pytest.approx(2.0)
    assert daily["path"].wealth.iloc[-1] == pytest.approx(2.25)
    assert hold["weights"].iloc[1].a == pytest.approx(2 / 3)
    assert linked_contribution(hold).sum() == pytest.approx(1.0)


def test_costs_and_linking():
    prices = pd.DataFrame(
        {"a": [100, 110, 99], "b": [100, 100, 110]}, index=pd.bdate_range("2024-01-01", periods=3)
    )
    sim = portfolio(prices, {"a": 0.5, "b": 0.5}, frequency="none", cost_bps=100)
    assert sim["path"].cost.iloc[0] == pytest.approx(0.01)
    assert sim["path"].net.iloc[0] == pytest.approx(0.99 * 1.05 - 1)
    assert sim["path"].wealth.iloc[-1] == pytest.approx(0.99 * (0.5 * 0.99 + 0.5 * 1.1))
    assert linked_contribution(sim).sum() == pytest.approx(sim["path"].wealth.iloc[-1] - 1)


@pytest.mark.parametrize(
    "weights", [{"a": 0.2, "b": 0.2}, {"a": -0.1, "b": 1.1}, {"a": float("nan"), "b": 1}, {"a": 1}]
)
def test_invalid_weights(weights):
    with pytest.raises(ValueError):
        validate_weights(weights, ["a", "b"])


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_no_future_leak(strategy):
    rng = np.random.default_rng(9)
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, (100, 2)), axis=0)),
        index=pd.bdate_range("2024-01-01", periods=100),
        columns=["a", "b"],
    )
    changed = prices.copy()
    changed.iloc[70:] *= 5
    a = backtest(prices, strategy, lookback=10, frequency="daily")
    b = backtest(changed, strategy, lookback=10, frequency="daily")
    pd.testing.assert_frame_equal(a["path"].iloc[:69], b["path"].iloc[:69])
    assert (a["weights"].sum(axis=1) <= 1 + 1e-10).all()


def test_signal_two_bar_delay():
    prices = pd.DataFrame(
        {"a": [100, 100, 110, 110, 110, 110]}, index=pd.bdate_range("2024-01-01", periods=6)
    )
    sim = backtest(prices, "momentum", lookback=2, frequency="daily", cost_bps=0)
    assert sim["weights"].iloc[:3].a.eq(0).all()
    assert sim["weights"].iloc[3].a == 1


def test_brinson():
    wp = pd.Series([0.6, 0.4], index=["tech", "other"])
    wb = pd.Series([0.4, 0.6], index=wp.index)
    rp = pd.Series([0.1, 0.02], index=wp.index)
    rb = pd.Series([0.08, 0.03], index=wp.index)
    result = brinson(wp, wb, rp, rb)
    assert result.active_contribution.sum() == pytest.approx((wp * rp).sum() - (wb * rb).sum())


def test_rolling_and_stats():
    r = series([0.01, -0.02, 0.03, 0.01, -0.01, 0.01, 0.04, -0.02, 0.03, 0.005])
    rolling = rolling_metrics(r, r, 3)
    assert rolling["return"].iloc[2] == pytest.approx(1.01 * 0.98 * 1.03 - 1)
    assert rolling.beta.dropna().iloc[-1] == pytest.approx(1)
    assert rolling.correlation.dropna().iloc[-1] == pytest.approx(1)
    d = diagnostics(r)
    assert d["mean"] == pytest.approx(r.mean())
    assert d["variance"] == pytest.approx(r.var())
    assert d["jarque_bera"]["p_value"] >= 0
    assert diagnostics(series([0, 0, 0]))["skew"] is None
    assert len(period_returns(r)["weekly"]) >= 2
