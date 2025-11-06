#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Explore one column across many CSV files and count unique values.
- Reads each CSV in chunks (memory efficient)
- Uses multiprocessing (one process per file) for speed
- Normalizes text (NFKD + casefold) so similar strings are grouped
- Outputs a CSV sorted by count, with columns: count,value
"""

import os
import pandas as pd
from collections import Counter
from multiprocessing import Pool, cpu_count, freeze_support
from tqdm import tqdm
import unicodedata

# ===================== SETTINGS =====================
DATA_DIRECTORY = r'F:\M1\RECHERCHE\DSA TRANSPARENCY\datateam\DSA TRANSPARENCY DATABASE\DATASET\23-11-2024'   # Root folder containing CSV files (subfolders allowed)
COLUMN_NAME   = 'incompatible_content_explanation'         # Column to explore
OUTPUT_CSV    = None                    # Optional manual override (e.g., 'outputs/my_counts.csv'); set None to auto-generate
CHUNKSIZE     = 10000                   # Rows per reading block (lower = less RAM, higher = faster)
N_WORKERS     = None                    # None -> use min(#CPU, #files); or set a number (e.g., 4)
# =========================================================

def normalize_text(text):
    """Return a normalized version of input text.

    - Applies NFKD unicode normalization (decompose accents)
    - Applies casefold (robust lowercase) for case-insensitive grouping

    Args:
        text: Any value; only strings are normalized.

    Returns:
        The normalized string, or the original value if not a string.
    """
    if not isinstance(text, str):
        return text
    # NFKD decomposes accents; casefold lowers and normalizes case
    return unicodedata.normalize('NFKD', text).casefold()

def process_file(rel_path):
    """Process one CSV file and count occurrences in the target column.

    Reads the file in chunks to limit memory usage, normalizes values,
    and updates a Counter with value frequencies.

    Args:
        rel_path: CSV path relative to DATA_DIRECTORY.

    Returns:
        collections.Counter mapping normalized value -> count for this file.
    """
    file_path = os.path.join(DATA_DIRECTORY, rel_path)
    counter = Counter()
    try:
        for chunk in pd.read_csv(
            file_path,
            dtype=str,
            chunksize=CHUNKSIZE,
            usecols=[COLUMN_NAME],
            on_bad_lines='skip',
            low_memory=False
        ):
            if COLUMN_NAME in chunk.columns:
                vals = chunk[COLUMN_NAME].dropna().astype(str).map(normalize_text)
                counter.update(vals)
    except Exception as e:
        print(f"[WARN] Skipped {file_path}: {e}")
    return counter

def list_csv_files(root_dir):
    """List all CSV files (recursively) under a root directory.

    Args:
        root_dir: Directory to scan.

    Returns:
        List of CSV file paths, relative to root_dir.
    """
    files = []
    for r, _, fs in os.walk(root_dir):
        for fn in fs:
            if fn.lower().endswith('.csv'):
                files.append(os.path.relpath(os.path.join(r, fn), root_dir))
    return files

def generate_output_filename(column_name, data_directory):
    """Generate output filename: outputs/column_value_counts/{dataset}_{column}_value_counts.csv.

    Always includes the dataset folder name (last segment of data_directory)
    and a sanitized column name.

    Args:
        column_name: Name of the column being analyzed.
        data_directory: Path to the data directory.

    Returns:
        Output file path (e.g., 'outputs/column_value_counts/23-11-2024_decision_facts_value_counts.csv').
    """
    safe_col = column_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    dataset_name = os.path.basename(os.path.normpath(data_directory))
    safe_dataset = dataset_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"{safe_dataset}_{safe_col}_value_counts.csv"
    return os.path.join('outputs', 'column_value_counts', filename)

def main():
    """Entry point: aggregate counts over all CSV files and write a CSV output.

    - Collects all CSV files under DATA_DIRECTORY
    - Uses a process pool to process files in parallel
    - Merges per-file Counters into a global frequency table
    - Saves a CSV sorted by descending count with columns [count, value]
    """
    freeze_support()
    
    # Determine output filename: manual override if provided, else auto-generate
    output_path = OUTPUT_CSV or generate_output_filename(COLUMN_NAME, DATA_DIRECTORY)
    
    csv_files = list_csv_files(DATA_DIRECTORY)
    if not csv_files:
        print(f"No CSV files found in {DATA_DIRECTORY}")
        return

    num_workers = min(cpu_count(), len(csv_files)) if N_WORKERS is None else N_WORKERS
    global_counter = Counter()

    with Pool(processes=num_workers) as pool:
        for cnt in tqdm(pool.imap(process_file, csv_files), total=len(csv_files), desc="Exploring"):
            global_counter.update(cnt)

    if global_counter:
        df = pd.DataFrame(
            [(c, v) for v, c in global_counter.items()],
            columns=['count', 'value']
        ).sort_values('count', ascending=False)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"[OK] Wrote: {output_path} ({len(df)} rows)")
    else:
        print("No values collected (missing or empty column).")

if __name__ == '__main__':
    main()