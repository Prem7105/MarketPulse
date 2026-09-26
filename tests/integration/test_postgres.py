import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.services.ingestion import CSVProvider, ingest


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Dedicated PostgreSQL TEST_DATABASE_URL not supplied"
)
def test_postgres_migrations_and_ingestion(sample_folder):
    url = os.environ["TEST_DATABASE_URL"]
    assert "test" in url.rsplit("/", 1)[-1], "Only a dedicated test database may be migrated down"
    env = {**os.environ, "DATABASE_URL": url}

    def migrate(target):
        subprocess.run(
            [sys.executable, "-m", "alembic", *target], env=env, check=True, capture_output=True
        )

    migrate(["upgrade", "head"])
    engine = create_engine(url)
    assert "asset_prices" in inspect(engine).get_table_names()
    with Session(engine) as db:
        dataset_id, _ = ingest(db, CSVProvider(sample_folder / "prices.csv", "PostgreSQL test"))
        assert (
            db.execute(
                text("SELECT count(*) FROM asset_prices WHERE dataset_id=:d"), {"d": dataset_id}
            ).scalar()
            == 900
        )
    migrate(["downgrade", "base"])
    assert "asset_prices" not in inspect(engine).get_table_names()
    migrate(["upgrade", "head"])
    engine.dispose()
