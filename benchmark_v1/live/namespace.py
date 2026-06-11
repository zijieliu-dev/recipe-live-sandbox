"""namespace.py - per-(task, scenario, side) isolated live namespaces.

original and candidate NEVER share writable objects:

  google_sheets  a fresh TAB per run in the bench spreadsheet
                 (b<rid>_<scen>_<side>); read-back = that tab; cleanup =
                 deleteSheet. Fully isolated.
  jira           one bench project for everything; per-run isolation via a
                 marker LABEL on every created issue + the created-key
                 registry. Cleanup = delete registered issues.
  slack          one bench channel (SLACK_CHANNEL_OVERRIDE); per-run isolation
                 via a marker token appended to message text + the run-start
                 ts window. Cleanup = delete registered messages (chat.delete).
  salesforce     shared dev org; isolation purely via the created-id registry
                 (payloads are never mutated). Cleanup = delete created ids,
                 revert registered field updates.

materialize() returns the namespace dict (with resource_map + cleanup hooks);
it is saved under live/materialized/<rid>/<scenario>/<side>.json.
"""
import json
import os
import re

from test_sandbox.benchmark_v1 import common

MATERIALIZED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "materialized")


def marker(recipe_id, scenario_id, side):
    """Unique, label-safe run marker (no spaces/colons - Jira label rules)."""
    scen = re.sub(r"\W+", "", scenario_id)[:12]
    return "B%s_%s_%s" % (recipe_id, scen, side[0])


def tab_name(recipe_id, scenario_id, side):
    return marker(recipe_id, scenario_id, side).lower()


def materialize(recipe_id, scenario_id, side, cfg, clients, targets):
    """Create the per-run live resources. Returns the namespace dict."""
    ns = {
        "recipe_id": recipe_id,
        "scenario_id": scenario_id,
        "side": side,                                  # "original" | "candidate"
        "marker": marker(recipe_id, scenario_id, side),
        "slack_channel": targets.get("slack_channel"),
        "jira_project": targets.get("jira_project"),
        "sheets_spreadsheet": targets.get("sheets_spreadsheet"),
        "sheets_tab": None,
        "sheets_sheet_id": None,
        "cleanup_plan": [],                            # filled here + at run time
        "cleanup_results": [],
    }
    sheets = clients.get("sheets")
    if sheets is not None and ns["sheets_spreadsheet"]:
        title = tab_name(recipe_id, scenario_id, side)
        res = sheets._req("POST", "/spreadsheets/%s:batchUpdate" % ns["sheets_spreadsheet"],
                          body={"requests": [{"addSheet": {"properties": {"title": title}}}]})
        props = res["replies"][0]["addSheet"]["properties"]
        ns["sheets_tab"] = props["title"]
        ns["sheets_sheet_id"] = props["sheetId"]
        ns["cleanup_plan"].append({"provider": "google_sheets", "op": "delete_tab",
                                   "spreadsheet": ns["sheets_spreadsheet"],
                                   "sheet_id": props["sheetId"], "tab": title})
    return ns


def resource_map(ns):
    """Physical -> logical mapping used by the live canonicalizer. Both sides
    of a task produce the same logical names, so their diffs can compare."""
    m = {}
    if ns.get("sheets_tab"):
        m[ns["sheets_tab"]] = "logical.sheets.main"
    if ns.get("sheets_spreadsheet"):
        m[ns["sheets_spreadsheet"]] = "logical.sheets.spreadsheet"
    if ns.get("slack_channel"):
        m[ns["slack_channel"]] = "logical.slack.bench_channel"
    if ns.get("jira_project"):
        m[ns["jira_project"]] = "logical.jira.project"
    return m


def save(ns, extra=None):
    d = os.path.join(MATERIALIZED_DIR, str(ns["recipe_id"]), ns["scenario_id"])
    os.makedirs(d, exist_ok=True)
    doc = dict(ns)
    doc["resource_map"] = resource_map(ns)
    if extra:
        doc.update(extra)
    path = os.path.join(d, "%s.json" % ns["side"])
    with open(path, "w") as f:
        json.dump(doc, f, indent=1, default=str)
    return path


def cleanup(ns, clients):
    """Execute the cleanup plan. Every step's outcome is recorded - a failed
    cleanup is a metric (cleanup_error), never silently ignored."""
    results = []
    for step in ns.get("cleanup_plan", []):
        ok, detail = False, ""
        try:
            prov, op = step["provider"], step["op"]
            if prov == "google_sheets" and op == "delete_tab":
                clients["sheets"]._req(
                    "POST", "/spreadsheets/%s:batchUpdate" % step["spreadsheet"],
                    body={"requests": [{"deleteSheet": {"sheetId": step["sheet_id"]}}]})
                ok = True
            elif prov == "jira" and op == "delete_issue":
                clients["jira"]._req("DELETE", "/rest/api/3/issue/%s" % step["key"])
                ok = True
            elif prov == "slack" and op == "delete_message":
                res = clients["slack"].call("chat.delete",
                                            {"channel": step["channel"], "ts": step["ts"]})
                ok = bool(res.get("ok"))
                detail = res.get("error") or ""
            elif prov == "salesforce" and op == "delete_record":
                clients["sf"].delete(step["sobject"], step["id"])
                ok = True
            elif prov == "salesforce" and op == "revert_update":
                clients["sf"].update(step["sobject"], step["id"], step["pre_fields"])
                ok = True
            else:
                detail = "unknown cleanup op"
        except Exception as e:
            detail = repr(e)[:200]
        results.append({**step, "ok": ok, "detail": detail})
    ns["cleanup_results"] = results
    return results
