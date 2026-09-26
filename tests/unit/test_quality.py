import numpy as np
import pandas as pd
import pytest

from app.services.validation import validate_prices


def bars():
    return pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "symbol": ["ABC"] * 3,
            "open": [10] * 3,
            "high": [11] * 3,
            "low": [9] * 3,
            "close": [10] * 3,
            "adjusted_close": [10] * 3,
        }
    )


@pytest.mark.parametrize(
    "column,value",
    [
        ("date", "wrong"),
        ("date", "2024-01-02T00:00:00Z"),
        ("symbol", "BAD SYMBOL"),
        ("symbol", None),
        ("low", 0),
        ("close", 12),
        ("adjusted_close", np.nan),
        ("high", np.inf),
        ("low", -1),
    ],
)
def test_rejected(column, value):
    f = bars()
    f.loc[1, column] = value
    clean, report = validate_prices(f)
    assert report.rows_rejected == 1
    assert len(clean) == 2
    assert report.errors


def test_duplicate_all_rejected():
    f = bars()
    f.loc[1, "date"] = f.loc[0, "date"]
    clean, report = validate_prices(f)
    assert len(report.duplicates) == 2
    assert len(clean) == 1


def test_suspicious_retained():
    f = bars()
    f.loc[1, "adjusted_close"] = 30
    clean, report = validate_prices(f)
    assert len(clean) == 3
    assert len(report.suspicious_returns) == 2


def test_missing_and_normalization():
    f = bars()
    f.loc[2, "date"] = "2024-01-05"
    f.symbol = " abc "
    clean, report = validate_prices(f)
    assert clean.symbol.eq("ABC").all()
    assert report.missing_dates["ABC"] == ["2024-01-03", "2024-01-04"]


def test_schema():
    with pytest.raises(ValueError, match="Missing CSV columns"):
        validate_prices(bars().drop(columns="close"))
