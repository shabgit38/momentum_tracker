import pandas as pd


def add_ema(df):
    for span in [10, 20, 50, 100, 200]:
        df[f"EMA{span}"] = df["Close"].ewm(span=span, adjust=False).mean()
    return df


def pivot_points(df):
    """
    Classic floor pivot points using the last completed session's H/L/C.
    Returns Pivot + S1-S5 + R1-R5.
    """
    last = df.iloc[-1]
    H, L, C = float(last["High"]), float(last["Low"]), float(last["Close"])
    rng = H - L

    P  = (H + L + C) / 3
    R1 = 2 * P - L
    S1 = 2 * P - H
    R2 = P + rng
    S2 = P - rng
    R3 = H + 2 * (P - L)
    S3 = L - 2 * (H - P)
    R4 = R3 + rng
    S4 = S3 - rng
    R5 = R4 + rng
    S5 = S4 - rng

    return {
        "Pivot": P,
        "R1": R1, "R2": R2, "R3": R3, "R4": R4, "R5": R5,
        "S1": S1, "S2": S2, "S3": S3, "S4": S4, "S5": S5,
    }
