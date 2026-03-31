import streamlit as st
import pandas as pd

from data_fetch import get_stock_data, get_weekly_close, get_monthly_close, get_high_low_resampled
from indicators import add_ema, pivot_points

st.set_page_config(page_title="Stock Technical Dashboard", layout="wide")
st.title("Stock Technical Dashboard")

raw_input = st.text_input(
    "Enter ticker symbols (comma-separated)",
    placeholder="e.g. AAPL, MSFT, GOOGL"
)

tickers = [t.strip().upper()+".NS" for t in raw_input.split(",") if t.strip()]

if not tickers:
    st.warning("Enter at least one ticker symbol.")
    st.stop()

EMA_COLS = ["EMA10", "EMA20", "EMA50", "EMA100", "EMA200"]
ROW_PX   = 35   # approximate height of one table row
HDR_PX   = 38   # table header height


def _insert_current(ordered: list[tuple[str, float]], current_price: float) -> list[dict]:
    """
    Given a list of (label, value) sorted descending by value,
    insert ▶ Current adjacent to the closest level.
    """
    closest = min(range(len(ordered)), key=lambda i: abs(ordered[i][1] - current_price))
    rows = []
    for i, (label, val) in enumerate(ordered):
        if i == closest:
            if current_price >= val:
                rows.append({"Level": "▶ Current", "Value": round(current_price, 2)})
                rows.append({"Level": label,       "Value": round(val, 2)})
            else:
                rows.append({"Level": label,       "Value": round(val, 2)})
                rows.append({"Level": "▶ Current", "Value": round(current_price, 2)})
        else:
            rows.append({"Level": label, "Value": round(val, 2)})
    return rows


def build_ohlc_ema_table(df, current_price: float) -> pd.DataFrame:
    last = df.iloc[-1]
    items = {
        "Open":   round(float(last["Open"]),   2),
        "High":   round(float(last["High"]),   2),
        "Low":    round(float(last["Low"]),    2),
        "EMA10":  round(float(last["EMA10"]),  2),
        "EMA20":  round(float(last["EMA20"]),  2),
        "EMA50":  round(float(last["EMA50"]),  2),
        "EMA100": round(float(last["EMA100"]), 2),
        "EMA200": round(float(last["EMA200"]), 2),
    }
    ordered = sorted(items.items(), key=lambda x: x[1], reverse=True)
    return pd.DataFrame(_insert_current(ordered, current_price)).set_index("Level")


def build_pivot_table(df, current_price: float) -> pd.DataFrame:
    pivots = pivot_points(df)
    ordered = [
        ("R5",    pivots["R5"]),
        ("R4",    pivots["R4"]),
        ("R3",    pivots["R3"]),
        ("R2",    pivots["R2"]),
        ("R1",    pivots["R1"]),
        ("Pivot", pivots["Pivot"]),
        ("S1",    pivots["S1"]),
        ("S2",    pivots["S2"]),
        ("S3",    pivots["S3"]),
        ("S4",    pivots["S4"]),
        ("S5",    pivots["S5"]),
    ]
    return pd.DataFrame(_insert_current(ordered, current_price)).set_index("Level")


def build_hl_table(df, current_price: float) -> pd.DataFrame:
    wc = get_weekly_close(df)
    mc = get_monthly_close(df)
    hl = get_high_low_resampled(df)

    items: dict[str, float] = {}
    if wc is not None:
        items["W Close"] = round(wc, 2)
    if mc is not None:
        items["M Close"] = round(mc, 2)
    for period in ["1W", "1M", "3M", "6M", "1Y"]:
        h, l = hl[period]
        items[f"{period} High"] = round(float(h), 2)
        items[f"{period} Low"]  = round(float(l), 2)

    ordered = sorted(items.items(), key=lambda x: x[1], reverse=True)
    return pd.DataFrame(_insert_current(ordered, current_price)).set_index("Level")


def generate_summary(df, current_price: float) -> str:
    last   = df.iloc[-1]
    parts  = []

    # ── EMA position ──────────────────────────────────────────────────────────
    ema_vals = {e: float(last[e]) for e in EMA_COLS}
    above = [e for e in EMA_COLS if current_price > ema_vals[e]]
    below = [e for e in EMA_COLS if current_price < ema_vals[e]]

    if above and below:
        parts.append(f"above {above[-1]}, below {below[0]}")
    elif above:
        parts.append("above all EMAs")
    else:
        parts.append("below all EMAs")

    # ── Pivot position ────────────────────────────────────────────────────────
    pivots  = pivot_points(df)
    p_order = [
        ("R5", pivots["R5"]), ("R4", pivots["R4"]), ("R3", pivots["R3"]),
        ("R2", pivots["R2"]), ("R1", pivots["R1"]),
        ("Pivot", pivots["Pivot"]),
        ("S1", pivots["S1"]), ("S2", pivots["S2"]), ("S3", pivots["S3"]),
        ("S4", pivots["S4"]), ("S5", pivots["S5"]),
    ]
    lvl_above = [(l, v) for l, v in p_order if v > current_price]   # levels above price
    lvl_below = [(l, v) for l, v in p_order if v < current_price]   # levels below price

    if lvl_above and lvl_below:
        nearest_above = lvl_above[-1][0]   # last in desc list = nearest level above price
        nearest_below = lvl_below[0][0]    # first in desc list = nearest level below price
        parts.append(f"between {nearest_above} and {nearest_below}")
    elif not lvl_above:
        parts.append("above R5")
    else:
        parts.append("below S5")

    # ── Period H/L position ───────────────────────────────────────────────────
    hl = get_high_low_resampled(df)
    all_hl: dict[str, float] = {}
    for period in ["1W", "1M", "3M", "6M", "1Y"]:
        h, l = hl[period]
        all_hl[f"{period} High"] = float(h)
        all_hl[f"{period} Low"]  = float(l)

    closest_label, closest_val = min(all_hl.items(), key=lambda x: abs(x[1] - current_price))
    direction = "above" if current_price > closest_val else ("below" if current_price < closest_val else "at")
    parts.append(f"{direction} {closest_label}")

    return f"**▶ {round(current_price, 2)}** — " + " · ".join(parts)


# ── Fetch all tickers ─────────────────────────────────────────────────────────
progress   = st.progress(0, text="Fetching data…")
stock_data: dict = {}

for i, ticker in enumerate(tickers):
    try:
        df = get_stock_data(ticker)
        if df.empty:
            stock_data[ticker] = None
        else:
            stock_data[ticker] = add_ema(df)
    except Exception as e:
        stock_data[ticker] = e
    progress.progress((i + 1) / len(tickers), text=f"Fetched {ticker}")

progress.empty()

# ── Render one card per ticker ────────────────────────────────────────────────
for ticker in tickers:
    data = stock_data[ticker]
    st.markdown(f"### {ticker}")

    if data is None:
        st.warning(f"{ticker}: no data returned")
        st.divider()
        continue
    if isinstance(data, Exception):
        st.error(f"{ticker}: {data}")
        st.divider()
        continue

    df            = data
    current_price = float(df.iloc[-1]["Close"])

    try:
        ohlc_ema_df = build_ohlc_ema_table(df, current_price)
        pivot_df    = build_pivot_table(df, current_price)
        hl_df       = build_hl_table(df, current_price)
        summary     = generate_summary(df, current_price)
    except Exception as e:
        st.error(f"{ticker} error: {e}")
        st.divider()
        continue

    # Summary always visible
    st.markdown(summary)

    with st.expander("Show / Hide Tables", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.caption("OHLC & EMAs")
            st.dataframe(
                ohlc_ema_df.style.format("{:.2f}", na_rep="—"),
                width="stretch",
                height=len(ohlc_ema_df) * ROW_PX + HDR_PX,
            )

        with col2:
            st.caption("Pivot Levels")
            st.dataframe(
                pivot_df.style.format("{:.2f}", na_rep="—"),
                width="stretch",
                height=len(pivot_df) * ROW_PX + HDR_PX,
            )

        with col3:
            st.caption("Period High / Low")
            st.dataframe(
                hl_df.style.format("{:.2f}", na_rep="—"),
                width="stretch",
                height=len(hl_df) * ROW_PX + HDR_PX,
            )

    st.divider()

st.caption(
    "OHLC/EMAs & Pivots = last session · Period H/L = rolling window · "
    "▶ Current placed next to closest value in each table"
)
