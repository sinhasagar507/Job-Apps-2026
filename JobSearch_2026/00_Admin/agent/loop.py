"""The morning run - one scheduled execution of the agent loop.

Phase 1 scope: perceive the tracker, decide who is overdue/pending, compose the
digest, and hand it off for delivery (dry-run by default). Gmail perception
(reply detection) is added in Phase 2 - the `replies` list is empty for now.

Run:
    python3 -m agent.loop [YYYY-MM-DD]      # from the 00_Admin directory
    AGENT_DRY_RUN=0 python3 -m agent.loop   # arm real delivery handoff

The loop is idempotent: if the digest was already sent for `today`, it exits
without re-acting (unless AGENT_FORCE=1).
"""
import os
import sys
from datetime import date

from . import config, digest, state
from .tools import notify
from .tools import tracker as tracker_tool


def parse_arg_date(argv):
    if len(argv) > 1:
        from datetime import datetime
        return datetime.strptime(argv[1], "%Y-%m-%d").date()
    return date.today()


def run(today=None, force=None):
    today = today or parse_arg_date(sys.argv)
    force = force if force is not None else os.environ.get("AGENT_FORCE") == "1"

    st = state.load()

    # Idempotency guard: don't re-send a digest already sent today.
    if state.digest_already_sent(st, today) and not force:
        notify._log(f"skip: digest already sent for {today} (use AGENT_FORCE=1 to override)")
        print(f"Digest already sent for {today}. Nothing to do. (AGENT_FORCE=1 to re-run.)")
        return

    # PERCEPTION (Phase 1: tracker only)
    rows = tracker_tool.read_tracker()

    # DECISION (deterministic kernel)
    verdict = tracker_tool.compute_due(rows, today)

    # Phase 2 will populate this from a read-only Gmail scan + fuzzy matcher.
    replies = []

    # COMPOSE
    subject, body = digest.compose(verdict, today, replies=replies)

    notify._log(
        f"run {today} level={config.LEVEL} dry_run={config.DRY_RUN} "
        f"due={len(verdict['due'])} pending={len(verdict['pending'])} replies={len(replies)}"
    )

    # ACTION
    result = notify.send_digest(subject, body)

    # Record idempotency only when a real send happened (or force in dry-run for testing).
    if not result["dry_run"]:
        state.mark_digest_sent(st, today)
        state.save(st)

    return result


if __name__ == "__main__":
    run()
