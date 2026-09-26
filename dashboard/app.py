"""Research UI: consumes API results and keeps finance logic in the backend."""

import os

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="MarketPulse | Research", page_icon="📊", layout="wide")
st.markdown(
    """<style>.stApp {background:#0b1120;color:#e2e8f0} [data-testid=stMetric] {background:#151f32;padding:16px;border-radius:10px;border:1px solid #27364d} h1,h2,h3{letter-spacing:-.03em}</style>""",
    unsafe_allow_html=True,
)
API = os.getenv("API_URL", "http://127.0.0.1:8000")
HEADERS = {"X-API-Key": os.getenv("API_KEY", "")}


@st.cache_data(ttl=30)
def get(path):
    response = httpx.get(API + path, headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.json()


def post(path, payload):
    response = httpx.post(API + path, json=payload, headers=HEADERS, timeout=180)
    if response.is_error:
        try:
            message = response.json().get("detail", response.text)
        except ValueError:
            message = response.text
        st.error(str(message))
        st.stop()
    get.clear()
    return response.json()


def line(rows, title, y=None):
    frame = pd.DataFrame(rows)
    if frame.empty:
        st.info("No observations for this view")
        return
    frame["date"] = pd.to_datetime(frame.date)
    fig = px.line(
        frame,
        x="date",
        y=y or [c for c in frame.columns if c != "date"],
        title=title,
        template="plotly_dark",
    )
    fig.update_layout(
        paper_bgcolor="#0b1120",
        plot_bgcolor="#0b1120",
        legend_title_text="",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig, width="stretch")


def cards(metrics):
    for col, key, label in zip(
        st.columns(4),
        ["cumulative_return", "annualized_volatility", "sharpe", "max_drawdown"],
        ["Cumulative return", "Annual volatility", "Sharpe ratio", "Maximum drawdown"],
    ):
        value = metrics.get(key)
        col.metric(
            label,
            (
                "Undefined"
                if value is None
                else (f"{value:.2f}" if key == "sharpe" else f"{value:.2%}")
            ),
        )


def heatmap(values, title):
    st.plotly_chart(
        px.imshow(
            pd.DataFrame(values),
            text_auto=".2f",
            title=title,
            color_continuous_scale="RdBu_r",
            template="plotly_dark",
        ),
        width="stretch",
    )


st.title("MarketPulse")
st.caption("QUANTITATIVE INVESTMENT RESEARCH & RISK ANALYTICS")
try:
    datasets = get("/datasets")
except httpx.HTTPError:
    st.error("API unavailable. Start the API and database using the README commands.")
    st.stop()

with st.expander("Market data connection", expanded=not datasets):
    status = get("/market/status")
    st.caption(
        f"Provider: {status['provider']} · {'Key configured' if status['configured'] else 'API key needed in server .env'}"
    )
    market_symbols = st.text_input("Market symbols (comma separated)", "AAPL,MSFT,SPY")
    market_list = [v.strip().upper() for v in market_symbols.split(",") if v.strip()]
    history_length = st.number_input("Daily history observations", 3, 5000, 756)
    if st.button("Load real daily history", disabled=not status["configured"]):
        post("/market/refresh", {"symbols": market_list, "observations": history_length})
        st.rerun()
    st.caption(
        "Daily research excludes today's incomplete exchange session. Each symbol consumes provider credits."
    )
    auto_quotes = st.toggle(
        "Refresh quotes every 60 seconds", value=False, disabled=not status["configured"]
    )

    @st.fragment(run_every=60 if auto_quotes else None)
    def quote_panel():
        clicked = st.button("Fetch latest quotes", disabled=not status["configured"])
        if auto_quotes or clicked:
            try:
                response = httpx.get(
                    API + "/market/quotes",
                    params={"symbols": ",".join(market_list)},
                    headers=HEADERS,
                    timeout=180,
                )
                if response.is_error:
                    st.error(response.json().get("detail", "Quotes unavailable"))
                else:
                    st.dataframe(pd.DataFrame(response.json()), hide_index=True, width="stretch")
                    st.caption(
                        "Provider timestamp is shown. Data may be delayed or from the last closed session depending on exchange and plan."
                    )
            except httpx.HTTPError:
                st.error("Quote request failed. No substitute prices are shown.")

    quote_panel()

with st.sidebar:
    st.subheader("Research workspace")
    page = st.radio(
        "View",
        [
            "Overview",
            "Asset Research",
            "Risk Analytics",
            "Portfolio Analytics",
            "Benchmark Comparison",
            "Factor Analysis",
            "Attribution",
            "Backtesting",
            "Data Quality",
            "Research Reports",
        ],
    )
    if not datasets:
        st.info(
            "No real dataset loaded. Configure the provider key and use Load real daily history, or import a genuine provider CSV below."
        )
        upload = st.file_uploader("Price CSV", type="csv")
        source = st.text_input("Data source", "User CSV")
        if upload and st.button("Import data"):
            post("/ingest", {"csv": upload.getvalue().decode(), "source": source})
            st.rerun()
        st.stop()
    dataset = st.selectbox(
        "Dataset", datasets, format_func=lambda d: f"{d['source']} · {d['id'][:8]}"
    )
    all_assets = [a["symbol"] for a in get(f"/assets?dataset_id={dataset['id']}")]
    symbols = st.multiselect(
        "Research assets",
        all_assets,
        default=[s for s in ["AAPL", "MSFT", "NVDA", "AMZN"] if s in all_assets] or all_assets[:1],
    )
    benchmark = st.selectbox(
        "Benchmark",
        ["None"] + all_assets,
        index=all_assets.index("SPY") + 1 if "SPY" in all_assets else 0,
    )
    periods = st.number_input("Observations per year", 1, 366, 252)
    rf = st.number_input("Annual risk-free (%)", -99.0, 100.0, 3.0, step=0.5) / 100
    window = st.selectbox("Rolling / lookback window", [20, 60, 126, 252], index=1)
    start = st.date_input("Start", pd.Timestamp(dataset["start"]).date())
    end = st.date_input("End", pd.Timestamp(dataset["end"]).date())
    confidence = st.slider("VaR confidence", 0.80, 0.99, 0.95, 0.01)

if not symbols:
    st.info("Select at least one asset in the sidebar.")
    st.stop()
if "SYNTHETIC" in dataset["source"].upper():
    st.warning(
        "SYNTHETIC DEMONSTRATION — fictional prices and factors, not actual market performance."
    )
st.caption(
    f"Dataset {dataset['id'][:12]} · latest available {dataset['end']} · source: {dataset['source']}"
)
payload = {
    "dataset_id": dataset["id"],
    "symbols": symbols,
    "benchmark": None if benchmark == "None" else benchmark,
    "periods": periods,
    "annual_rf": rf,
    "window": window,
    "start": str(start),
    "end": str(end),
    "confidence": confidence,
}


def cached_run(path, body):
    key = str((path, body))
    if st.session_state.get("request_key") != key:
        st.session_state["result"] = post(path, body)
        st.session_state["request_key"] = key
    return st.session_state["result"]


if page in ["Overview", "Asset Research", "Risk Analytics", "Benchmark Comparison"]:
    selected = st.selectbox("Selected asset", symbols)
    run = cached_run("/research/asset", {**payload, "symbols": [selected]})
    data = run["results"]
    cards(data["metrics"])
    if page == "Overview":
        line(data["equity"], f"{selected} · growth of one unit")
        comparison = cached_run("/research/compare", payload)["results"]
        st.dataframe(pd.DataFrame(comparison["summary"]), hide_index=True, width="stretch")
    elif page == "Asset Research":
        tab1, tab2, tab3 = st.tabs(["Prices", "Volatility & Sharpe", "Drawdown & Returns"])
        with tab1:
            line(data["prices"], "Adjusted close")
        with tab2:
            line(data["rolling"], "Rolling volatility and Sharpe", ["volatility", "sharpe"])
        with tab3:
            line(data["drawdown"], "Drawdown from previous peak")
            st.subheader("Calendar period returns")
            period = st.selectbox("Frequency", ["weekly", "monthly", "yearly"])
            st.dataframe(data["period_returns"][period], hide_index=True)
    elif page == "Risk Analytics":
        tab1, tab2, tab3 = st.tabs(["Distribution", "Drawdown", "Statistics"])
        with tab1:
            left, right = st.columns(2)
            with left:
                st.dataframe(pd.Series(data["metrics"], name="value"), width="stretch")
            with right:
                st.plotly_chart(
                    px.histogram(
                        pd.DataFrame(data["returns"]),
                        x="value",
                        nbins=50,
                        title="Daily return distribution",
                        template="plotly_dark",
                    ),
                    width="stretch",
                )
        with tab2:
            line(data["drawdown"], "Drawdown")
            st.dataframe(data["drawdown_table"], hide_index=True)
        with tab3:
            qq = pd.DataFrame(data["statistics"]["qq"])
            st.plotly_chart(
                px.scatter(
                    qq,
                    x="theoretical",
                    y="observed",
                    title="Normal QQ diagnostic",
                    template="plotly_dark",
                ),
                width="stretch",
            )
            st.json({k: v for k, v in data["statistics"].items() if k != "qq"}, expanded=False)
    else:
        if payload["benchmark"] is None:
            st.info("Select a benchmark to compare.")
        else:
            chart = (
                pd.DataFrame(data["equity"])
                .rename(columns={"value": selected})
                .merge(
                    pd.DataFrame(data["benchmark_equity"]).rename(columns={"value": benchmark}),
                    on="date",
                )
            )
            line(chart.to_dict("records"), "Matched-date cumulative performance")
            line(data["relative_drawdown"], "Relative wealth drawdown")
            line(data["rolling"], "Rolling beta and correlation", ["beta", "correlation"])
            st.dataframe(
                {
                    k: data["metrics"].get(k)
                    for k in [
                        "beta",
                        "alpha",
                        "active_return",
                        "tracking_error",
                        "information_ratio",
                        "upside_capture",
                        "downside_capture",
                    ]
                }
            )
elif page in ["Portfolio Analytics", "Attribution"]:
    st.subheader("Portfolio construction")
    holdings = st.data_editor(
        pd.DataFrame({"symbol": symbols, "weight": [1 / len(symbols)] * len(symbols)}),
        disabled=["symbol"],
        hide_index=True,
        width="stretch",
    )
    frequency = st.selectbox("Rebalance", ["monthly", "quarterly", "daily", "none"])
    cost = st.number_input("Transaction cost (bps per risky dollar)", 0.0, 1000.0, 10.0)
    if st.button("Analyze portfolio", type="primary"):
        st.session_state["portfolio"] = post(
            "/portfolios",
            {
                **payload,
                "weights": dict(zip(holdings.symbol, holdings.weight)),
                "frequency": frequency,
                "cost_bps": cost,
            },
        )
    if "portfolio" in st.session_state:
        stored = st.session_state["portfolio"]
        st.caption(
            f"Saved run {stored['run_id']} · parameters below identify the analyzed selection"
        )
        with st.expander("Saved parameters"):
            st.json(stored["parameters"])
        data = stored["results"]
        cards(data["metrics"])
        if page == "Portfolio Analytics":
            tab1, tab2, tab3 = st.tabs(["Performance", "Holdings & Correlation", "Risk Attribution"])
            with tab1:
                line(data["path"], "Portfolio equity", ["wealth"])
            with tab2:
                line(data["weights"], "Beginning-period holdings")
                heatmap(data["correlation"], "Asset return correlation")
            with tab3:
                st.bar_chart(pd.Series(data["target_weight_risk"]["risk_contribution"]))
                st.caption(
                    "Risk contributions use the target weights and full-sample covariance; realized risk reflects drifting holdings."
                )
        else:
            st.bar_chart(pd.Series(data["attribution"]))
            st.caption(
                "Wealth-linked security, cash and cost contributions sum to cumulative portfolio return."
            )
            st.json(data.get("active_contribution", {}))
elif page == "Factor Analysis":
    names = st.multiselect(
        "Factors",
        ["market", "size", "value", "momentum", "quality", "low_volatility"],
        default=["market", "size", "value", "momentum"],
    )
    if names and st.button("Estimate exposures", type="primary"):
        result = post("/research/factor-analysis", {**payload, "factors": names})
        st.session_state["factors"] = result
    if "factors" in st.session_state:
        saved = st.session_state["factors"]
        with st.expander("Saved run parameters"):
            st.json(saved["parameters"])
        for symbol, data in saved["results"].items():
            st.subheader(f"{symbol} · R² {data['r_squared']:.3f}")
            frame = pd.DataFrame(data["coefficients"]).T
            st.dataframe(frame, width="stretch")
            fig = go.Figure(
                go.Bar(
                    x=frame.index,
                    y=frame.beta,
                    error_y=dict(
                        type="data",
                        array=frame.ci_high - frame.beta,
                        arrayminus=frame.beta - frame.ci_low,
                    ),
                )
            )
            fig.update_layout(
                title="Coefficient estimates and 95% intervals", template="plotly_dark"
            )
            st.plotly_chart(fig, width="stretch")
        st.caption(
            "HAC standard errors address some serial dependence. Statistical association does not establish causality."
        )
elif page == "Backtesting":
    strategy = st.selectbox(
        "Strategy", ["buy_hold", "equal_weight", "momentum", "moving_average", "volatility_target"]
    )
    cost = st.number_input("Trading cost (bps)", 0.0, 1000.0, 10.0)
    frequency = st.selectbox("Rebalancing", ["monthly", "quarterly", "daily", "none"])
    target = st.slider("Target annual volatility", 0.01, 0.50, 0.15, 0.01)
    st.caption(
        "Close t signal → close t+1 execution → return ending t+2. Cash earns selected risk-free rate."
    )
    if st.button("Run backtest", type="primary"):
        st.session_state["backtest"] = post(
            "/backtests",
            {
                **payload,
                "strategy": strategy,
                "lookback": window,
                "frequency": frequency,
                "cost_bps": cost,
                "target_vol": target,
            },
        )
    if "backtest" in st.session_state:
        saved = st.session_state["backtest"]
        with st.expander("Saved run parameters"):
            st.json(saved["parameters"])
        data = saved["results"]
        cards(data["metrics"])
        tab1, tab2, tab3 = st.tabs(["Equity & Drawdown", "Costs & Turnover", "Metrics"])
        with tab1:
            line(data["path"], "Net equity", ["wealth"])
            line(data["drawdown"], "Strategy drawdown")
        with tab2:
            line(data["path"], "Turnover and proportional costs", ["turnover", "cost"])
        with tab3:
            st.dataframe(data["metrics"])
elif page == "Data Quality":
    st.json(dataset["quality"])
    st.info(
        "Suspicious but valid observations are retained. Missing weekdays can be exchange holidays."
    )
    upload = st.file_uploader("Import adjusted OHLC CSV", type="csv")
    source = st.text_input("Source label", "User CSV")
    if upload and st.button("Validate and import"):
        post("/ingest", {"csv": upload.getvalue().decode(), "source": source})
        st.rerun()
elif page == "Research Reports":
    st.write(
        "Generate an auditable report covering comparison, portfolio, factors, strategies and quality."
    )
    if st.button("Generate research report", type="primary"):
        run = post("/reports", payload)
        st.session_state["report_id"] = run["run_id"]
    history = get("/research/runs")
    reports = [r["id"] for r in history if r["kind"] == "report"]
    if reports:
        selected = st.selectbox("Saved report", reports)
        response = httpx.get(API + f"/reports/{selected}", headers=HEADERS, timeout=60)
        response.raise_for_status()
        st.download_button(
            "Download Markdown report",
            response.text,
            file_name=f"MarketPulse-{selected[:8]}.md",
            mime="text/markdown",
        )
        st.markdown(response.text)
    st.dataframe(history, hide_index=True, width="stretch")
st.divider()
st.caption(
    "Research support • past returns are not forecasts • null ratios mean undefined, not zero"
)
