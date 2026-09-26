# Real market data setup

The application no longer ships synthetic observations or seeds them at startup. Old synthetic snapshots remain preserved in an existing database but are hidden and blocked for research by default. No API failure falls back to random, demo or made-up prices. Generated observations are restricted to automated tests.

## Supported API: Twelve Data

Set these values in the server `.env` (which is git-ignored):

```dotenv
MARKET_DATA_PROVIDER=twelvedata
TWELVEDATA_API_KEY=your_actual_provider_key
```

`API_KEY` is the optional key that protects MarketPulse's own API; it is different from the vendor credential. Never put vendor credentials in frontend code, commits, screenshots or query URLs. The provider uses an Authorization header and suppresses vendor error bodies. This implementation supports Twelve Data; another provider requires its own adapter. No valid key was supplied during implementation, so authenticated vendor access and your entitlements have not been verified.

Start with `docker compose up --build` after copying `.env.example` to `.env` and setting the key. The init container now runs migrations only. Open the dashboard's **Market data connection** panel; use **Fetch latest quotes**, optional **Refresh quotes every 60 seconds**, and **Load real daily history**.

Or import from the project root:

```bash
python -m scripts.ingest_market_data --symbols AAPL MSFT SPY --observations 756
```

## Honest freshness and adjustment conventions

Quotes come from `/quote`; provider timestamp, fetch time, quote age, exchange/currency and market-open field are shown. REST polling is not a tick-by-tick WebSocket feed. A paid/data entitlement may be required for the exchanges and latency you need. A fresh HTTP response does not guarantee a fresh quote. A closed exchange may return its last session. The UI does not label an unverified entitlement as real-time.

Historical research uses `/time_series` with `interval=1day`, `adjust=all`, and a bounded observation count. The provider's adjusted OHLC close is mapped into adjusted_close. Today's exchange-local daily bar is excluded conservatively to avoid mixing partial sessions into daily risk statistics, including after the close; the session becomes eligible the next local date. USD instruments only are supported by the current single-currency database. Missing exchange timezone/currency, invalid bars, unavailable symbols, auth failures and rate limits produce clear failures without partial imports.

Each symbol consumes API credits. Refreshes are explicit; quote polling is off by default. The server does not automatically retry rate-limit failures or purchase an upgrade. Choose a small universe within your plan. Data remains versioned; the snapshot's quality metadata includes provider, adjustment mode, fetched time and exchange details. Historical snapshot hash is independent of the quote timestamp.

Factors and dated risk-free series are separate datasets. The quote/price integration does not invent them. Factor views and reports state unavailable until real dated factor and risk-free observations are imported together with the price dataset via CSV. The risk-free input used for basic risk metrics remains an explicit modeling assumption, not a claimed live interest rate.

## Endpoints

- `GET /market/status`: provider name and whether a key is configured, never the key.
- `GET /market/quotes?symbols=AAPL,MSFT`: authenticated provider quotes, no database mixing.
- `POST /market/refresh`: `{ "symbols": ["AAPL","MSFT"], "benchmark": "SPY", "observations": 756 }`; imports validated completed bars into a versioned research snapshot.

## Verification

Mock-transport tests cover header authentication, adjustment parameters, current-day exclusion, entitlement/rate errors, missing keys, quote timestamps and synthetic-data blocking. They exercise provider behavior deterministically without using API credits. A real end-to-end request requires your provider key and network access to the vendor. No real market result is claimed before that check.

Official references:
- https://twelvedata.com/docs
- https://support.twelvedata.com/en/articles/5656039-how-to-get-historical-prices
- https://github.com/twelvedata/mcp/blob/main/CLAUDE.md
