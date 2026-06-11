"""dispatch.py - the live-write dispatcher (the gateway).

Hybrid semantics per the live-track design:
  reads                  -> fixture-backed (same deterministic world as the
                            sandbox track; original & candidate see identical
                            reads), EXCEPT reads of objects created in this
                            run, which are answered from the live system;
  writes (Slack/Jira/    -> REAL API calls through the existing live mappers
   Sheets/Salesforce)       (live/slack.py etc.), after target rebinding into
                            the run's namespace and an allowlist policy check;
  everything else        -> comps primitives, exactly like the sandbox track.

Every real write is logged (write_log) with requested vs physical target and
the raw response - extra-write detection relies on this log, never on
read-back alone. Created/updated objects land in a run-local registry that
drives read-after-write, read-back verification, and the cleanup plan.

Write returns are the REAL responses (issue key, message ts, ...) so a recipe
step that references a previous write's output keeps working.
"""
import copy

from test_sandbox.benchmark_v1 import ops
from test_sandbox.benchmark_v1.sandbox import FixtureDispatch
from test_sandbox.benchmark_v1.live import config as live_config

_JIRA_UPDATE_FIELDS = "summary,description,labels,priority,status,assignee"
_SF_COMPOSITE_CAP = 20      # pre-snapshot/register at most N records per call


def _clone_sheets_client(client, ns):
    """Shallow client clone pinned to the namespace tab - physically isolates
    every sheet write without touching the recipe's inputs."""
    import copy as _copy
    c = _copy.copy(client)
    c.spreadsheet_id = ns["sheets_spreadsheet"]
    c.tab = ns["sheets_tab"]
    return c


class LiveWriteDispatch:
    def __init__(self, fixture, ns, clients, cfg=None, groups=None):
        """groups: provider groups that go LIVE; everything else stays
        fixture-mocked. Gold records its groups and candidates MUST run with
        the same set, or write comparison is meaningless."""
        self.fx = FixtureDispatch(fixture)
        self.recorder = self.fx.recorder          # sandbox-style call trace
        self.ns = ns
        self.cfg = cfg or live_config.load_env()
        self.clients = clients
        self.groups = set(groups) if groups is not None else None
        self.write_log = []
        self.violations = []
        self.live_errors = []
        self.registry = {"jira_issues": [], "jira_updates": [], "jira_comments": [],
                         "slack_messages": [], "sf_records": [], "sf_updates": []}
        self.handlers = {}
        if clients.get("slack") is not None:
            from test_sandbox.live import slack as m
            self.handlers["slack"] = m.make_handler(clients["slack"])
        if clients.get("jira") is not None:
            from test_sandbox.live import jira as m
            self.handlers["jira"] = m.make_handler(clients["jira"])
        if clients.get("sheets") is not None and ns.get("sheets_tab"):
            from test_sandbox.live import google_sheets as m
            self.handlers["google_sheets"] = m.make_handler(
                _clone_sheets_client(clients["sheets"], ns))
        if clients.get("sf") is not None:
            from test_sandbox.live import salesforce as m
            self.handlers["salesforce"] = m.make_handler(clients["sf"])
        if self.groups is not None:
            self.handlers = {g: h for g, h in self.handlers.items()
                             if g in self.groups}

    # ------------------------------------------------------------------ #
    def __call__(self, provider, operation, inp, ctx):
        group = live_config.provider_group(provider)
        if group in self.handlers:
            if ops.is_write(provider, operation):
                return self._write(group, provider, operation, inp, ctx)
            if group == "salesforce":
                # SF reads go LIVE (stage3 precedent): update/composite flows
                # carry record Ids from reads, and fabricated fixture Ids 404
                # against the real org. Original and candidate run this
                # back-to-back against the same org (cleanup reverts between
                # them), so both sides still see the same world.
                try:
                    out = self.handlers[group](provider, operation, inp, ctx)
                    self.recorder.record(provider, operation, inp, out,
                                         False, ops.object_of(inp), "live")
                    return out
                except Exception as e:
                    self.live_errors.append({"provider": provider,
                                             "operation": operation,
                                             "error": repr(e)[:300]})
                    raise
            hit = self._registry_read(group, operation, inp, ctx)
            if hit is not None:
                return hit
        return self.fx(provider, operation, inp, ctx)

    # ------------------------------------------------------------------ #
    # writes                                                             #
    # ------------------------------------------------------------------ #
    def _write(self, group, provider, operation, inp, ctx):
        inp2, requested = self._rebind(group, operation, inp)
        violation = self._policy_check(group, operation, inp2)
        if violation:
            self.violations.append({"provider": provider, "operation": operation,
                                    "requested": requested, "reason": violation})
            out = {"ok": False, "success": False, "error": "policy_violation"}
            self.write_log.append({"provider": provider, "operation": operation,
                                   "group": group, "requested": requested,
                                   "blocked": True, "acked": False})
            return out
        pre = self._pre_state(group, operation, inp2)
        try:
            out = self.handlers[group](provider, operation, inp2, ctx)
        except Exception as e:
            self.live_errors.append({"provider": provider, "operation": operation,
                                     "error": repr(e)[:300]})
            raise
        out = out if isinstance(out, dict) else {}
        self._register(group, operation, inp2, out, pre, requested)
        self.write_log.append({
            "provider": provider, "operation": operation, "group": group,
            "requested": requested, "blocked": False,
            "acked": self._acked(group, out),
            "input": copy.deepcopy(inp),
            "response_keys": sorted(out)[:12],
        })
        return out

    def _rebind(self, group, operation, inp):
        """Force the physical target into the run's namespace; return the
        rebound input + the REQUESTED (recipe-intended) target, which is what
        canonical effects compare."""
        inp2 = copy.deepcopy(inp) if isinstance(inp, dict) else {}
        requested = {}
        if group == "slack":
            requested["channel"] = inp2.get("channel") or inp2.get("channel_id")
            # physical redirect happens in the mapper via SLACK_CHANNEL_OVERRIDE
        elif group == "jira":
            pit = inp2.get("project_issuetype") or inp2.get("sample_project_issuetype")
            requested["project_issuetype"] = pit
            requested["issue"] = inp2.get("issuekey") or inp2.get("key") or inp2.get("id")
            if operation in ("create_issue", "create_customer_request"):
                itype = None
                if isinstance(pit, str) and ":" in pit:
                    itype = pit.split(":", 1)[1].strip()
                inp2["project_issuetype"] = "%s : %s" % (
                    self.ns["jira_project"], itype or "Task")
                labels = inp2.get("labels")
                labels = labels if isinstance(labels, list) else (
                    [labels] if isinstance(labels, str) and labels.strip() else [])
                inp2["labels"] = labels + [self.ns["marker"]]
        elif group == "google_sheets":
            requested["spreadsheet"] = inp2.get("spreadsheet_id") or inp2.get("spreadsheet")
            requested["sheet"] = inp2.get("sheet_name") or inp2.get("sheet")
            # physical pinning happens via the cloned client (namespace tab)
        elif group == "salesforce":
            requested["sobject"] = inp2.get("sobject_name")
        return inp2, requested

    def _policy_check(self, group, operation, inp2):
        if group == "slack" and not self.ns.get("slack_channel"):
            return "no bench slack channel configured (SLACK_CHANNEL_OVERRIDE)"
        if group == "google_sheets" and not self.ns.get("sheets_tab"):
            return "no namespace sheet tab materialized"
        if group == "jira" and operation in ("create_issue", "create_customer_request"):
            # creates are rebound to the bench project above; anything else
            # slipping through is a gateway bug, so block it.
            pit = inp2.get("project_issuetype") or ""
            if isinstance(pit, str) and pit.split(":")[0].strip() not in (
                    self.ns["jira_project"], ""):
                return "jira create outside bench project"
        return None

    def _pre_state(self, group, operation, inp2):
        """Snapshot the object an UPDATE will touch (changed-field diff +
        cleanup revert). Best-effort: unusable keys -> None."""
        try:
            if group == "jira" and operation in ("update_issue",
                                                 "update_issue_status",
                                                 "assign_issue"):
                key = inp2.get("issuekey") or inp2.get("key") \
                    or inp2.get("issue_key") or inp2.get("id")
                if isinstance(key, str) and "-" in key:
                    return self.clients["jira"].get_issue(key, _JIRA_UPDATE_FIELDS)
            if group == "salesforce" and operation in (
                    "update_sobject", "updated_custom_object"):
                rid, sob = inp2.get("id"), inp2.get("sobject_name")
                if rid and sob:
                    return self.clients["sf"].get(sob, rid)
            if group == "salesforce" and operation == "composite_update_sobject":
                sob = inp2.get("sobject_name")
                recs = inp2.get("records")
                recs = [recs] if isinstance(recs, dict) else (recs or [])
                pre = {}
                for rec in recs[:_SF_COMPOSITE_CAP]:
                    rid = rec.get("Id") or rec.get("id") if isinstance(rec, dict) else None
                    if rid and sob:
                        pre[rid] = self.clients["sf"].get(sob, rid)
                return pre or None
            if group == "salesforce" and operation == "upsert_sobject":
                # does the upsert key match an existing record? (decides
                # whether cleanup deletes a create or reverts an update)
                sob = inp2.get("sobject_name")
                qf = inp2.get("query_field") or "Id"
                if isinstance(qf, dict):
                    qf = qf.get("primary_key") or qf.get("field") or "Id"
                key_val = inp2.get(qf) or inp2.get("Id") or inp2.get("id")
                if sob and key_val:
                    if qf in ("Id", "id"):
                        return {"existing": self.clients["sf"].get(sob, key_val)}
                    rows = self.clients["sf"].query_all(
                        "SELECT Id FROM %s WHERE %s = '%s' LIMIT 1"
                        % (sob, qf, str(key_val).replace("'", "\\'")))
                    if rows:
                        return {"existing": self.clients["sf"].get(sob, rows[0]["Id"])}
                return {"existing": None}
        except Exception:
            return None
        return None

    def _acked(self, group, out):
        if group == "slack":
            return out.get("ok") is True
        if group == "google_sheets":
            return (out.get("appended") or 0) > 0
        if group == "jira":
            return bool(out.get("key")) and out.get("success") is not False
        if group == "salesforce":
            if "count" in out:                     # composite: acked = wrote rows
                return (out.get("count") or 0) > 0
            res = out.get("result") if isinstance(out.get("result"), dict) else {}
            return bool(out.get("id") or out.get("success") or res.get("id")
                        or res.get("success"))
        return False

    def _register(self, group, operation, inp2, out, pre, requested):
        plan = self.ns["cleanup_plan"]
        if group == "jira":
            if operation == "create_comment" and out.get("id"):
                # the mapper returns the comment object; the issue key is the
                # (rebound/patched) input key, falling back to the bench target
                key = inp2.get("key") or inp2.get("issuekey") or inp2.get("id") \
                    or inp2.get("Issue") or inp2.get("issue_key") \
                    or self.ns.get("jsm_target_key") or self.ns.get("jira_target_key")
                if isinstance(key, str) and "-" in key:
                    self.registry.setdefault("jira_comments", []).append(
                        {"key": key, "comment_id": out["id"],
                         "requested": requested})
                    plan.append({"provider": "jira", "op": "delete_comment",
                                 "key": key, "comment_id": out["id"]})
                return
            if not out.get("key"):
                return
            if operation in ("create_issue", "create_customer_request"):
                self.registry["jira_issues"].append(
                    {"key": out["key"], "requested": requested})
                plan.append({"provider": "jira", "op": "delete_issue",
                             "key": out["key"]})
            elif operation in ("update_issue", "update_issue_status",
                               "assign_issue"):
                self.registry["jira_updates"].append(
                    {"key": out["key"], "pre": pre, "operation": operation,
                     "payload_fields": sorted(inp2), "requested": requested})
                if pre is None:
                    # key wasn't usable -> the mapper seeded a NEW issue to act
                    # on; it is ours to delete (pollution guard)
                    plan.append({"provider": "jira", "op": "delete_issue",
                                 "key": out["key"]})
        elif group == "slack" and out.get("ok") and out.get("ts"):
            ch = out.get("channel") or self.ns.get("slack_channel")
            self.registry["slack_messages"].append(
                {"channel": ch, "ts": out["ts"], "requested": requested,
                 "thread_ts": out.get("message", {}).get("thread_ts")
                 if isinstance(out.get("message"), dict) else None})
            plan.append({"provider": "slack", "op": "delete_message",
                         "channel": ch, "ts": out["ts"]})
        elif group == "salesforce":
            self._register_sf(operation, inp2, out, pre, requested, plan)

    def _sf_track_update(self, sob, rid, payload, pre_rec, requested, plan):
        pre_fields = {k: (pre_rec or {}).get(k) for k in payload
                      if pre_rec and k in pre_rec}
        self.registry["sf_updates"].append(
            {"sobject": sob, "id": rid, "pre": pre_fields,
             "payload_fields": sorted(payload), "requested": requested})
        if pre_fields:
            plan.append({"provider": "salesforce", "op": "revert_update",
                         "sobject": sob, "id": rid, "pre_fields": pre_fields})

    def _register_sf(self, operation, inp2, out, pre, requested, plan):
        sob = inp2.get("sobject_name")
        res = out.get("result") if isinstance(out.get("result"), dict) else {}
        rid = out.get("id") or res.get("id")
        if not sob:
            return
        if operation == "composite_create_sobject":
            recs = inp2.get("records")
            recs = [recs] if isinstance(recs, dict) else (recs or [])
            srcs = [r for r in recs if isinstance(r, dict)
                    and any(k not in ("Id", "id", "attributes") for k in r)]
            for src, r in list(zip(srcs, out.get("records") or []))[:_SF_COMPOSITE_CAP]:
                crid = (r or {}).get("id")
                if crid:
                    self.registry["sf_records"].append(
                        {"sobject": sob, "id": crid, "requested": requested,
                         "fields_written": [k for k in src
                                            if k not in ("Id", "id", "attributes")]})
                    plan.append({"provider": "salesforce", "op": "delete_record",
                                 "sobject": sob, "id": crid})
        elif operation == "composite_update_sobject":
            recs = inp2.get("records")
            recs = [recs] if isinstance(recs, dict) else (recs or [])
            by_id = {(r.get("Id") or r.get("id")): r for r in recs
                     if isinstance(r, dict)}
            for r in (out.get("records") or [])[:_SF_COMPOSITE_CAP]:
                urid = (r or {}).get("id")
                if not urid:
                    continue
                src = by_id.get(urid) or {}
                payload = [k for k in src if k not in ("Id", "id", "attributes")]
                self._sf_track_update(sob, urid, payload,
                                      (pre or {}).get(urid), requested, plan)
        elif operation == "upsert_sobject" and rid:
            existing = (pre or {}).get("existing")
            payload = [k for k in inp2 if k not in ("sobject_name", "id", "Id",
                                                    "query_field", "all_or_none")
                       and not isinstance(inp2[k], (dict, list))]
            if existing:
                self._sf_track_update(sob, rid, payload, existing, requested, plan)
            else:
                self.registry["sf_records"].append(
                    {"sobject": sob, "id": rid, "requested": requested,
                     "fields_written": payload})
                plan.append({"provider": "salesforce", "op": "delete_record",
                             "sobject": sob, "id": rid})
        elif rid and operation in ("create_sobject", "create_custom_object"):
            self.registry["sf_records"].append(
                {"sobject": sob, "id": rid, "requested": requested,
                 "fields_written": [k for k in inp2
                                    if k not in ("sobject_name", "id", "Id")
                                    and not isinstance(inp2[k], (dict, list))]})
            plan.append({"provider": "salesforce", "op": "delete_record",
                         "sobject": sob, "id": rid})
        elif rid and isinstance(pre, dict) and "existing" not in pre:
            payload = [k for k in inp2 if k not in ("sobject_name", "id")
                       and not isinstance(inp2[k], (dict, list))]
            self._sf_track_update(sob, rid, payload, pre, requested, plan)

    # ------------------------------------------------------------------ #
    # read-after-write                                                   #
    # ------------------------------------------------------------------ #
    def _registry_read(self, group, operation, inp, ctx):
        """Reads of objects created in THIS run are answered live."""
        try:
            if group == "jira" and operation == "get_issue":
                key = (inp or {}).get("id") or (inp or {}).get("issuekey") \
                    or (inp or {}).get("key")
                if any(r["key"] == key for r in self.registry["jira_issues"]):
                    return self.clients["jira"].get_issue(key)
            if group == "salesforce" and operation in ("get_sobject", "get_custom_object"):
                rid = (inp or {}).get("id")
                for r in self.registry["sf_records"]:
                    if r["id"] == rid:
                        return self.clients["sf"].get(r["sobject"], rid) or {}
        except Exception:
            return None
        return None
