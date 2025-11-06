#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plot one or more time series from CSV files with columns: date,count.
- Input is a single explicit list of (path, label) pairs
- Optional date window (start/end) and missing-date completion
- Optional vertical event line (date + label + color)
- X-axis tick frequency: daily | weekly | monthly | auto
- Output: show and/or save a PNG
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ===================== SETTINGS (minimal) =====================
# Declare the series to plot as explicit (path, label) pairs.
# Each CSV must have columns: date,count.
INPUTS = [
    (r'outputs\daily_counts\23-11-2024_incompatible_content_explanation-equals-allowing_young_peopl_daily.csv', 'Allowing young people'),
    # (r'outputs/daily_counts/series_b.csv', 'Series B'),
]

# Date window (None => use data range)
START_DATE = None    # e.g., '2024-10-01'
END_DATE   = None    # e.g., '2024-12-15'

# Complete missing days with 0 (recommended for smooth charts)
COMPLETE_MISSING_DATES = True

# Tick frequency on X axis: 'daily' | 'weekly' | 'monthly' | None (auto)
TICK_FREQUENCY = 'weekly'

# Vertical event line (None to disable)
EVENT_DATE  = '2024-11-24'   # e.g., '2024-11-24' or None
EVENT_LABEL = 'First round of the Romanian presidential election'
EVENT_COLOR = 'orange'

# Output
SHOW_PLOT = True
SAVE_PNG  = True
OUTPUT_PNG = None  # None => auto-generate from labels; or explicit path
FIGSIZE = (12, 6)
# Title and axis labels
TITLE = "Time series"
X_LABEL = "Date"
Y_LABEL = "SoR's"
# =====================================================


def load_series_from_csv(path: str):
    """Load a CSV with columns date,count as a pandas Series indexed by daily dates."""
    df = pd.read_csv(path)
    if 'date' not in df.columns or 'count' not in df.columns:
        raise ValueError(f"CSV must contain 'date' and 'count' columns: {path}")
    df = df[['date', 'count']].copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values('date')
    s = df.set_index('date')['count'].astype(int)
    return s


def complete_daily(s: pd.Series, start: pd.Timestamp | None, end: pd.Timestamp | None):
    """Reindex a series to daily frequency, filling missing days with 0."""
    data_start = s.index.min()
    data_end = s.index.max()
    srt = start if start is not None else data_start
    edt = end if end is not None else data_end
    idx = pd.date_range(start=srt, end=edt, freq='D')
    return s.reindex(idx, fill_value=0)


def infer_inputs():
    """Return the list of (path, label) pairs to plot."""
    return INPUTS or []


def set_tick_frequency(freq: str | None):
    """Configure x-axis tick locator/formatter based on desired frequency."""
    ax = plt.gca()
    if freq == 'daily':
        locator = mdates.DayLocator()
        fmt = mdates.DateFormatter('%d/%m/%Y')
    elif freq == 'weekly':
        locator = mdates.WeekdayLocator(byweekday=mdates.MO)
        fmt = mdates.DateFormatter('%d/%m/%Y')
    elif freq == 'monthly':
        locator = mdates.MonthLocator()
        fmt = mdates.DateFormatter('%b %Y')
    else:
        # auto
        locator = mdates.AutoDateLocator()
        fmt = mdates.ConciseDateFormatter(locator)

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(fmt)


def auto_output_name(series_meta: list[tuple[str, str]]):
    """Generate a default output PNG name from input labels."""
    # Use up to first two labels to keep name short
    labels = [lbl for _, lbl in series_meta]
    if not labels:
        base = "timeseries"
    elif len(labels) == 1:
        base = labels[0]
    else:
        base = f"{labels[0]}_vs_{labels[1]}"
    base = base.replace(' ', '_').replace('/', '_').replace('\\', '_')
    return os.path.join('outputs', 'plot_timeseries', f"{base}.png")


def main():
    series_meta = infer_inputs()
    if not series_meta:
        print("No input series found. Configure INPUT_CSV, INPUT_DIRECTORY, or INPUTS.")
        return

    # Print mapping file -> label for verification
    print("Series to plot:")
    for path, label in series_meta:
        print(f" - {label}: {path}")

    # Prepare date window
    start = pd.to_datetime(START_DATE) if START_DATE else None
    end   = pd.to_datetime(END_DATE) if END_DATE else None

    plt.figure(figsize=FIGSIZE)

    for path, label in series_meta:
        s = load_series_from_csv(path)
        if COMPLETE_MISSING_DATES:
            s = complete_daily(s, start, end)
        else:
            # Optionally bound without filling
            if start:
                s = s[s.index >= start]
            if end:
                s = s[s.index <= end]
        # Plot
        plt.plot(s.index, s.values, marker='o', linestyle='-', alpha=0.85, label=label)

    # Event line (optional)
    if EVENT_DATE:
        try:
            ev = pd.to_datetime(EVENT_DATE)
            plt.axvline(ev, color=EVENT_COLOR, linestyle='--', linewidth=2,
                        label=(EVENT_LABEL if EVENT_LABEL else EVENT_DATE))
        except Exception:
            print(f"[WARN] Invalid EVENT_DATE ignored: {EVENT_DATE}")

    # Axes styling
    plt.title(TITLE)
    plt.xlabel(X_LABEL)
    plt.ylabel(Y_LABEL)
    plt.ylim(bottom=0)
    set_tick_frequency(TICK_FREQUENCY)
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    # Output
    out_path = OUTPUT_PNG or auto_output_name(series_meta)
    if SAVE_PNG:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        plt.savefig(out_path, dpi=300, bbox_inches='tight')
        print(f"[OK] Saved PNG: {out_path}")
    if SHOW_PLOT:
        plt.show()
    else:
        plt.close()


if __name__ == "__main__":
    main()