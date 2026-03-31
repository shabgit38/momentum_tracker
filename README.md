# Stock Dashboard

Streamlit dashboard that shows:
- Weekly, monthly, 3‑month, 6‑month, and 1‑year low/high values
- Exponential moving averages (10/20/50/100/200)
- Pivot levels (S1/S2/S3/R1/R2/R3)

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Data is pulled via `yfinance` (Yahoo Finance). For best results, use US tickers (e.g., `AAPL`, `MSFT`).
- Pivot levels use the **previous trading day's** OHLC.
