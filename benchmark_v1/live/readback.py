"""readback.py - real-API read-back verification (the final truth).

A write call's response is only an ack; the verdict comes from reading the
real external state back and canonicalizing it:

  google_sheets  values.get on the namespace tab -> the tab's final value
                 matrix (one `sheets.final_values` effect; the tab started
                 empty, so the matrix IS the state diff)
  jira           every registry-created key -> issue read-back (summary,
                 type, labels, priority, description); every registered
                 update -> pre/post changed-field diff
  slack          every registry message (channel, ts) -> conversations.history
                 read-back of that exact message (text, buttons) - history,
                 not search, so no indexing delay
  salesforce     every registry-created id -> record read-back limited to the
                 fields the recipe wrote; updates -> pre/post changed fields

Transient read failures retry (cfg readback_retries/wait) and are recorded as
flake_retries; a final failure is a live_readback_error.
"""
import time

from test_sandbox.benchmark_v1.live import canonical_live as cl


def _retry(cfg, fn, flakes, label):
    last = None
    for attempt in range(max(1, int(cfg.get("readback_retries", 3)))):
        try:
            return fn()
        except Exception as e:
            last = e
            flakes.append({"what": label, "attempt": attempt, "error": repr(e)[:200]})
            time.sleep(float(cfg.get("readback_wait_sec", 2.0)))
    raise last


def read_back(ns, dispatch, clients, cfg):
    """-> (canonical_effects, raw_snapshots, flake_retries). Raises only after
    retries are exhausted (caller records live_readback_error)."""
    effects, raw, flakes = [], {}, []
    rmap_ns = ns
    reg = dispatch.registry

    # ---- google sheets: final tab state --------------------------------- #
    if ns.get("sheets_tab") and clients.get("sheets") is not None:
        values = _retry(cfg, lambda: clients["sheets"].get_values(
            spreadsheet_id=ns["sheets_spreadsheet"], tab=ns["sheets_tab"]),
            flakes, "sheets.values")
        raw["sheets_values"] = values
        if values:
            effects.append({
                "provider": "google_sheets",
                "family": "sheets.final_values",
                "spreadsheet": "logical.sheets.spreadsheet",
                "sheet": "logical.sheets.main",
                "values": [[cl.scrub_value(c, rmap_ns) for c in row]
                           for row in values],
                "n_rows": len(values),
            })

    # ---- jira: created issues + updates ---------------------------------- #
    if clients.get("jira") is not None:
        raw["jira_issues"] = []
        for r in reg["jira_issues"]:
            issue = _retry(cfg, lambda k=r["key"]: clients["jira"].get_issue(k),
                           flakes, "jira.get_issue")
            raw["jira_issues"].append(issue)
            f = (issue or {}).get("fields") or {}
            labels = [l for l in (f.get("labels") or []) if l != ns["marker"]]
            effects.append({
                "provider": "jira",
                "family": "jira.create_issue",
                "project": "logical.jira.project",
                "requested_project": cl.norm_text(
                    (r.get("requested") or {}).get("project_issuetype"), ns) or None,
                "issue_type": ((f.get("issuetype") or {}).get("name")),
                "summary": cl.norm_text(f.get("summary"), ns) or None,
                "description": cl.norm_text(cl.adf_to_text(f.get("description")), ns) or None,
                "labels": sorted(cl.norm_text(l, ns) for l in labels),
                "priority": ((f.get("priority") or {}).get("name")),
            })
        raw["jira_comments"] = []
        for r in reg.get("jira_comments", []):
            def fetch_comment(rr=r):
                res = clients["jira"].get_comments(rr["key"])
                for c in (res or {}).get("comments", []):
                    if str(c.get("id")) == str(rr["comment_id"]):
                        return c
                raise RuntimeError("comment %s not found on %s"
                                   % (rr["comment_id"], rr["key"]))
            c = _retry(cfg, fetch_comment, flakes, "jira.get_comment")
            raw["jira_comments"].append(c)
            effects.append({
                "provider": "jira",
                "family": "jira.comment",
                "issue": "<JIRA_ISSUE_KEY>",
                "body": cl.norm_text(cl.adf_to_text(c.get("body")), ns) or None,
            })
        for r in reg["jira_updates"]:
            post = _retry(cfg, lambda k=r["key"]: clients["jira"].get_issue(k),
                          flakes, "jira.get_issue_post")
            pre_f = ((r.get("pre") or {}).get("fields") or {})
            post_f = (post or {}).get("fields") or {}
            changed = {}
            for k in ("summary", "priority", "labels", "description", "status"):
                a = pre_f.get(k)
                b = post_f.get(k)
                if k in ("priority", "status"):
                    a = (a or {}).get("name") if isinstance(a, dict) else a
                    b = (b or {}).get("name") if isinstance(b, dict) else b
                if k == "description":
                    a, b = cl.adf_to_text(a), cl.adf_to_text(b)
                if a != b:
                    changed[k] = cl.norm_text(b, ns) if isinstance(b, str) else b
            effects.append({
                "provider": "jira",
                "family": "jira.update_issue",
                "issue": "<JIRA_ISSUE_KEY>",
                "changed_fields": changed,
            })

    # ---- slack: registered messages -------------------------------------- #
    if clients.get("slack") is not None:
        raw["slack_messages"] = []
        for r in reg["slack_messages"]:
            def fetch(rr=r):
                res = clients["slack"].call(
                    "conversations.history",
                    {"channel": rr["channel"], "latest": rr["ts"],
                     "oldest": rr["ts"], "inclusive": True, "limit": 1},
                    http_get=True)
                if not res.get("ok") or not res.get("messages"):
                    raise RuntimeError("message not found: %s" % res.get("error"))
                return res["messages"][0]
            msg = _retry(cfg, fetch, flakes, "slack.history")
            raw["slack_messages"].append(msg)
            buttons = []
            for b in (msg.get("blocks") or []):
                for el in (b.get("elements") or []):
                    if isinstance(el, dict) and el.get("type") == "button":
                        t = el.get("text")
                        buttons.append(cl.norm_text(
                            t.get("text") if isinstance(t, dict) else t, ns))
            effects.append({
                "provider": "slack",
                "family": "slack.post_message",
                "channel": cl.norm_text(
                    (r.get("requested") or {}).get("channel"), ns) or
                "logical.slack.bench_channel",
                "thread": "<THREAD>" if r.get("thread_ts") else None,
                "text": cl.norm_text(msg.get("text"), ns),
                "buttons": buttons,
            })

    # ---- salesforce: created records + updates --------------------------- #
    if clients.get("sf") is not None:
        raw["sf_records"] = []
        for r in reg["sf_records"]:
            rec = _retry(cfg, lambda rr=r: clients["sf"].get(rr["sobject"], rr["id"]),
                         flakes, "sf.get")
            raw["sf_records"].append(rec)
            written = (r.get("fields_written")
                       or dispatch_payload_fields(dispatch, r)
                       or [k for k in (rec or {}) if not k.startswith("attributes")])
            effects.append({
                "provider": "salesforce",
                "family": "salesforce.create_record",
                "sobject": r["sobject"],
                "fields": {k: cl.scrub_value((rec or {}).get(k), ns)
                           for k in sorted(written)
                           if k in (rec or {}) and k not in ("Id", "attributes")},
            })
        for r in reg["sf_updates"]:
            post = _retry(cfg, lambda rr=r: clients["sf"].get(rr["sobject"], rr["id"]),
                          flakes, "sf.get_post")
            changed = {}
            for k in r.get("payload_fields") or []:
                a = (r.get("pre") or {}).get(k)
                b = (post or {}).get(k)
                if a != b:
                    changed[k] = cl.scrub_value(b, ns)
            effects.append({
                "provider": "salesforce",
                "family": "salesforce.update_record",
                "sobject": r["sobject"],
                "record": "<SF_ID>",
                "changed_fields": changed,
            })

    return effects, raw, flakes


def dispatch_payload_fields(dispatch, reg_entry):
    """Field names the recipe sent for this created record (from the write log)."""
    for w in dispatch.write_log:
        if w.get("group") == "salesforce" and not w.get("blocked"):
            inp = w.get("input") or {}
            if inp.get("sobject_name") == reg_entry["sobject"]:
                return [k for k in inp
                        if k not in ("sobject_name", "id", "all_or_none")
                        and not isinstance(inp[k], (dict, list))]
    return None
