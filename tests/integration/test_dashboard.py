"""Opt-in smoke test against a running seeded API: RUN_DASHBOARD_TESTS=1 pytest."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.skipif(os.getenv("RUN_DASHBOARD_TESTS") != "1", reason="Requires running seeded API")
def test_every_dashboard_view():
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[2] / "dashboard/app.py"), default_timeout=60
    ).run()
    assert not app.exception
    for page in app.sidebar.radio[0].options:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, f"{page}: {app.exception}"
        label = {
            "Portfolio Analytics": "Analyze portfolio",
            "Factor Analysis": "Estimate exposures",
            "Backtesting": "Run backtest",
            "Research Reports": "Generate research report",
        }.get(page)
        if label:
            next(b for b in app.button if b.label == label).click().run(timeout=120)
            assert not app.exception, f"{page}: {app.exception}"
