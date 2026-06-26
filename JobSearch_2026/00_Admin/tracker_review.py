#!/usr/bin/env python3
"""Daily Application Tracker review — the decision kernel.

Reads Application_Tracker.csv and classifies each open row, relative to a date:
  - PENDING (still inside the 2-day reply window): wait for a recruiter reply.
  - DUE / OVERDUE (window passed, Applied? = No): cold-apply now.
Rule: hard deadline = Date of Outreach + 2 days. Stdlib only.

This module is BOTH a CLI (`python3 tracker_review.py [YYYY-MM-DD]`) and a
library (`from tracker_review import load_rows, classify`). The agent imports
classify() as its deterministic policy — it never reimplements the date math.
"""
import csv, os, sys
from datetime import date, datetime, timedelta

WINDOW_DAYS = 2
HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "Application_Tracker.csv")

# Placeholder company names that can't be perceived/matched against an inbox.
PLACEHOLDERS = {"[company]", "unknown", "tbd", ""}


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def load_rows(csv_path=CSV):
    """Read the tracker CSV into a list of dict rows (header excluded)."""
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))


def is_placeholder(company):
    return (company or "").strip().lower() in PLACEHOLDERS


def classify(rows, today=None):
    """Pure policy: bucket open rows into pending vs due as of `today`.

    Returns {"pending": [...], "due": [...]} where each item is a dict:
        {line, row, deadline, days_overdue}
    - line: 1-based CSV line (header is line 1), so first data row is line 2.
    - deadline: date or None (None means the outreach date was missing/garbled).
    - days_overdue: int for due items (0+), None for pending items.
    Rows with Applied? = Yes are skipped entirely.
    """
    if today is None:
        today = date.today()

    pending, due = [], []
    for i, r in enumerate(rows, start=2):  # +2: header is row 1
        if (r.get("Applied?") or "").strip().lower() == "yes":
            continue
        out = parse_date(r.get("Date of Outreach"))
        if not out:
            due.append({"line": i, "row": r, "deadline": None, "days_overdue": None})
            continue
        deadline = out + timedelta(days=WINDOW_DAYS)
        if today <= deadline:
            pending.append({"line": i, "row": r, "deadline": deadline, "days_overdue": None})
        else:
            due.append({"line": i, "row": r, "deadline": deadline,
                        "days_overdue": (today - deadline).days})
    return {"pending": pending, "due": due}


def main():
    today = date.today() if len(sys.argv) < 2 else parse_date(sys.argv[1])
    verdict = classify(load_rows(), today)
    pending, due = verdict["pending"], verdict["due"]

    print(f"=== Tracker review for {today} (reply window = {WINDOW_DAYS} days) ===\n")

    print(f"PENDING - still waiting on a reply ({len(pending)}):")
    if not pending:
        print("  (none)")
    for it in pending:
        r = it["row"]
        print(f"  row {it['line']}: {r['Company']} - {r['Role']} | outreach {r['Date of Outreach']} ({r['Outreach Mode']}) | decide by {it['deadline']}")

    print(f"\nDUE - window passed, no reply logged -> COLD-APPLY NOW ({len(due)}):")
    if not due:
        print("  (none)")
    for it in due:
        r = it["row"]
        days = it["days_overdue"] if it["days_overdue"] is not None else "?"
        print(f"  row {it['line']}: {r['Company']} - {r['Role']} | outreach {r['Date of Outreach']} ({r['Platform']}) | {days} day(s) overdue")


if __name__ == "__main__":
    main()
