"""Compose the morning digest from a classified verdict.

Three sections (house style: no em dashes, hyphens only):
  A. Replies - engage today        (populated in Phase 2 once Gmail perception lands)
  B. Overdue - cold-apply now      (window passed, Applied? = No)
  C. Pending - decide-by dates     (still inside the 2-day window)

Placeholder rows ([Company]/Unknown/TBD) are surfaced separately because the
agent can't perceive an inbox reply for a job with no real company name.
"""
from .tools import tracker as tracker_tool


def _line(item, with_overdue=False):
    r = item["row"]
    company = (r.get("Company") or "").strip()
    role = (r.get("Role") or "").strip()
    if with_overdue:
        n = item["days_overdue"]
        n = f"{n} day(s) overdue" if n is not None else "no outreach date"
        plat = (r.get("Platform") or "").strip()
        return f"  - {company} - {role} | {plat} | {n}"
    return f"  - {company} - {role} | outreach {r.get('Date of Outreach')} | decide by {item['deadline']}"


def compose(verdict, today, replies=None):
    """Return (subject, body). `replies` is a list of flagged items (Phase 2);
    for Phase 1 it is empty and section A reports none."""
    replies = replies or []
    pending = verdict["pending"]
    due = verdict["due"]

    # Split DUE into real companies (actionable) vs placeholders (need a name).
    real_due = [it for it in due if not tracker_tool.is_placeholder(it["row"].get("Company"))]
    placeholder_due = [it for it in due if tracker_tool.is_placeholder(it["row"].get("Company"))]

    subject = (
        f"Job search - {today}: {len(real_due)} to cold-apply, "
        f"{len(replies)} replies, {len(pending)} pending"
    )

    out = [f"Morning job-search digest for {today}", ""]

    # A. Replies
    out.append(f"A. REPLIES - engage today ({len(replies)})")
    if not replies:
        out.append("  (none detected)")
    else:
        for it in replies:
            r = it["row"]
            snip = it.get("snippet", "")
            out.append(f"  - {r.get('Company')} - {r.get('Role')} | {snip}")
    out.append("")

    # B. Overdue -> cold-apply
    out.append(f"B. OVERDUE - cold-apply now ({len(real_due)})")
    if not real_due:
        out.append("  (none)")
    else:
        for it in real_due:
            out.append(_line(it, with_overdue=True))
    out.append("")

    # C. Pending
    out.append(f"C. PENDING - waiting on a reply ({len(pending)})")
    if not pending:
        out.append("  (none)")
    else:
        for it in pending:
            out.append(_line(it))
    out.append("")

    # Housekeeping: placeholder rows that need a real company name.
    if placeholder_due:
        out.append(f"NEEDS ATTENTION - rows with no real company name ({len(placeholder_due)})")
        for it in placeholder_due:
            r = it["row"]
            out.append(f"  - row {it['line']}: {r.get('Company')} - {r.get('Role')} (fill in or drop)")
        out.append("")

    out.append("Reminder: I never submit applications. Log in and submit the overdue ones yourself.")
    return subject, "\n".join(out)
