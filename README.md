# SoR (TikTok DSA) — Minimal Analysis Toolkit

This folder contains three simple, harmonized Python scripts to explore values, compute daily counts, and plot time series for SoR (TikTok DSA) datasets.

**Note:** This code and documentation were generated with the assistance of a Large Language Model (LLM).

## Scripts

- **column_value_counts.py** — Explore a single column across many CSV files and count unique values (normalized).
  - Output: `outputs/column_value_counts/{dataset}_{column}_value_counts.csv` (count,value)

- **daily_counts.py** — Count rows per day from many CSVs using AND across columns and OR across values (equals/contains, normalized).
  - Output: `outputs/daily_counts/{dataset}_{filters_summary}_daily.csv` (date,count)

- **plot_timeseries.py** — Plot one or more time series from CSVs (date,count). Supports date window, missing-date completion, event line, ticks, title/axes.
  - Output: `outputs/plot_timeseries/{auto_or_custom}.png`

## Requirements

- Python 3.9+
- `pip install pandas tqdm matplotlib`

## Outputs

- `outputs/column_value_counts/`
- `outputs/daily_counts/`
- `outputs/plot_timeseries/`

Directories are created automatically if needed.

## Usage

### 1) Explore a column (unique values + counts)

- Edit settings at the top of `column_value_counts.py`:
  - `DATA_DIRECTORY`, `COLUMN_NAME`, `OUTPUT_CSV` (optional), `CHUNKSIZE`, `N_WORKERS`
- Run:
  ```bash
  python column_value_counts.py
  ```
- Output CSV: `count,value` sorted by count.

### 2) Compute daily counts with filters

- Edit settings at the top of `daily_counts.py`:
  - `DATA_DIRECTORY`, `DATE_COLUMN` (default `application_date`)
  - `FILTERS` (AND across columns, OR across values; normalized; `mode`: equals|contains)
  - `OUTPUT_CSV` (optional), `CHUNKSIZE`, `N_WORKERS`

**Examples:**
```python
# RO only
FILTERS = {'territorial_scope': {'mode': 'contains', 'values': ['["RO"]']}}

# Thematic (AND across columns, OR within each column)
FILTERS = {
  'territorial_scope': {'mode': 'equals', 'values': ['["RO"]']},
  'incompatible_content_ground': {'mode': 'contains', 'values': ['political', 'advertising']},
}
```

- Run:
  ```bash
  python daily_counts.py
  ```
- Output CSV: `date,count`.

### 3) Plot time series

- Edit settings at the top of `plot_timeseries.py`:
  - `INPUTS = [(path, label), ...]`  (each CSV must be `date,count`)
  - `START_DATE`, `END_DATE` (optional)
  - `COMPLETE_MISSING_DATES` (True/False)
  - `TICK_FREQUENCY`: 'daily'|'weekly'|'monthly'|None
  - `EVENT_DATE`/label/color (optional)
  - `TITLE`, `X_LABEL`, `Y_LABEL` (default: "Time series", "Date", "SoR's")
  - `SHOW_PLOT`, `SAVE_PNG`, `OUTPUT_PNG`, `FIGSIZE`
- Run:
  ```bash
  python plot_timeseries.py
  ```
- Output PNG in `outputs/plot_timeseries/`.

## Settings Summary

- **Normalization**
  - Text comparisons use NFKD + casefold for robust, case/diacritics-insensitive matching.

- **Filters (daily_counts.py)**
  - AND across columns; OR across values within the same column.
  - `mode: 'equals'` for exact matches on normalized values (faster).
  - `mode: 'contains'` for substring matches (free-text, serialized lists like territorial_scope).

- **Performance**
  - Read CSVs in chunks for memory efficiency.
  - Multiprocessing (one process per file) with `freeze_support()` enabled for Windows.

## Quick Examples

- **Column exploration** (incompatible_content_explanation):
  - Set `COLUMN_NAME = 'incompatible_content_explanation'` and run `python column_value_counts.py`.

- **Daily counts for Art.16** in decision_facts:
  ```python
  FILTERS = {'decision_facts': {'mode': 'contains', 'values': ['art. 16 dsa']}}
  ```
  - Run `python daily_counts.py`.

- **Plot a single series:**
  ```python
  INPUTS = [
    (r'outputs/daily_counts/23-11-2024_art16_ro_daily.csv', 'Art.16 RO')
  ]
  ```
  - Run `python plot_timeseries.py`.

## Troubleshooting

- **"No CSV files found"**: check `DATA_DIRECTORY` or file paths.
- **"CSV must contain 'date' and 'count'"**: ensure plotting inputs are from `daily_counts.py` or similar.
- **Performance**: increase `CHUNKSIZE`, verify disk speed, and manage number of series per figure.

## Attribution

This toolkit was generated with the assistance of a Large Language Model (LLM) and refined for this research workflow.

