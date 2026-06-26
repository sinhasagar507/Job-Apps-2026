"""Agent memory: the agent_state.json sidecar.

This holds what the ROBOT remembers, kept separate from the CSV (the world
state the human owns). It gives the agent two things:
  - idempotency  : digest_sent[date] + reply_msg_ids so a re-run never double-acts
  - memory       : per-row reply flags and a growing company->domain alias map

Stdlib only (json). Safe to delete: the agent rebuilds it on the next run.
"""
import json
import os

from . import config

_EMPTY = {
    "rows": {},                  # stable_key -> {last_scanned, reply_detected, ...}
    "digest_sent": {},           # "YYYY-MM-DD" -> true
    "company_domain_aliases": {  # seed; grows as matches are confirmed (Phase 2)
        "Starbucks": "starbucks.com",
        "Twitch": "twitch.tv",
        "Amazon": "amazon.com",
        "Point72": "point72.com",
    },
}


def stable_key(row):
    """Identity for a tracker row. Rows have no id, so key on the fields that
    together identify an outreach attempt. Placeholder rows still get a key but
    are skipped from inbox perception elsewhere."""
    return "|".join([
        (row.get("Company") or "").strip(),
        (row.get("Role") or "").strip(),
        (row.get("Date of Outreach") or "").strip(),
    ])


def load(path=None):
    path = path or config.STATE_JSON
    if not os.path.exists(path):
        return json.loads(json.dumps(_EMPTY))  # deep copy of the default
    with open(path) as f:
        data = json.load(f)
    # Backfill any missing top-level keys so older sidecars stay valid.
    for k, v in _EMPTY.items():
        data.setdefault(k, json.loads(json.dumps(v)))
    return data


def save(state, path=None):
    path = path or config.STATE_JSON
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)  # atomic


def digest_already_sent(state, day):
    return bool(state.get("digest_sent", {}).get(str(day)))


def mark_digest_sent(state, day):
    state.setdefault("digest_sent", {})[str(day)] = True
