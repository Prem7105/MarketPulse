"""Generate illustrative synthetic data, never presented as market history."""

from pathlib import Path

import numpy as np
import pandas as pd

SYMBOLS = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "JPM", "XOM", "JNJ", "SPY"]


def generate(folder=Path("tests/fixtures/generated"), seed=2026, observations=756):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=observations)
    factors = pd.DataFrame(
        rng.normal(0, 0.004, (observations, 6)),
        index=dates,
        columns=["market", "size", "value", "momentum", "quality", "low_volatility"],
    )
    factors["market"] = rng.normal(0.0003, 0.009, observations)
    if observations > 250:
        factors.iloc[250 : min(275, observations), 0] -= 0.008
    rf = pd.Series((1.03) ** (1 / 252) - 1, index=dates, name="risk_free")
    frames = []
    for i, symbol in enumerate(SYMBOLS):
        beta = rng.uniform(-0.3, 0.4, 6)
        beta[0] = 0.65 + i * 0.08
        noise = rng.normal(0, 0.006 + i * 0.0004, observations)
        r = factors.to_numpy() @ beta + noise + rf.to_numpy()
        if symbol == "SPY":
            r = factors.market.to_numpy() + rf.to_numpy()
        price = (70 + i * 20) * np.cumprod(1 + r)
        opened = price * np.exp(rng.normal(0, 0.002, observations))
        frames.append(
            pd.DataFrame(
                {
                    "date": dates.strftime("%Y-%m-%d"),
                    "symbol": symbol,
                    "open": opened,
                    "high": np.maximum(price, opened) * 1.004,
                    "low": np.minimum(price, opened) * 0.996,
                    "close": price,
                    "adjusted_close": price,
                }
            )
        )
    pd.concat(frames).to_csv(folder / "prices.csv", index=False, float_format="%.8f")
    factors.rename_axis("date").to_csv(folder / "factors.csv", float_format="%.12g")
    rf.rename_axis("date").to_csv(folder / "risk_free.csv", float_format="%.12g")
    (folder / "README.md").write_text(
        f"# SYNTHETIC DATA — NOT REAL MARKET HISTORY\n\nSeed {seed}; {observations} weekday observations; fictional prices using familiar ticker labels. Six fictional factors are not Fama–French data. No splits, dividends, delistings, exchange holidays or currency changes. Regenerate with `python -m scripts.generate_sample`. Prices used for return calculations are adjusted_close.\n"
    )


if __name__ == "__main__":
    generate()
