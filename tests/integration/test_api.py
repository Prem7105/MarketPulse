import io

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.db.models import AssetPrice, Dataset, ResearchRun
from app.services.ingestion import CSVProvider, ingest
from app.services.research import price_panel


def request(dataset):
    return {"dataset_id": dataset, "symbols": ["AAPL", "MSFT"], "benchmark": "SPY", "window": 20}


def test_health_assets_prices(client, dataset):
    assert client.get("/health").status_code == 200
    assert len(client.get("/datasets").json()) == 1
    assert len(client.get("/assets").json()) == 9
    assert client.get("/assets/AAPL").json()["symbol"] == "AAPL"
    assert client.get("/assets/UNKNOWN").status_code == 404
    assert len(client.get(f"/assets/AAPL/prices?dataset_id={dataset}").json()) == 100


@pytest.mark.parametrize(
    "path",
    [
        "/research/asset",
        "/research/compare",
        "/research/factor-analysis",
        "/portfolios",
        "/backtests",
        "/reports",
    ],
)
def test_research_endpoints(client, dataset, path, db):
    payload = request(dataset)
    if path == "/backtests":
        payload["lookback"] = 20
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run_id"]
    run = db.get(ResearchRun, body["run_id"])
    assert run.dataset_id == dataset
    if path == "/portfolios":
        assert client.get(f"/portfolios/{body['portfolio_id']}/analytics").status_code == 200
        assert sum(body["results"]["attribution"].values()) == pytest.approx(
            body["results"]["metrics"]["cumulative_return"]
        )
    if path == "/backtests":
        assert client.get(f"/backtests/{body['backtest_id']}").status_code == 200
    if path == "/reports":
        report = client.get(f"/reports/{body['run_id']}")
        assert "SYNTHETIC" in report.text
        assert "12. Limitations" in report.text


@pytest.mark.parametrize(
    "patch",
    [
        {"symbols": []},
        {"symbols": ["AAPL", "AAPL"]},
        {"periods": 0},
        {"start": "2025-01-01", "end": "2024-01-01"},
        {"confidence": 1},
    ],
)
def test_api_rejects_invalid(client, dataset, patch):
    assert client.post("/research/compare", json={**request(dataset), **patch}).status_code == 422


def test_unknown_and_invalid_weights(client, dataset):
    assert (
        client.post(
            "/research/compare", json={**request(dataset), "dataset_id": "a" * 64}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/portfolios", json={**request(dataset), "weights": {"AAPL": 0.5, "MSFT": 0.6}}
        ).status_code
        == 422
    )
    for path in ["/backtests/9999", "/portfolios/9999", "/reports/missing"]:
        assert client.get(path).status_code == 404


def test_idempotent_ingestion(db, sample_folder):
    provider = CSVProvider(sample_folder / "prices.csv", "fixture")
    one, _ = ingest(db, provider)
    two, _ = ingest(db, provider)
    assert one == two
    assert db.scalar(select(func.count()).select_from(AssetPrice)) == 900
    assert db.scalar(select(func.count()).select_from(Dataset)) == 1


def test_dataset_versioning(db, sample_folder):
    one, _ = ingest(db, CSVProvider(sample_folder / "prices.csv", "fixture"))
    original = price_panel(db, one, ["AAPL"])
    frame = pd.read_csv(sample_folder / "prices.csv")
    frame.loc[0, "adjusted_close"] *= 1.1
    two, _ = ingest(db, CSVProvider(io.StringIO(frame.to_csv(index=False)), "fixture"))
    assert one != two
    pd.testing.assert_frame_equal(original, price_panel(db, one, ["AAPL"]))


def test_upload(client, sample_folder):
    response = client.post(
        "/ingest", json={"source": "CSV test", "csv": (sample_folder / "prices.csv").read_text()}
    )
    assert response.status_code == 200, response.text
    assert response.json()["quality"]["rows_accepted"] == 900
    assert client.post("/ingest", json={"source": "bad", "csv": "x,y\n1,2"}).status_code == 422


def test_api_key(client, dataset, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings(), "api_key", "test-key")
    assert client.get("/datasets").status_code == 401
    assert client.get("/datasets", headers={"X-API-Key": "test-key"}).status_code == 200
