"""
live/jira.py - a real-API Jira comp handler.

Maps Workato Jira operations (provider "jira" and "jira_service_desk") to live
REST calls via JiraClient, returning data shaped like the mocked connector so
downstream datapills resolve unchanged.

Custom-field writes use the same drop-bad-field retry as the Salesforce handler:
Jira rejects unknown/unconfigured fields with a 400 naming them, so we drop the
offenders and retry (best-effort create against whatever the org actually has).

Unmapped/trigger ops return {} so the run never crashes.
"""
from test_sandbox.jira_live import JiraError

# Jira's GA /search/jql endpoint rejects unbounded queries; this bounded form
# is the safe fallback when a recipe's JQL pill resolved empty or malformed.
_SAFE_JQL = 'created >= "2000-01-01" ORDER BY created DESC'

# top-level input keys that are NOT issue fields
RESERVED = {"key", "issuekey", "issue_key", "id", "fields", "jql", "pagination",
            "query", "accountId", "transition_name", "project_issuetype",
            "sample_project_issuetype", "Issue", "body", "public",
            "serviceDeskId", "requestTypeId", "requestFieldValues",
            "raiseOnBehalfOf"}


def _split_project_issuetype(v):
    """Workato's 'PROJ--IssueType' combined picker -> (project_key, issuetype)."""
    if isinstance(v, str) and "--" in v:
        proj, _, itype = v.partition("--")
        return proj.strip(), itype.strip()
    return None, None


def _labels(v):
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str) and v.strip():
        return [t.strip() for t in v.replace(",", "\n").split("\n") if t.strip()]
    return None


def _skipped(v):
    """A field whose formula resolved to `skip`/MISSING -> omit it."""
    from test_sandbox.engine.formula import SKIP
    from test_sandbox.engine.refs import MISSING
    return v is SKIP or v is MISSING


def _issue_fields(inp, for_update=False):
    """Build the Jira `fields` object from a Workato create/update input."""
    # normalize `skip`/MISSING sentinels to None so the checks below drop them
    # (they're not writable and not JSON-serializable)
    inp = {k: (None if _skipped(v) else v) for k, v in inp.items()}
    fields = {}
    # the project_issuetype pill is sometimes a stripped/empty ref
    # (#{_ref(null,null,[])}); fall back to the recipe's design-time sample.
    pit = inp.get("project_issuetype") or inp.get("sample_project_issuetype")
    proj, itype = _split_project_issuetype(pit)
    if not for_update:                          # project/type are set only on create
        if proj:
            fields["project"] = {"key": proj}
        if itype:
            fields["issuetype"] = {"name": itype}
    if inp.get("summary") is not None:
        fields["summary"] = inp["summary"]
    if inp.get("description") is not None:
        fields["description"] = inp["description"]
    if inp.get("priority"):
        fields["priority"] = {"name": inp["priority"]}
    if inp.get("assignee_id"):
        fields["assignee"] = {"id": inp["assignee_id"]}
    if inp.get("reporter_id"):
        fields["reporter"] = {"id": inp["reporter_id"]}
    if inp.get("parent"):
        fields["parent"] = {"key": inp["parent"]}
    labels = _labels(inp.get("labels"))
    if labels is not None:
        fields["labels"] = labels
    # pass custom fields (customfield_xxxxx) straight through
    for k, v in inp.items():
        if k.startswith("customfield_") and v not in (None, "", [], {}):
            fields[k] = v
    return fields


def _bad_fields(err):
    """Pull offending field keys out of a Jira 400 body."""
    out = []
    body = err.body if isinstance(err.body, dict) else {}
    errs = body.get("errors")
    if isinstance(errs, dict):
        out += list(errs.keys())
    return out


_FALLBACK_PIT = {}


def _fallback_pit(client):
    """A real (project_key, issuetype) to create against when the recipe's
    project_issuetype pill resolved empty (fabricated/empty trigger). Cached."""
    if "v" in _FALLBACK_PIT:
        return _FALLBACK_PIT["v"]
    proj = None
    try:
        page = client._req("GET", "/rest/api/3/project/search", params={"maxResults": 50})
        vals = [p.get("key") for p in page.get("values", []) if p.get("key")]
        proj = vals[0] if vals else None
    except Exception:
        proj = None
    _FALLBACK_PIT["v"] = (proj, "Task")
    return _FALLBACK_PIT["v"]


def _seed_key(client):
    """A real, existing issue key (shares realize.py's single seeded issue)."""
    from test_sandbox.live.realize import jira_seed_issue
    return jira_seed_issue(client)


def _jsm_seed(client):
    """The org's real seeded service-desk request: {serviceDeskId, requestTypeId,
    issueKey} (or {} if the org has no JSM). Shared, created once."""
    from test_sandbox.live.realize import jsm_seed_request
    return jsm_seed_request(client)


def _jsm_seed_key(client):
    """A real service-desk request key to comment on (None if no JSM)."""
    return _jsm_seed(client).get("issueKey")


def _usable_key(raw):
    return raw if (isinstance(raw, str) and raw.strip()) else None


def _with_issue(client, raw_key, fn):
    """Run fn(key) against the recipe's issue key; if that key is empty (the pill
    resolved from a fabricated/empty trigger) or 404s (key points at an issue this
    org doesn't have), retry once against a real seeded issue so the op still
    exercises Jira live. Returns (key_used, result)."""
    key = _usable_key(raw_key) or _seed_key(client)
    try:
        return key, fn(key)
    except JiraError as e:
        if e.status == 404:
            sk = _seed_key(client)
            if sk and sk != key:
                return sk, fn(sk)
        raise


def _create_retry(client, fields):
    f = dict(fields)
    for _ in range(8):
        try:
            return client.create_issue(f)
        except JiraError as e:
            bad = [k for k in _bad_fields(e) if k in f]
            if not bad:
                raise
            for k in bad:
                f.pop(k, None)
    return client.create_issue(f)


def _update_retry(client, key, fields):
    f = dict(fields)
    for _ in range(8):
        try:
            return client.update_issue(key, f)
        except JiraError as e:
            bad = [k for k in _bad_fields(e) if k in f]
            if not bad:
                raise
            for k in bad:
                f.pop(k, None)
    return client.update_issue(key, f)


def make_handler(client):
    def handle(provider, operation, inp, ctx):
        # Fire-as-is: a 4xx (missing project/field/issue) is RECORDED and the run
        # continues, rather than aborting the recipe at the first bad call. This
        # mirrors Slack's soft failures and surfaces every call's outcome.
        try:
            return _handle(provider, operation, inp, ctx)
        except JiraError as e:
            ctx.log_side_effect(provider, operation, error=str(e.status),
                                detail=str(e.body)[:300])
            return {"success": False, "__jira_error__": e.body, "status": e.status}

    def _handle(provider, operation, inp, ctx):
        if not isinstance(inp, dict):
            inp = {}

        # ---- service management -----------------------------------------
        if provider == "jira_service_desk":
            if operation == "create_comment":
                # comment on the recipe's request; if its key is empty (fabricated
                # trigger) or doesn't resolve to a real service-desk request, fall
                # back to a real seeded SD request so the call writes live. Log
                # `key` so the effect scores as a real write.
                body = inp.get("body") or "Sandbox live test comment"
                pub = inp.get("public", True)
                key = _usable_key(inp.get("Issue")) or _jsm_seed_key(client)
                res = {}
                try:
                    res = client.sd_create_comment(key, body, pub) if key else {}
                except JiraError:
                    sk = _jsm_seed_key(client)
                    if sk and sk != key:
                        key, res = sk, client.sd_create_comment(sk, body, pub)
                    else:
                        raise
                ctx.log_side_effect(provider, operation, issue=key, key=key,
                                    success=isinstance(res, dict) and res.get("id") is not None)
                return res if isinstance(res, dict) else {}
            if operation == "create_customer_request":
                body = {k: inp[k] for k in
                        ("serviceDeskId", "requestTypeId", "requestFieldValues",
                         "raiseOnBehalfOf") if inp.get(k) not in (None, "", {}, [])}
                # drop request fields that resolved empty (they 400 the payload)
                rfv = {k: v for k, v in (body.get("requestFieldValues") or {}).items()
                       if v not in (None, "", {}, [])}
                seed = _jsm_seed(client)
                # empty serviceDeskId/requestTypeId (fabricated trigger) -> seed
                if not body.get("serviceDeskId"):
                    body["serviceDeskId"] = seed.get("serviceDeskId")
                if not body.get("requestTypeId"):
                    body["requestTypeId"] = seed.get("requestTypeId")
                if not rfv.get("summary"):
                    rfv["summary"] = "Sandbox live test request"
                body["requestFieldValues"] = rfv

                def _create(b):
                    return client.sd_create_request(b) if b.get("serviceDeskId") \
                        and b.get("requestTypeId") else {}
                res = {}
                try:
                    res = _create(body)
                except JiraError:
                    res = {}
                # the recipe's serviceDeskId/requestTypeId may be from another org
                # (invalid here) -> retry against the org's real seeded desk + type
                # with a minimal valid payload, so the request still writes live.
                if not (isinstance(res, dict) and res.get("issueKey")) and seed:
                    retry = {"serviceDeskId": seed.get("serviceDeskId"),
                             "requestTypeId": seed.get("requestTypeId"),
                             "requestFieldValues": {"summary": rfv.get("summary")}}
                    res = _create(retry)
                key = res.get("issueKey") if isinstance(res, dict) else None
                ctx.log_side_effect(provider, operation,
                                    serviceDeskId=body.get("serviceDeskId"),
                                    key=key, success=key is not None)
                return dict(res, key=key, issueKey=key) if isinstance(res, dict) else {}
            return {}

        # ---- platform ----------------------------------------------------
        if operation == "create_issue":
            fields = _issue_fields(inp)
            # project_issuetype can resolve empty (fabricated trigger / stripped
            # pill) -> Jira 400 "project required". Fall back to a real project so
            # the recipe still writes live, and retry the same way if the recipe's
            # own project/issuetype is invalid for this org.
            if not (fields.get("project") and fields.get("issuetype")):
                proj, itype = _fallback_pit(client)
                if proj:
                    fields["project"] = {"key": proj}
                    fields["issuetype"] = {"name": itype}
            if not fields.get("summary"):           # summary is always required
                fields["summary"] = "Sandbox live recipe test issue"
            try:
                res = _create_retry(client, fields)
            except JiraError:
                proj, itype = _fallback_pit(client)
                if not proj:
                    raise
                fields["project"] = {"key": proj}
                fields["issuetype"] = {"name": itype}
                res = _create_retry(client, fields)
            ctx.log_side_effect(provider, operation,
                                project_issuetype=inp.get("project_issuetype"),
                                key=res.get("key"))
            return dict(res, id=res.get("id"), key=res.get("key"),
                        Key=res.get("key"), success=True)

        if operation == "update_issue":
            fields = _issue_fields(inp, for_update=True)
            raw = inp.get("issuekey") or inp.get("key") or inp.get("id")
            key, _ = _with_issue(client, raw, lambda k: _update_retry(client, k, fields))
            ctx.log_side_effect(provider, operation, key=key)
            return {"key": key, "id": key, "success": True}

        if operation == "get_issue":
            raw = inp.get("id") or inp.get("issuekey") or inp.get("key")
            _, issue = _with_issue(client, raw, lambda k: client.get_issue(k, inp.get("fields")))
            return issue if isinstance(issue, dict) else {}

        if operation in ("search_issues_by_JQL", "search_issues"):
            jql = inp.get("jql") or inp.get("query") or ""
            if not (isinstance(jql, str) and jql.strip()):
                jql = _SAFE_JQL                   # empty pill -> a valid, broad query
            try:
                res = client.search_jql(jql)
            except JiraError as e:
                if e.status not in (400, 410):     # malformed JQL from a fabricated pill
                    raise
                res = client.search_jql(_SAFE_JQL)
            return res if isinstance(res, dict) else {"issues": []}

        if operation == "find_user":
            res = client.find_user(inp.get("query") or inp.get("accountId") or "")
            users = res if isinstance(res, list) else []
            first = users[0] if users else {}
            return dict(first, users=users)

        if operation == "assign_issue":
            raw = inp.get("key") or inp.get("issuekey") or inp.get("id")
            key, _ = _with_issue(client, raw,
                                 lambda k: client.assign_issue(k, inp.get("assignee_id")))
            ctx.log_side_effect(provider, operation, key=key,
                                assignee_id=inp.get("assignee_id"))
            return {"key": key, "success": True}

        if operation == "create_comment":
            raw = inp.get("key") or inp.get("issuekey") or inp.get("id")
            body = inp.get("body") if _usable_key(inp.get("body")) else "Sandbox live test comment"
            key, res = _with_issue(client, raw,
                                   lambda k: client.create_comment(k, body))
            ctx.log_side_effect(provider, operation, key=key)
            return res if isinstance(res, dict) else {}

        if operation == "get_issue_comments":
            raw = inp.get("issuekey") or inp.get("key") or inp.get("id")
            _, res = _with_issue(client, raw, lambda k: client.get_comments(k))
            return res if isinstance(res, dict) else {}

        if operation == "update_issue_status":
            raw = inp.get("issue_key") or inp.get("issuekey") or inp.get("key")
            key = _usable_key(raw) or _seed_key(client)
            want = (inp.get("transition_name") or "").strip().lower()
            key, tx = _with_issue(client, key, lambda k: client.transitions(k))
            tx = tx.get("transitions", [])
            match = next((t for t in tx if (t.get("name") or "").strip().lower() == want), None)
            if match:
                client.transition_issue(key, match["id"])
                ctx.log_side_effect(provider, operation, key=key,
                                    transition=inp.get("transition_name"))
                return {"key": key, "success": True}
            ctx.log_side_effect(provider, operation, key=key,
                                transition=inp.get("transition_name"),
                                error="no matching transition",
                                available=[t.get("name") for t in tx])
            return {"key": key, "success": False}

        # triggers / unsupported live ops -> empty (won't break the run)
        return {}

    return handle
