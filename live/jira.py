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
                res = client.sd_create_comment(inp.get("Issue"), inp.get("body"),
                                                inp.get("public", True))
                ctx.log_side_effect(provider, operation, issue=inp.get("Issue"))
                return res if isinstance(res, dict) else {}
            if operation == "create_customer_request":
                body = {k: inp[k] for k in
                        ("serviceDeskId", "requestTypeId", "requestFieldValues",
                         "raiseOnBehalfOf") if inp.get(k) not in (None, "", {}, [])}
                res = client.sd_create_request(body)
                ctx.log_side_effect(provider, operation,
                                    serviceDeskId=inp.get("serviceDeskId"))
                return res if isinstance(res, dict) else {}
            return {}

        # ---- platform ----------------------------------------------------
        if operation == "create_issue":
            fields = _issue_fields(inp)
            res = _create_retry(client, fields)
            ctx.log_side_effect(provider, operation,
                                project_issuetype=inp.get("project_issuetype"),
                                key=res.get("key"))
            return dict(res, id=res.get("id"), key=res.get("key"),
                        Key=res.get("key"), success=True)

        if operation == "update_issue":
            key = inp.get("issuekey") or inp.get("key") or inp.get("id")
            fields = _issue_fields(inp, for_update=True)
            _update_retry(client, key, fields)
            ctx.log_side_effect(provider, operation, key=key)
            return {"key": key, "id": key, "success": True}

        if operation == "get_issue":
            key = inp.get("id") or inp.get("issuekey") or inp.get("key")
            issue = client.get_issue(key, inp.get("fields"))
            return issue if isinstance(issue, dict) else {}

        if operation in ("search_issues_by_JQL", "search_issues"):
            res = client.search_jql(inp.get("jql") or inp.get("query") or "")
            return res if isinstance(res, dict) else {"issues": []}

        if operation == "find_user":
            res = client.find_user(inp.get("query") or inp.get("accountId") or "")
            users = res if isinstance(res, list) else []
            first = users[0] if users else {}
            return dict(first, users=users)

        if operation == "assign_issue":
            key = inp.get("key") or inp.get("issuekey") or inp.get("id")
            client.assign_issue(key, inp.get("assignee_id"))
            ctx.log_side_effect(provider, operation, key=key,
                                assignee_id=inp.get("assignee_id"))
            return {"key": key, "success": True}

        if operation == "create_comment":
            key = inp.get("key") or inp.get("issuekey") or inp.get("id")
            res = client.create_comment(key, inp.get("body"))
            ctx.log_side_effect(provider, operation, key=key)
            return res if isinstance(res, dict) else {}

        if operation == "get_issue_comments":
            key = inp.get("issuekey") or inp.get("key") or inp.get("id")
            return client.get_comments(key)

        if operation == "update_issue_status":
            key = inp.get("issue_key") or inp.get("issuekey") or inp.get("key")
            want = (inp.get("transition_name") or "").strip().lower()
            tx = client.transitions(key).get("transitions", [])
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
