"""Tracker tool: read/classify (delegates to the kernel) and atomic updates.

The decision logic is NOT reimplemented here - it imports tracker_review.py,
the deterministic policy kernel that lives next to the CSV.
"""
import csv
import os
import sys

from .. import config

# tracker_review.py lives in 00_Admin (one level up from the agent package).
sys.path.insert(0, config.ADMIN_DIR)
import tracker_review  # noqa: E402  (load_rows, classify, is_placeholder, parse_date)


def read_tracker(csv_path=None):
    """[R] Load all tracker rows as dicts."""
    return tracker_review.load_rows(csv_path or config.TRACKER_CSV)


def compute_due(rows, today):
    """[R] The decision kernel: {pending, due} as of `today`."""
    return tracker_review.classify(rows, today)


def is_placeholder(company):
    return tracker_review.is_placeholder(company)


def update_tracker(line, updates, csv_path=None):
    """[M] Update one row (by 1-based CSV line, header=1) and write atomically.

    `updates` is a dict of column -> new value. Returns the updated row.
    Only call after explicit human confirmation for Applied?/Date Applied.
    """
    csv_path = csv_path or config.TRACKER_CSV
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    idx = line - 2  # line 2 == rows[0]
    if idx < 0 or idx >= len(rows):
        raise IndexError(f"line {line} out of range (have {len(rows)} data rows)")
    rows[idx].update(updates)

    tmp = csv_path + ".tmp"
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, csv_path)  # atomic
    return rows[idx]
