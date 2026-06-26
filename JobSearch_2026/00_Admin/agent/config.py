"""Agent configuration — paths, autonomy level, and guardrail switches.

Everything the agent's behavior depends on lives here so it's one place to audit.
Values can be overridden by environment variables (handy for the cloud schedule).
"""
import os

# --- Paths -----------------------------------------------------------------
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))      # .../00_Admin/agent
ADMIN_DIR = os.path.dirname(AGENT_DIR)                       # .../00_Admin
PROJECT_ROOT = os.path.abspath(os.path.join(ADMIN_DIR, "..", ".."))  # Job Applications
TRACKER_CSV = os.path.join(ADMIN_DIR, "Application_Tracker.csv")
STATE_JSON = os.path.join(AGENT_DIR, "agent_state.json")
RUNS_LOG = os.path.join(AGENT_DIR, "runs.log")
FOLLOWUPS_DIR = os.path.abspath(os.path.join(ADMIN_DIR, "..", "05_FollowUps"))

# --- Who gets the digest ---------------------------------------------------
RECIPIENT = os.environ.get("AGENT_RECIPIENT", "namantaneja1993@gmail.com")

# --- Decision policy -------------------------------------------------------
# Reply window in days (deadline = Date of Outreach + WINDOW_DAYS). Mirrors the
# kernel; kept here so config is the single source for tunables.
WINDOW_DAYS = int(os.environ.get("AGENT_WINDOW_DAYS", "2"))

# --- Autonomy & guardrails -------------------------------------------------
# L0 = propose only | L1 = act toward the user (default) | L2 = auto-send outreach
LEVEL = os.environ.get("AGENT_LEVEL", "L1")

# DRY_RUN ON means externally-visible actions (send_digest, calendar, outreach)
# only LOG what they would do. Default ON; flip to "0" to actually send.
DRY_RUN = os.environ.get("AGENT_DRY_RUN", "1") != "0"
