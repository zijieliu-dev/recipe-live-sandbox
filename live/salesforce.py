"""
live/salesforce.py - a real-API Salesforce comp handler.

Maps Workato Salesforce operations to live REST calls (via SalesforceClient),
returning data in the same shape the mocked connector would, so the rest of the
recipe's datapills resolve unchanged.

Object is always `sobject_name`; field filters/values are the other top-level
input keys. SOQL operations carry a full `query`. If a recipe references a
field/object the org doesn't have, the API raises and the run records it -> that
recipe is auto-excluded (per the "exclude what we can't access" rule).

make_dispatch(client) returns a dispatch fn for the interpreter: salesforce ->
live, all other providers -> the normal mocked comps.dispatch.
"""
import re

from test_sandbox.salesforce_live import SalesforceError

RESERVED = {"sobject_name", "field_list", "limit", "query", "table_list",
            "query_field", "id", "since_offset", "output_schema"}


def _bad_fields(err):
    out = []
    body = err.body if isinstance(err.body, list) else [err.body]
    for e in body:
        if isinstance(e, dict):
            out += e.get("fields", []) or []
    return out


def _write_retry(write_fn, data):
    """Call write_fn(data); on a 400 naming offending fields, drop them and retry
    (handles org validation quirks like State/Country picklists)."""
    d = dict(data)
    for _ in range(6):
        try:
            return write_fn(d)
        except SalesforceError as e:
            bad = [f for f in _bad_fields(e) if f in d]
            if not bad:
                raise
            for f in bad:
                d.pop(f, None)
    return write_fn(d)

READ_OPS = {"search_sobjects", "search_sobjects_soql", "search_sobjects_soql_v2",
            "scheduled_sobject_soql_query", "scheduled_sobject_soql_query_v2",
            "get_custom_object", "get_sobject", "get_related"}
CREATE_OPS = {"create_custom_object", "create_sobject", "composite_create_sobject"}
UPDATE_OPS = {"update_sobject", "composite_update_sobject", "updated_custom_object"}

_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*$")


def _fields(field_list):
    if not isinstance(field_list, str):
        return []
    out = []
    for tok in field_list.replace(",", "\n").split("\n"):
        tok = tok.strip()
        if tok and _FIELD_RE.match(tok):
            out.append(tok)
    return out


def _lit(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return "'%s'" % s


def _filters(inp):
    return {k: v for k, v in inp.items()
            if k not in RESERVED and v not in (None, "", [], {})}


def make_handler(client):
    def handle(provider, operation, inp, ctx):
        if not isinstance(inp, dict):
            inp = {}
        sobject = inp.get("sobject_name")

        if operation == "search_sobjects":
            fields = _fields(inp.get("field_list")) or ["Id"]
            where = " AND ".join("%s = %s" % (k, _lit(v)) for k, v in _filters(inp).items())
            soql = "SELECT %s FROM %s" % (", ".join(fields), sobject)
            if where:
                soql += " WHERE " + where
            soql += " LIMIT %s" % (inp.get("limit") or 200)
            recs = client.query_all(soql)
            return {sobject: recs, "records": recs, "count": len(recs)}

        if operation in ("search_sobjects_soql", "scheduled_sobject_soql_query"):
            # v1: `query` is the WHERE clause; build the full SOQL around it
            fields = _fields(inp.get("field_list")) or ["Id"]
            soql = "SELECT %s FROM %s" % (", ".join(fields), sobject)
            where = inp.get("query")
            if where and where.strip():
                soql += " WHERE " + where
            soql += " LIMIT %s" % (inp.get("limit") or 200)
            recs = client.query_all(soql)
            out = {"records": recs, "count": len(recs)}
            if sobject:
                out[sobject] = recs
            return out

        if operation in ("search_sobjects_soql_v2", "scheduled_sobject_soql_query_v2"):
            # v2: `query` is full SOQL
            q = inp.get("query")
            recs = client.query_all(q) if q else []
            out = {"records": recs, "count": len(recs)}
            if sobject:
                out[sobject] = recs
            return out

        if operation in ("get_custom_object", "get_sobject"):
            rec = client.get(sobject, inp.get("id"))
            rec = rec if isinstance(rec, dict) else {}
            return dict(rec, **{sobject: rec}) if sobject else rec

        if operation in CREATE_OPS:
            data = _filters(inp)
            res = _write_retry(lambda d: client.create(sobject, d), data)
            ctx.log_side_effect(provider, operation, sobject=sobject, data=data, result=res)
            rid = res.get("id")
            return dict(data, Id=rid, id=rid, success=res.get("success", True))

        if operation in UPDATE_OPS:
            data = _filters(inp)
            _write_retry(lambda d: client.update(sobject, inp.get("id"), d), data)
            ctx.log_side_effect(provider, operation, sobject=sobject, id=inp.get("id"), data=data)
            return {"Id": inp.get("id"), "id": inp.get("id"), "success": True}

        if operation == "upsert_sobject":
            qf = inp.get("query_field") or "Id"
            data = _filters(inp)
            ext = data.pop(qf, None) or inp.get("Id") or inp.get("id")
            res = client.upsert(sobject, qf, ext, data)
            ctx.log_side_effect(provider, operation, sobject=sobject, query_field=qf, data=data)
            rid = res.get("id") if isinstance(res, dict) else ext
            return dict(data, Id=rid, id=rid, success=True)

        if operation == "delete_sobject":
            res = client.delete(sobject, inp.get("id"))
            ctx.log_side_effect(provider, operation, sobject=sobject, id=inp.get("id"))
            return {"id": inp.get("id"), "success": True}

        if operation == "get_sobject_schema":
            schema = client.describe(sobject)
            ctx.log_side_effect(provider, operation, sobject=sobject,
                                field_count=len(schema.get("fields", [])))
            return schema

        if operation == "__adhoc_http_action":
            # a raw REST call: verb + path (relative to the instance url)
            verb = (inp.get("verb") or "GET").upper()
            path = inp.get("path") or ""
            if path and not path.startswith("/"):
                path = "/" + path
            ctx.log_side_effect(provider, operation, verb=verb, path=path)
            try:
                return client._req(verb, path)
            except SalesforceError as e:
                return {"__http_error__": e.body}

        # triggers / unsupported live ops -> empty (won't break the run)
        return {}

    return handle


def make_dispatch(client, jira_client=None, slack_client=None):
    """Interpreter dispatch: route each live-enabled provider to its real API,
    everything else -> mocked comps.dispatch.

    salesforce              -> always live (client is required)
    jira / jira_service_desk -> live iff jira_client is given
    slack / slack_bot        -> live iff slack_client is given
    """
    from test_sandbox import comps
    sf = make_handler(client)

    jira = slack = None
    if jira_client is not None:
        from test_sandbox.live.jira import make_handler as make_jira
        jira = make_jira(jira_client)
    if slack_client is not None:
        from test_sandbox.live.slack import make_handler as make_slack
        slack = make_slack(slack_client)

    def dispatch(provider, operation, inp, ctx):
        if provider == "salesforce":
            return sf(provider, operation, inp, ctx)
        if jira is not None and provider in ("jira", "jira_service_desk"):
            return jira(provider, operation, inp, ctx)
        if slack is not None and provider in ("slack", "slack_bot"):
            return slack(provider, operation, inp, ctx)
        return comps.dispatch(provider, operation, inp, ctx)

    return dispatch
