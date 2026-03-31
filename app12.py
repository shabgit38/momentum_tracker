# IGNORE THIS FILE, THIS IS A DIFFERENT DASHBOARD

import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Stock Dashboard", layout="wide")

st.title("Stock Dashboard")

with st.sidebar:
    ticker = st.text_input("Ticker", value="AAPL").strip().upper()
    period = st.selectbox("Price History", ["1y", "2y", "5y", "max"], index=1)
    show_volume = st.checkbox("Show Volume", value=True)

if not ticker:
    st.info("Enter a ticker symbol to begin.")
    st.stop()


@st.cache_data(show_spinner=False, ttl=60 * 30)
def load_data(symbol: str, period: str) -> pd.DataFrame:
    data = yf.download(symbol, period=period, auto_adjust=False, progress=False)
    data = data.rename(columns=str.title)
    data = data.dropna()
    return data


data = load_data(ticker, period)

if data.empty:
    st.error("No data returned. Check the ticker and try again.")
    st.stop()

if isinstance(data.columns, pd.MultiIndex):
    tickers = data.columns.get_level_values(-1).unique()
    if len(tickers) == 1:
        data = data.xs(tickers[0], axis=1, level=-1)
    else:
        st.error(
            "Multiple tickers detected. Please enter a single ticker symbol."
        )
        st.stop()

# Normalize column names for consistent downstream access.
data.columns = [str(col).title() for col in data.columns]

required_cols = {"High", "Low", "Close"}
missing_cols = sorted(required_cols - set(data.columns))
if missing_cols:
    st.error(
        f"Missing expected columns: {', '.join(missing_cols)}. "
        f"Received columns: {', '.join(map(str, data.columns))}."
    )
    st.stop()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def pivots_from_ohlc(high: float, low: float, close: float) -> dict:
    pivot = (high + low + close) / 3.0
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    return {
        "Pivot": pivot,
        "R1": r1,
        "R2": r2,
        "R3": r3,
        "S1": s1,
        "S2": s2,
        "S3": s3,
    }


# Compute EMAs
ema_periods = [10, 20, 50, 100, 200]
ema_df = pd.DataFrame(index=data.index)
for span in ema_periods:
    ema_df[f"EMA {span}"] = ema(data["Close"], span)


# Timeframe high/low calculations
now = data.index[-1]


def window_stats(days: int) -> dict:
    window = data[data.index >= now - timedelta(days=days)]
    if window.empty:
        return {"Low": np.nan, "High": np.nan}
    return {"Low": window["Low"].min(), "High": window["High"].max()}


def resample_stats(freq: str, periods: int) -> dict:
    res = data.resample(freq).agg({"Low": "min", "High": "max"})
    res = res.tail(periods)
    if res.empty:
        return {"Low": np.nan, "High": np.nan}
    return {"Low": res["Low"].min(), "High": res["High"].max()}


stats = {
    "Weekly (52w)": resample_stats("W", 52),
    "Monthly (12m)": resample_stats("ME", 12),
    "3 Months": window_stats(90),
    "6 Months": window_stats(182),
    "1 Year": window_stats(365),
}


# Pivot levels from previous trading day
prev_day = data.iloc[-2] if len(data) >= 2 else data.iloc[-1]
levels = pivots_from_ohlc(prev_day["High"], prev_day["Low"], prev_day["Close"])


# Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Price with EMAs")
    chart_df = pd.concat([data["Close"], ema_df], axis=1)
    st.line_chart(chart_df)
    if show_volume:
        if "Volume" in data.columns:
            st.subheader("Volume")
            st.bar_chart(data["Volume"])
        else:
            st.info("Volume data not available for this ticker.")

with col2:
    st.subheader("High / Low Summary")
    stats_table = pd.DataFrame(stats).T
    st.dataframe(stats_table.style.format("{:.2f}"), width='stretch')

    st.subheader("Pivot Levels (Prev Day)")
    pivot_table = pd.DataFrame(levels, index=["Level"]).T
    st.dataframe(pivot_table.style.format("{:.2f}"), width='stretch')


st.caption(f"Data source: Yahoo Finance via yfinance. Last updated: {now.date()}.")
