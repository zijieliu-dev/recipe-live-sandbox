"""Jira canonicalizer: project / issue type / summary / description / labels /
priority for creates; key fields for updates, comments, transitions."""
from . import generic


def _project_and_type(inp):
    pit = inp.get("project_issuetype") or inp.get("sample_project_issuetype") or ""
    if isinstance(pit, str) and ":" in pit:
        proj, itype = pit.split(":", 1)
        return generic.norm_text(proj), generic.norm_text(itype)
    proj = inp.get("project_key") or inp.get("project") or (pit if pit else None)
    return (generic.norm_text(proj) or None,
            generic.norm_text(inp.get("issue_type") or inp.get("issuetype")) or None)


def _labels(v):
    if isinstance(v, list):
        return sorted(generic.norm_text(x) for x in v if x)
    if isinstance(v, str) and v.strip():
        return sorted(generic.norm_text(x) for x in v.replace(";", ",").split(",") if x.strip())
    return []


def canonicalize(effect):
    inp = effect.get("input") or {}
    if not isinstance(inp, dict):
        inp = {}
    fam = generic.family(effect.get("provider"), effect.get("operation"))
    proj, itype = _project_and_type(inp)
    out = {
        "provider": effect.get("provider"),
        "family": fam,
        "project": proj,
        "issue_type": itype,
    }
    if fam in ("jira.create_issue", "jira.update_issue"):
        out["summary"] = generic.norm_text(inp.get("summary")) or None
        out["description"] = generic.norm_text(inp.get("description")) or None
        out["labels"] = _labels(inp.get("labels"))
        out["priority"] = generic.norm_text(inp.get("priority")) or None
        custom = {k: generic.scrub(v) for k, v in inp.items()
                  if str(k).startswith("customfield_") and v not in (None, "", [], {})}
        if custom:
            out["custom_fields"] = custom
    if fam == "jira.comment":
        out["body"] = generic.norm_text(inp.get("body") or inp.get("comment_body")) or None
        out["issue"] = generic.norm_text(inp.get("issuekey") or inp.get("key")
                                         or inp.get("id") or inp.get("Issue")) or None
    if fam == "jira.transition":
        out["issue"] = generic.norm_text(inp.get("key") or inp.get("issuekey")
                                         or inp.get("id")) or None
        out["to_status"] = generic.norm_text(inp.get("status") or inp.get("status_name")
                                             or inp.get("transition")) or None
    if fam == "jira.assign":
        out["issue"] = generic.norm_text(inp.get("key") or inp.get("issuekey")
                                         or inp.get("id")) or None
        out["assignee"] = generic.norm_text(inp.get("assignee_id")) or None
    return out
