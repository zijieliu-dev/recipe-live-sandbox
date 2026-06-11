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


def _sf_minimal_payload(sobject, marker_str):
    """The minimal create payload per sobject type (required fields differ)."""
    name = "BENCH target %s" % marker_str
    per_type = {
        "Account": {"Name": name},
        "Contact": {"LastName": name},
        "Lead": {"LastName": name, "Company": "BENCH"},
        "Opportunity": {"Name": name, "StageName": "Prospecting",
                        "CloseDate": "2030-12-31"},
        "Case": {"Subject": name},
        "Task": {"Subject": name},
        "Event": {"Subject": name, "DurationInMinutes": 30,
                  "ActivityDateTime": "2030-12-31T00:00:00Z"},
        "Campaign": {"Name": name},
    }
    return per_type.get(sobject, {"Name": name})


def marker(recipe_id, scenario_id, side):
    """Unique, label-safe run marker (no spaces/colons - Jira label rules)."""
    scen = re.sub(r"\W+", "", scenario_id)[:12]
    return "B%s_%s_%s" % (recipe_id, scen, side[0])


def tab_name(recipe_id, scenario_id, side):
    return marker(recipe_id, scenario_id, side).lower()


def materialize(recipe_id, scenario_id, side, cfg, clients, targets, needs=None):
    """Create the per-run live resources. `needs` (from
    rebind.update_target_templates) requests bench UPDATE TARGETS:
      jira_target  -> a real issue in the bench project the recipe can
                      update/comment on (fixture gets patched to its key)
      jsm_target   -> the org's seeded JSM request key (shared; per-run
                      isolation via comment ids)
      sf_targets   -> one minimal record per sobject the recipe updates
    Returns the namespace dict."""
    needs = needs or {}
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

    ns["materialize_errors"] = []
    jira = clients.get("jira")
    if needs.get("jira_target") and jira is not None:
        try:
            res = jira.create_issue({
                "project": {"key": ns["jira_project"]},
                "issuetype": {"name": "Task"},
                "summary": "BENCH update target %s" % ns["marker"],
                "labels": [ns["marker"]],
            })
            ns["jira_target_key"] = res.get("key")
            ns["cleanup_plan"].append({"provider": "jira", "op": "delete_issue",
                                       "key": res.get("key")})
        except Exception as e:
            ns["materialize_errors"].append("jira_target: %s" % repr(e)[:150])
    if needs.get("jsm_target") and jira is not None:
        try:
            from test_sandbox.live.realize import jsm_seed_request
            ns["jsm_target_key"] = (jsm_seed_request(jira) or {}).get("issueKey")
        except Exception as e:
            ns["materialize_errors"].append("jsm_target: %s" % repr(e)[:150])
    sf = clients.get("sf")
    if needs.get("sf_targets") and sf is not None:
        ns["sf_target_ids"] = {}
        for sob in needs["sf_targets"]:
            try:
                res = sf.create(sob, _sf_minimal_payload(sob, ns["marker"]))
                rid = (res or {}).get("id")
                if rid:
                    ns["sf_target_ids"][sob] = rid
                    ns["cleanup_plan"].append({"provider": "salesforce",
                                               "op": "delete_record",
                                               "sobject": sob, "id": rid})
            except Exception as e:
                ns["materialize_errors"].append("sf_target %s: %s" % (sob, repr(e)[:120]))
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
            elif prov == "jira" and op == "delete_comment":
                clients["jira"]._req("DELETE", "/rest/api/3/issue/%s/comment/%s"
                                     % (step["key"], step["comment_id"]))
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
            # "already absent" IS the desired state for deletes, and a revert
            # of a record that was deleted afterwards (our own target) is moot
            if ("404" in detail or "does not exist" in detail
                    or "NOT_FOUND" in detail or "ENTITY_IS_DELETED" in detail):
                ok, detail = True, "already gone"
        results.append({**step, "ok": ok, "detail": detail})
    ns["cleanup_results"] = results
    return results
