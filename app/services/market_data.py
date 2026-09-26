"""Authenticated external data only. Quotes are separate from daily research bars."""

import math
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
import pandas as pd

from app.core.config import settings


class MarketDataError(Exception):
    """Safe, secret-free error presented to researchers."""


def symbols_list(symbols):
    values = list(dict.fromkeys(s.strip().upper() for s in symbols))
    if (
        not values
        or len(values) > 20
        or any(not re.fullmatch(r"[A-Z0-9.^-]{1,32}", s) for s in values)
    ):
        raise ValueError("Choose 1–20 valid ticker symbols")
    return values


class TwelveDataProvider:
    source = "Twelve Data | daily OHLC adjusted for splits and dividends (adjust=all)"

    def __init__(self, symbols, outputsize=756, client=None):
        self.symbols = symbols_list(symbols)
        if not 3 <= outputsize <= 5000:
            raise ValueError("History length must be 3–5000 observations")
        self.outputsize = outputsize
        self.client = client
        config = settings()
        if config.market_data_provider != "twelvedata":
            raise MarketDataError(
                "Unsupported provider. Configure MARKET_DATA_PROVIDER=twelvedata."
            )
        self.key = config.twelvedata_api_key.get_secret_value()
        if not self.key:
            raise MarketDataError(
                "Set TWELVEDATA_API_KEY in the server .env file to load real prices."
            )
        self.metadata = {
            "provider": "Twelve Data",
            "adjustment": "all",
            "interval": "1day",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "symbols": {},
        }

    def _request(self, endpoint, params):
        # Header authentication avoids API keys in URLs, query logs and HTTP error strings.
        def send(client):
            return client.get(
                f"https://api.twelvedata.com/{endpoint}",
                params=params,
                headers={"Authorization": f"apikey {self.key}"},
                timeout=30,
            )

        try:
            if self.client is None:
                with httpx.Client(follow_redirects=False) as client:
                    response = send(client)
            else:
                response = send(self.client)
            if response.status_code in (401, 403):
                raise MarketDataError("Provider rejected the key or this data entitlement.")
            if response.status_code == 429:
                raise MarketDataError("Provider rate limit reached. Wait before requesting again.")
            if response.status_code != 200:
                raise MarketDataError(f"Provider request failed (HTTP {response.status_code}).")
            data = response.json()
            if not isinstance(data, dict):
                raise MarketDataError("Provider returned an unexpected response format.")
            if data.get("status") == "error" or "code" in data:
                code = data.get("code")
                if code == 429:
                    raise MarketDataError(
                        "Provider rate limit reached. Wait before requesting again."
                    )
                if code in (401, 403):
                    raise MarketDataError("Provider rejected the key or this data entitlement.")
                # Never relay arbitrary vendor error text; it may echo credentials.
                raise MarketDataError(
                    "Provider could not supply this symbol/data. Check plan and ticker."
                )
            return data
        except (httpx.HTTPError, ValueError):
            raise MarketDataError(
                "Market-data connection or response failed. No substitute data was used."
            ) from None

    def read(self):
        frames = []
        for symbol in self.symbols:
            data = self._request(
                "time_series",
                {
                    "symbol": symbol,
                    "interval": "1day",
                    "outputsize": self.outputsize,
                    "adjust": "all",
                    "order": "asc",
                },
            )
            meta = data.get("meta", {})
            if meta.get("symbol", "").upper() != symbol or meta.get("currency") != "USD":
                raise MarketDataError(
                    "History must match the requested symbol and be USD denominated."
                )
            try:
                tz = ZoneInfo(meta["exchange_timezone"])
                today = datetime.now(tz).date()
                frame = pd.DataFrame(data["values"])
                if frame.empty or not {"datetime", "open", "high", "low", "close"}.issubset(frame):
                    raise ValueError()
                frame = frame.rename(columns={"datetime": "date"})
                dates = pd.to_datetime(frame.date, format="%Y-%m-%d", errors="raise")
                # Conservatively exclude the exchange-local current day, even after closing.
                frame = frame.loc[dates.dt.date < today].copy()
                if len(frame) < 3:
                    raise ValueError()
                frame["symbol"] = symbol
                # All returned OHLC were explicitly requested with adjust=all.
                frame["adjusted_close"] = frame["close"]
                frames.append(
                    frame[["date", "symbol", "open", "high", "low", "close", "adjusted_close"]]
                )
                self.metadata["symbols"][symbol] = {
                    "exchange": meta.get("exchange"),
                    "exchange_timezone": meta["exchange_timezone"],
                    "currency": "USD",
                    "latest_completed_bar": frame.date.max(),
                }
            except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError):
                raise MarketDataError(
                    "Provider history is incomplete or missing exchange timezone metadata."
                ) from None
        result = pd.concat(frames, ignore_index=True)
        from app.services.validation import validate_prices

        _, report = validate_prices(result)
        if report.rows_rejected:
            raise MarketDataError(
                "Provider returned invalid bars; import cancelled without partial data."
            )
        return result

    def quotes(self):
        quotes = []
        for symbol in self.symbols:
            data = self._request("quote", {"symbol": symbol})
            try:
                price = float(data["close"])
                stamp = int(data["timestamp"])
                if (
                    data["symbol"].upper() != symbol
                    or price <= 0
                    or not math.isfinite(price)
                    or stamp <= 0
                ):
                    raise ValueError()
                observed = datetime.fromtimestamp(stamp, timezone.utc)
                fetched = datetime.now(timezone.utc)
                quotes.append(
                    {
                        "symbol": symbol,
                        "price": price,
                        "currency": data.get("currency"),
                        "exchange": data.get("exchange"),
                        "provider_timestamp": observed.isoformat(),
                        "fetched_at": fetched.isoformat(),
                        "age_seconds": max(0, (fetched - observed).total_seconds()),
                        "is_market_open": data.get("is_market_open"),
                        "provider": "Twelve Data",
                        "freshness": "Provider timestamp shown; real-time/delayed entitlement not independently verified",
                    }
                )
            except (KeyError, TypeError, ValueError, OverflowError, OSError):
                raise MarketDataError("Provider quote has no valid price or timestamp.") from None
        return quotes
