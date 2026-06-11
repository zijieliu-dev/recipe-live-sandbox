"""config.py - live-track environment: clients, bench targets, allowlists.

Secrets stay in test_sandbox/.env (the existing live clients read it).
Track-level settings live in live_env.json next to this file (committed,
no secrets):

  {
    "jira_project": "ST",            // bench project every Jira write lands in
    "sf_org": "my-dev-org",
    "providers_enabled": ["google_sheets", "jira", "slack", "salesforce"],
    "readback_retries": 3,
    "readback_wait_sec": 2.0
  }

Slack bench channel comes from SLACK_CHANNEL_OVERRIDE in .env (the mapper
already redirects every post there); the Sheets spreadsheet comes from
SHEETS_SPREADSHEET_ID.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_JSON = os.path.join(HERE, "live_env.json")

DEFAULTS = {
    "jira_project": "ST",
    "sf_org": "my-dev-org",
    "providers_enabled": ["google_sheets", "jira", "slack", "salesforce"],
    "readback_retries": 3,
    "readback_wait_sec": 2.0,
}

LIVE_PROVIDERS = {"salesforce", "jira", "jira_service_desk", "slack",
                  "slack_bot", "google_sheets"}
_PROVIDER_GROUP = {"slack": "slack", "slack_bot": "slack",
                   "jira": "jira", "jira_service_desk": "jira",
                   "google_sheets": "google_sheets",
                   "salesforce": "salesforce"}


def provider_group(provider):
    return _PROVIDER_GROUP.get(provider)


def load_env():
    cfg = dict(DEFAULTS)
    if os.path.exists(ENV_JSON):
        with open(ENV_JSON) as f:
            cfg.update(json.load(f))
    return cfg


def build_clients(cfg=None, only=None):
    """Authenticate the live clients once (same pattern as live/runner.py).
    `only` limits which provider groups are built (e.g. {"google_sheets"} for
    the Sheets pilot). Missing creds -> that provider stays None (disabled)."""
    cfg = cfg or load_env()
    want = set(only or cfg["providers_enabled"])
    clients = {"slack": None, "jira": None, "sheets": None, "sf": None}
    if "slack" in want:
        from test_sandbox.slack_live import SlackClient
        clients["slack"] = SlackClient.from_env()
    if "jira" in want:
        from test_sandbox.jira_live import JiraClient
        clients["jira"] = JiraClient.from_env()
    if "google_sheets" in want:
        from test_sandbox.google_sheets_live import SheetsClient
        clients["sheets"] = SheetsClient.from_env()
    if "salesforce" in want:
        from test_sandbox.salesforce_live import SalesforceClient
        clients["sf"] = SalesforceClient.from_cli(cfg["sf_org"])
    return clients


def bench_targets(cfg, clients):
    """The physical bench resources every write must land in (the allowlist
    backbone). Read from the clients' env so there is one source of truth."""
    slack_channel = None
    if clients.get("slack") is not None:
        slack_channel = getattr(clients["slack"], "channel_override", None) \
            or os.environ.get("SLACK_CHANNEL_OVERRIDE")
    spreadsheet = None
    if clients.get("sheets") is not None:
        spreadsheet = clients["sheets"].spreadsheet_id
    return {
        "slack_channel": slack_channel,
        "jira_project": cfg["jira_project"],
        "sheets_spreadsheet": spreadsheet,
    }
