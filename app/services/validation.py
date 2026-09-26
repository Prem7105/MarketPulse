"""Strict daily-bar validation, with non-destructive warnings."""

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close", "adjusted_close"]


@dataclass
class DataQualityReport:
    rows_processed: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    missing_dates: dict = field(default_factory=dict)
    duplicates: list = field(default_factory=list)
    suspicious_returns: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def validate_prices(raw: pd.DataFrame):
    report = DataQualityReport(rows_processed=len(raw))
    frame = raw.copy()
    frame.columns = frame.columns.astype(str).str.strip().str.lower()
    if frame.columns.duplicated().any():
        raise ValueError("Column names collide after normalization")
    required = ["date", "symbol", *PRICE_COLUMNS]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing))}")
    frame = frame[required].reset_index(drop=True)
    symbol_null = frame.symbol.isna()
    raw_symbols = frame.symbol.astype(str)
    frame.symbol = raw_symbols.str.strip().str.upper()
    if not raw_symbols.equals(frame.symbol):
        report.warnings.append("Ticker whitespace/case normalized to uppercase")
    raw_dates = frame.date.astype(str)
    dates_ok = raw_dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    frame.date = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
    for col in PRICE_COLUMNS:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    checks = {
        "Date must be a valid ISO YYYY-MM-DD daily date": ~dates_ok | frame.date.isna(),
        "Ticker must contain 1–32 letters, digits, dot, dash or caret": ~frame.symbol.str.fullmatch(
            r"[A-Z0-9.^-]{1,32}"
        )
        | symbol_null,
        "Prices must be finite and strictly positive": (
            ~np.isfinite(frame[PRICE_COLUMNS]) | (frame[PRICE_COLUMNS] <= 0)
        ).any(axis=1),
        "Impossible OHLC relationship": (frame.low > frame[["open", "close", "high"]].min(axis=1))
        | (frame.high < frame[["open", "close", "low"]].max(axis=1)),
        "Duplicate symbol/date: all conflicting rows rejected": frame.duplicated(
            ["symbol", "date"], keep=False
        ),
    }
    rejected = pd.Series(False, index=frame.index)
    for message, mask in checks.items():
        for idx in frame.index[mask]:
            report.errors.append({"row": int(idx) + 2, "reason": message})
        rejected |= mask
    report.duplicates = (
        frame.index[checks["Duplicate symbol/date: all conflicting rows rejected"]] + 2
    ).tolist()
    clean = frame.loc[~rejected].sort_values(["symbol", "date"]).reset_index(drop=True)
    report.rows_accepted = len(clean)
    report.rows_rejected = len(frame) - len(clean)
    for symbol, group in clean.groupby("symbol"):
        prices = group.set_index("date").adjusted_close
        absent = pd.bdate_range(prices.index.min(), prices.index.max()).difference(prices.index)
        report.missing_dates[symbol] = absent.strftime("%Y-%m-%d").tolist()
        moves = prices.pct_change(fill_method=None)
        for date, value in moves[moves.abs() > 0.25].items():
            report.suspicious_returns.append(
                {"symbol": symbol, "date": str(date.date()), "return": float(value)}
            )
        if moves.eq(0).rolling(5).sum().ge(5).any():
            report.warnings.append(
                f"{symbol}: at least five unchanged observations; inspect staleness"
            )
    if any(report.missing_dates.values()):
        report.warnings.append(
            "Missing weekdays flagged; an exchange calendar is required to distinguish holidays"
        )
    if report.suspicious_returns:
        report.warnings.append("Moves above 25% retained; inspect corporate actions and source")
    return clean, report
