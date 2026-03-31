import pandas as pd
import yfinance as yf


def get_stock_data(ticker):
    df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
    df.dropna(inplace=True)
    # yfinance ≥0.2 always returns MultiIndex columns even for a single ticker;
    # flatten to simple column names like "Close", "High", etc.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def get_weekly_close(df):
    """Return the most recent completed weekly close (Friday)."""
    weekly = df["Close"].resample("W").last()
    if not weekly.empty:
        weekly = weekly.iloc[:-1]
    return float(weekly.iloc[-1]) if not weekly.empty else None


def get_monthly_close(df):
    """Return the most recent completed monthly close."""
    monthly = df["Close"].resample("ME").last()
    if not monthly.empty:
        monthly = monthly.iloc[:-1]
    return float(monthly.iloc[-1]) if not monthly.empty else None


def get_high_low_resampled(df):
    df = df.copy()
    df.index = pd.to_datetime(df.index)

    # Drop current incomplete week
    last_complete_date = df.resample("W-FRI").last().index[-2]
    df = df[df.index <= last_complete_date]

    weekly  = df.resample("W-FRI").agg({"High": "max", "Low": "min"})
    monthly = df.resample("ME").agg({"High": "max", "Low": "min"})

    latest = df.index.max()
    df_3m = df[df.index >= latest - pd.DateOffset(months=3)]
    df_6m = df[df.index >= latest - pd.DateOffset(months=6)]
    df_1y = df[df.index >= latest - pd.DateOffset(years=1)]

    return {
        "1W": (float(weekly.iloc[-1]["High"]),  float(weekly.iloc[-1]["Low"])),
        "1M": (float(monthly.iloc[-1]["High"]), float(monthly.iloc[-1]["Low"])),
        "3M": (float(df_3m["High"].max()),      float(df_3m["Low"].min())),
        "6M": (float(df_6m["High"].max()),      float(df_6m["Low"].min())),
        "1Y": (float(df_1y["High"].max()),      float(df_1y["Low"].min())),
    }
