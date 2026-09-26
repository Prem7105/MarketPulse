from datetime import datetime, timezone

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.services.market_data import MarketDataError, TwelveDataProvider


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setattr(settings(), "twelvedata_api_key", SecretStr("test-secret"))


def history():
    return {
        "meta": {
            "symbol": "AAPL",
            "currency": "USD",
            "exchange_timezone": "America/New_York",
            "exchange": "NASDAQ",
        },
        "values": [
            {"datetime": d, "open": "100", "high": "102", "low": "99", "close": "101"}
            for d in ["2024-01-02", "2024-01-03", "2024-01-04"]
        ],
    }


def test_key_required(monkeypatch):
    monkeypatch.setattr(settings(), "twelvedata_api_key", SecretStr(""))
    with pytest.raises(MarketDataError, match="TWELVEDATA_API_KEY"):
        TwelveDataProvider(["AAPL"])


def test_history_header_and_adjustment(key):
    def handler(request):
        assert "test-secret" not in str(request.url)
        assert request.headers["Authorization"] == "apikey test-secret"
        assert request.url.params["adjust"] == "all"
        return httpx.Response(200, json=history())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = TwelveDataProvider(["AAPL"], client=client)
        bars = provider.read()
    assert len(bars) == 3
    assert bars.adjusted_close.eq("101").all()
    assert provider.metadata["symbols"]["AAPL"]["currency"] == "USD"


@pytest.mark.parametrize(
    "status,body",
    [
        (429, {}),
        (401, {}),
        (500, {}),
        (200, {"status": "error", "code": 429, "message": "test-secret"}),
        (200, {"status": "error", "code": 400, "message": "test-secret"}),
    ],
)
def test_errors_never_fallback_or_leak(key, status, body):
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    ) as client:
        with pytest.raises(MarketDataError) as error:
            TwelveDataProvider(["AAPL"], client=client).read()
    assert "test-secret" not in str(error.value)


def test_exclude_current_day(key):
    from zoneinfo import ZoneInfo

    data = history()
    data["values"].append(
        {
            **data["values"][0],
            "datetime": datetime.now(ZoneInfo("America/New_York")).date().isoformat(),
        }
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        assert len(TwelveDataProvider(["AAPL"], client=client).read()) == 3


def test_quotes_preserve_timestamp(key):
    stamp = 1704205800
    data = {
        "symbol": "AAPL",
        "close": "185.50",
        "timestamp": stamp,
        "currency": "USD",
        "is_market_open": False,
    }
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        quote = TwelveDataProvider(["AAPL"], client=client).quotes()[0]
    assert quote["provider_timestamp"] == datetime.fromtimestamp(stamp, timezone.utc).isoformat()
    assert quote["price"] == 185.5
    assert "not independently verified" in quote["freshness"]


def test_currency_rejected(key):
    data = history()
    data["meta"]["currency"] = "INR"
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        with pytest.raises(MarketDataError, match="USD"):
            TwelveDataProvider(["AAPL"], client=client).read()


def test_old_synthetic_data_hidden(client, dataset, monkeypatch):
    monkeypatch.setattr(settings(), "allow_synthetic_data", False)
    assert client.get("/datasets").json() == []
    assert client.get(f"/assets/AAPL/prices?dataset_id={dataset}").status_code == 404
    assert client.get("/assets").json() == []


def test_api_missing_key(client, monkeypatch):
    monkeypatch.setattr(settings(), "twelvedata_api_key", SecretStr(""))
    assert client.get("/market/status").json()["configured"] is False
    response = client.post("/market/refresh", json={"symbols": ["AAPL"]})
    assert response.status_code == 503
    assert "TWELVEDATA_API_KEY" in response.json()["detail"]


def test_real_history_api_import(client, monkeypatch, key):
    def response(self, endpoint, params):
        data = history()
        data["meta"]["symbol"] = params["symbol"]
        return data

    monkeypatch.setattr(TwelveDataProvider, "_request", response)
    monkeypatch.setattr(settings(), "allow_synthetic_data", False)
    response = client.post("/market/refresh", json={"symbols": ["AAPL"], "observations": 10})
    assert response.status_code == 200, response.text
    datasets = client.get("/datasets").json()
    assert len(datasets) == 1
    assert datasets[0]["quality"]["provider_metadata"]["provider"] == "Twelve Data"
    assert datasets[0]["rows"] == 6


def test_dashboard_empty_state(client, monkeypatch):
    from pathlib import Path

    import streamlit as st
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(settings(), "twelvedata_api_key", SecretStr(""))

    def fake_get(url, **kwargs):
        return client.get(url.replace("http://127.0.0.1:8000", ""))

    monkeypatch.setattr(httpx, "get", fake_get)
    st.cache_data.clear()
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[2] / "dashboard/app.py"), default_timeout=30
    ).run()
    assert not app.exception
    assert any("No real dataset" in message.value for message in app.info)
    assert next(b for b in app.button if b.label == "Load real daily history").disabled
    st.cache_data.clear()
