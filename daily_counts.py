#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Count rows per day with optional filters.
- Reads CSVs in chunks (memory-friendly)
- Uses multiprocessing (one process per file)
- Robust date parsing (handles 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS')
- Filters: AND across columns, OR across values within a column
- Output: CSV with columns: date,count
"""

import os
import pandas as pd
from collections import Counter
from multiprocessing import Pool, cpu_count, freeze_support
from tqdm import tqdm
import unicodedata

# ===================== SETTINGS =====================
DATA_DIRECTORY = r'F:\M1\RECHERCHE\DSA TRANSPARENCY\datateam\DSA TRANSPARENCY DATABASE\DATASET\23-11-2024'
DATE_COLUMN = 'application_date'     # e.g., 'application_date'
OUTPUT_CSV = None                    # None => auto-generate; otherwise explicit path

# Filters:
# - Multiple columns = AND (all columns must match)
# - Multiple values in the same column = OR (at least one value must match)
# Example:
#   {'col1': {'mode': 'contains', 'values': ['a', 'b']}, 'col2': {'mode': 'equals', 'values': ['x']}}
#   matches rows where: (col1 contains 'a' OR 'b') AND (col2 equals 'x')
# mode: 'equals' (exact match) or 'contains' (substring search)
FILTERS = {
    'incompatible_content_explanation': {'mode': 'equals', 'values': ['allowing young people to explore and learn safely during their unique phase of development is our priority. we do not allow youth exploitation and abuse, including child sexual abuse material (csam), nudity, grooming, sextortion, solicitation, pedophilia, and physical or psychological abuse of young people. this includes content that is real, fictional, digitally created, and shown in fine art or objects.we proactively enforce our community guidelines through a mix of technology and human moderation. we have detected this policy violation using automated measures. we have used automated measures in making this decision.']},
    #'territorial_scope': {'mode': 'contains', 'values': ['["RO"]']},
    # 'incompatible_content_ground': {'mode': 'contains', 'values': ['political', 'advertising', 'influencer']},
    # 'decision_facts': {'mode': 'contains', 'values': ['art. 16 dsa', 'eldigital services act']},
}

CHUNKSIZE = 10000
N_WORKERS = None
# =====================================================

def normalize_text(s):
    """Normalize text for case/diacritics-insensitive matching.

    Applies NFKD unicode normalization (decompose accents) and casefold
    (robust lowercase). Non-strings are returned unchanged.
    """
    if not isinstance(s, str):
        return s
    return unicodedata.normalize('NFKD', s).casefold()

def parse_date_robust(x):
    """Parse a date string robustly and return a date object or None.

    Accepts common formats like 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS'.
    Returns None on parsing failure.
    """
    if pd.isna(x):
        return None
    try:
        dt = pd.to_datetime(x, errors='coerce', format='mixed')
        return None if pd.isna(dt) else dt.date()
    except Exception:
        return None

def list_csv_files(root_dir):
    """Return a list of CSV file paths (relative to root_dir), recursively."""
    files = []
    for r, _, fs in os.walk(root_dir):
        for fn in fs:
            if fn.lower().endswith('.csv'):
                files.append(os.path.relpath(os.path.join(r, fn), root_dir))
    return files

def build_mask_for_column(series_str, mode, values_norm):
    """Build a boolean mask for one column.

    - equals: exact match against any of values_norm (OR within column)
    - contains: substring match against any of values_norm (OR within column)
    Returns: pd.Series[bool]
    """
    # OR across values: at least one value must match
    if mode == 'equals':
        return series_str.isin(values_norm)
    # contains
    return series_str.map(lambda x: any(v in x for v in values_norm))

def process_file(rel_path):
    """Process one CSV: apply filters, count rows per day, return Counter.

    AND logic across columns, OR logic across values within a column.
    Dates are parsed robustly before counting.
    """
    file_path = os.path.join(DATA_DIRECTORY, rel_path)
    date_counter = Counter()

    try:
        usecols = [DATE_COLUMN] + list(FILTERS.keys())
        usecols = list(dict.fromkeys(usecols))  # unique, preserve order
        for chunk in pd.read_csv(file_path, dtype=str, chunksize=CHUNKSIZE,
                                 usecols=usecols, on_bad_lines='skip', low_memory=False):
            # Global mask (AND across columns)
            mask = pd.Series(True, index=chunk.index)

            for col, cfg in FILTERS.items():
                if col not in chunk.columns:
                    mask &= False
                    break
                mode = cfg.get('mode', 'equals')
                values = cfg.get('values', [])
                values_norm = [normalize_text(v) for v in values]
                col_norm = chunk[col].astype(str).map(normalize_text)
                mask &= build_mask_for_column(col_norm, mode, values_norm)

            filtered = chunk[mask] if FILTERS else chunk

            if DATE_COLUMN in filtered.columns:
                dates = filtered[DATE_COLUMN].map(parse_date_robust).dropna()
                date_counter.update(dates)
    except Exception as e:
        print(f"[WARN] Skipped {file_path}: {e}")

    return date_counter

def summarize_filters_for_filename(filters):
    """Create a compact string summarizing filters for the output filename."""
    if not filters:
        return "all"
    parts = []
    for col, cfg in filters.items():
        mode = cfg.get('mode', 'equals')
        vals = cfg.get('values', [])
        vals_join = "_".join(str(v) for v in vals[:5])  # limit filename length
        frag = f"{col}-{mode}-{vals_join}"
        frag = frag.replace(' ', '_').replace('/', '_').replace('\\', '_').replace('[','').replace(']','')
        parts.append(frag[:60])
    return "__".join(parts)[:120]

def generate_output_filename(data_directory, filters):
    """Build output filename: outputs/daily_counts/{dataset}_{filters_summary}_daily.csv."""
    dataset = os.path.basename(os.path.normpath(data_directory))
    safe_dataset = dataset.replace(' ', '_').replace('/', '_').replace('\\', '_')
    summary = summarize_filters_for_filename(filters)
    return os.path.join('outputs', 'daily_counts', f"{safe_dataset}_{summary}_daily.csv")

def main():
    """Entry point: parallelize counting, merge results, write date,count CSV."""
    freeze_support()

    out_path = OUTPUT_CSV or generate_output_filename(DATA_DIRECTORY, FILTERS)
    csv_files = list_csv_files(DATA_DIRECTORY)
    if not csv_files:
        print(f"No CSV files found in {DATA_DIRECTORY}")
        return

    num_workers = min(cpu_count(), len(csv_files)) if N_WORKERS is None else N_WORKERS
    global_counter = Counter()

    with Pool(processes=num_workers) as pool:
        for cnt in tqdm(pool.imap(process_file, csv_files), total=len(csv_files), desc="Counting"):
            global_counter.update(cnt)

    if not global_counter:
        print("No matching rows found.")
        return

    df = pd.DataFrame(sorted(global_counter.items()), columns=['date', 'count'])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False, encoding='utf-8')
    print(f"[OK] Wrote: {out_path} ({len(df)} dates, total={df['count'].sum():,})")

if __name__ == '__main__':
    main()