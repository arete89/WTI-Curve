import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, timedelta
import warnings

warnings.filterwarnings("ignore")

# ── Contract helpers ──────────────────────────────────────────────────────────
MONTH_CODE = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
               7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}

CONTRACT_DATE = {v: k for k, v in MONTH_CODE.items()}  # reverse map

def cl_ticker(year: int, month: int) -> str:
    return f"CL{MONTH_CODE[month]}{str(year)[-2:]}.NYM"

def build_tickers(ref_date: date, n_months: int = 18) -> list[tuple[date, str]]:
    """(expiry_date, ticker) for n_months starting from next month."""
    pairs = []
    m, y = ref_date.month + 1, ref_date.year
    if m > 12:
        m, y = 1, y + 1
    for _ in range(n_months):
        pairs.append((date(y, m, 1), cl_ticker(y, m)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return pairs

# ── Batch fetch ───────────────────────────────────────────────────────────────
def build_curve(ref_date: date, ticker_pairs: list[tuple[date, str]]) -> pd.Series:
    """Batch-download all contracts and return prices as of ref_date."""
    tickers = [t for _, t in ticker_pairs]
    date_map = {t: d for d, t in ticker_pairs}

    start = ref_date - timedelta(days=7)
    end   = ref_date + timedelta(days=1)

    hist = yf.download(tickers, start=start, end=end, progress=False, auto_adjust=True)
    if hist.empty:
        return pd.Series(dtype=float)

    close = hist["Close"] if isinstance(hist.columns, pd.MultiIndex) else hist

    data = {}
    for ticker in tickers:
        if ticker in close.columns:
            s = close[ticker].dropna()
            if not s.empty:
                data[date_map[ticker]] = float(s.iloc[-1])

    return pd.Series(data).sort_index()

def fetch_spot_history(ref_date: date, days: int = 30) -> pd.Series:
    """Return daily spot closes for the past `days` calendar days ending on ref_date."""
    start = ref_date - timedelta(days=days + 10)  # extra buffer for weekends/holidays
    end   = ref_date + timedelta(days=1)
    hist  = yf.download("CL=F", start=start, end=end, progress=False, auto_adjust=True)
    if hist.empty:
        return pd.Series(dtype=float)
    close = hist["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    # Keep only the last `days` calendar days
    cutoff = pd.Timestamp(ref_date) - pd.Timedelta(days=days)
    return close[close.index >= cutoff]

# ── Main ──────────────────────────────────────────────────────────────────────
today     = date.today()
week_ago  = today - timedelta(weeks=1)
month_ago = today - timedelta(days=30)

print(f"Today:     {today}")
print(f"Week ago:  {week_ago}")
print(f"Month ago: {month_ago}")

tickers = build_tickers(today, n_months=20)

print("\nFetching spot history (90 days) …")
spot_history = fetch_spot_history(today, days=90)
print(f"  CL=F: {len(spot_history)} trading days, latest ${float(spot_history.iloc[-1]):.2f}" if not spot_history.empty else "  CL=F: unavailable")

print("Fetching today's curve …")
curve_today = build_curve(today, tickers)

print("Fetching week-ago curve …")
curve_week  = build_curve(week_ago, tickers)

print("Fetching month-ago curve …")
curve_month = build_curve(month_ago, tickers)

print(f"\nContracts returned — today: {len(curve_today)}, "
      f"week ago: {len(curve_week)}, month ago: {len(curve_month)}")

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 6))

colors = {
    "today": "#1f77b4",
    "week":  "#ff7f0e",
    "month": "#2ca02c",
    "spot":  "#d62728",
}

# Spot history — solid line on the left
last_spot_date  = spot_history.index[-1].date() if not spot_history.empty else None
last_spot_price = float(spot_history.iloc[-1])  if not spot_history.empty else None

if not spot_history.empty:
    spot_dates = [d.date() for d in spot_history.index]
    ax.plot(spot_dates, spot_history.values,
            color=colors["spot"], linewidth=2.2,
            label=f"Spot CL=F (90d)")

# Grey shaded divider between spot history and forward curve
if last_spot_date and not curve_today.empty:
    divider_start = last_spot_date
    divider_end   = curve_today.index[0]
    ax.axvline(divider_start, color="grey", linewidth=1.0, linestyle="--", alpha=0.7)

# Forward curves — all dashed; connect spot's last point to the first contract


if not curve_month.empty:
    ax.plot(curve_month.index, curve_month.values,
            color=colors["month"], linewidth=1.8, linestyle="--",
            marker="o", markersize=4, label=f"1 month ago  ({month_ago:%b %d, %Y})")

if not curve_week.empty:
    ax.plot(curve_week.index, curve_week.values,
            color=colors["week"], linewidth=1.8, linestyle="--",
            marker="s", markersize=4, label=f"1 week ago   ({week_ago:%b %d, %Y})")

if not curve_today.empty:
    # Draw a thin connector from spot's last close to the first futures contract
    if last_spot_date and last_spot_price:
        ax.plot([last_spot_date, curve_today.index[0]],
                [last_spot_price, curve_today.iloc[0]],
                color=colors["today"], linewidth=1.2, linestyle=":")
    ax.plot(curve_today.index, curve_today.values,
            color=colors["today"], linewidth=2.2, linestyle="--",
            marker="o", markersize=5, label=f"Latest fwd   ({today:%b %d, %Y})")

ax.set_title(f"WTI Forward Curve — {today:%B %d, %Y}", fontsize=14, fontweight="bold")
ax.set_xlabel("Contract Expiry", fontsize=11)
ax.set_ylabel("Price (USD/bbl)", fontsize=11)

ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.xticks(rotation=30, ha="right")

ax.legend(fontsize=9, framealpha=0.9)
ax.grid(True, linestyle=":", alpha=0.5)
ax.yaxis.set_major_formatter(plt.FormatStrFormatter("$%.1f"))

plt.tight_layout()
out_path = "wti_forward_curve.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved → {out_path}")
plt.show()
