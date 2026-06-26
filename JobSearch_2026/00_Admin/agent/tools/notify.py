"""Outbound delivery tools (the [X] / externally-visible actions).

In Phase 1 the actual email send is performed by the cloud-scheduled Claude
agent calling the Gmail integration. This Python layer's job is to:
  - honor DRY_RUN (default ON): log what WOULD be sent instead of sending,
  - emit the digest in a machine-readable block the scheduling agent can pick up,
  - keep an append-only audit trail.

So `send_digest` here never talks to SMTP/Gmail directly. That boundary keeps
secrets out of this script and lets the orchestrator (Claude + MCP) do the send.
"""
import datetime as _dt

from .. import config


def _log(msg):
    """[M] Append a timestamped line to the audit trail."""
    import os
    os.makedirs(os.path.dirname(config.RUNS_LOG), exist_ok=True)
    stamp = _dt.datetime.now().isoformat(timespec="seconds")
    with open(config.RUNS_LOG, "a") as f:
        f.write(f"{stamp} {msg}\n")


def send_digest(subject, body, recipient=None):
    """[X] Deliver the morning digest to the user.

    DRY_RUN ON  -> print + log "would send", emit a SEND_DIGEST block for the
                   orchestrator, and return {'sent': False, 'dry_run': True}.
    DRY_RUN OFF -> same emit, but flagged ready-to-send; the orchestrating Claude
                   agent reads the block and performs the Gmail send.
    """
    recipient = recipient or config.RECIPIENT
    mode = "DRY_RUN" if config.DRY_RUN else "LIVE"
    _log(f"[{mode}] send_digest -> {recipient} | subject: {subject}")

    # Machine-readable handoff block for the scheduling agent (and for eyeballing).
    print("----- SEND_DIGEST -----")
    print(f"MODE: {mode}")
    print(f"TO: {recipient}")
    print(f"SUBJECT: {subject}")
    print("BODY:")
    print(body)
    print("----- END SEND_DIGEST -----")
    return {"sent": False, "dry_run": config.DRY_RUN, "to": recipient, "subject": subject}
