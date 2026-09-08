# WTI-Curve
Plots the WTI crude oil forward curve using free data from Yahoo Finance via `yfinance`.

## What it shows

| Element | Description |
|---|---|
| **Red solid line** | 90-day spot price history (`CL=F`) |
| **Grey dashed line** | Divider between historical spot and forward curve |
| **Blue dashed line** | Today's forward curve (latest settle prices) |
| **Orange dashed line** | Forward curve snapshot from 1 week ago |
| **Green dashed line** | Forward curve snapshot from 1 month ago |

Up to 20 monthly NYMEX contracts are fetched (e.g. `CLV26.NYM`, `CLZ26.NYM`, …), starting from the next calendar month. Expired contracts are skipped automatically.

## Requirements

```
yfinance
pandas
matplotlib
```

Install with:

```bash
pip install yfinance pandas matplotlib
```

## Usage

```bash
python wti_forward_curve.py
```

Outputs `wti_forward_curve.png` in the current directory and opens an interactive plot window.

## Data source

All data is pulled from Yahoo Finance at runtime — no API key required. Prices reflect the most recent available close for each contract.
