import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.services.ingestion import CSVProvider, ingest
from tests.sample_data import generate


@pytest.fixture(scope="session")
def sample_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp("sample")
    generate(folder, observations=100)
    return folder


@pytest.fixture
def db(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings(), "allow_synthetic_data", True)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def dataset(db, sample_folder):
    f = pd.read_csv(sample_folder / "factors.csv", index_col="date", parse_dates=True)
    rf = pd.read_csv(sample_folder / "risk_free.csv", index_col="date", parse_dates=True).risk_free
    return ingest(db, CSVProvider(sample_folder / "prices.csv", "SYNTHETIC fixture"), f, rf)[0]


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
