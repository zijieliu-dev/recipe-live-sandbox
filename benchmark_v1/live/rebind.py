"""rebind.py - live resource rebinding via fixture patching.

A recipe that UPDATES/COMMENTS-ON an external object carries that object's
key/id as a datapill from fixture data (e.g. issuekey = #{_ref(...)} ->
"value_512" - a fabricated key that doesn't exist live). Instead of letting
the live mapper seed arbitrary fallback objects, the live track:

  1. statically finds which FIXTURE paths feed those key inputs in the
     ORIGINAL recipe (`update_target_templates`),
  2. materializes a real bench target per run (namespace.py),
  3. patches the fixture at those paths with the real key before running
     (`instantiate`), identically for gold and candidate - candidates use
     their own aliases but read the SAME fixture data, so their refs resolve
     to the same real key.

Templates are recipe-independent (fixture target + path + kind) and are
stored in the live gold so candidate runs reproduce them exactly.
"""
import re

from test_sandbox.engine import loader, refs
from test_sandbox.benchmark_v1.live import config as live_config

_PURE_REF = re.compile(r"^\s*#\{\s*_ref\(.*\)\s*\}\s*$", re.S)

# (group, operation) -> the input fields that carry the target key/id
_KEYED_WRITES = {
    ("jira", "update_issue"): ("issuekey", "key", "id"),
    ("jira", "create_comment"): ("key", "issuekey", "id"),
    ("jira", "update_issue_status"): ("issue_key", "issuekey", "key"),
    ("jira", "assign_issue"): ("key", "issuekey", "id"),
}
_JSM_COMMENT_FIELDS = ("Issue",)
_SF_UPDATE_OPS = {"update_sobject", "updated_custom_object"}


def _pure_ref_target(value, trig_alias, alias_keys):
    """Resolve the fixture field feeding a key/id input -> (target, path).

    Covers a pure '#{_ref(...)}' AND a formula wrapping exactly one ref
    (e.g. '=_ref(...).split(",").first'): patching the underlying fixture
    field with a plain real id makes either resolve to it. Multi-ref values
    are skipped (can't know which feeds the key)."""
    if not isinstance(value, str) or "_ref(" not in value:
        return None
    found = refs.find_refs(value)
    if len(found) != 1:
        return None
    r = found[0]
    path = [p for p in r["path"] if isinstance(p, (str, int))]
    if any(isinstance(p, dict) for p in r["path"]):
        return None                      # current_item etc.: not statically safe
    if r["line"] == trig_alias:
        return "trigger", path
    key = (alias_keys or {}).get(r["line"])
    if key:
        return "reads:%s" % key, path
    return None


def update_target_templates(recipe, fixture):
    """Scan the ORIGINAL recipe for keyed external writes; return patch
    templates [{target, path, kind, sobject?}] + the `needs` dict telling
    materialization which bench targets to create."""
    trig = loader.get_trigger(recipe) or {}
    trig_alias = trig.get("as")
    alias_keys = fixture.get("alias_keys") or {}
    templates, needs = [], {}

    for step in loader.iter_steps(recipe):
        if step.get("keyword") != "action":
            continue
        prov, op = step.get("provider"), step.get("name")
        group = live_config.provider_group(prov)
        inp = step.get("input") or {}
        if prov == "jira_service_desk" and op == "create_comment":
            for f in _JSM_COMMENT_FIELDS:
                tgt = _pure_ref_target(inp.get(f), trig_alias, alias_keys)
                if tgt:
                    templates.append({"target": tgt[0], "path": tgt[1],
                                      "kind": "jsm_request_key"})
                    needs["jsm_target"] = True
        elif (group, op) in _KEYED_WRITES:
            for f in _KEYED_WRITES[(group, op)]:
                tgt = _pure_ref_target(inp.get(f), trig_alias, alias_keys)
                if tgt:
                    templates.append({"target": tgt[0], "path": tgt[1],
                                      "kind": "jira_issue_key"})
                    needs["jira_target"] = True
                    break
        elif group == "salesforce" and op in _SF_UPDATE_OPS:
            sob = inp.get("sobject_name")
            tgt = _pure_ref_target(inp.get("id"), trig_alias, alias_keys)
            if tgt and isinstance(sob, str) and sob:
                templates.append({"target": tgt[0], "path": tgt[1],
                                  "kind": "sf_record_id", "sobject": sob})
                needs.setdefault("sf_targets", set()).add(sob)

    if "sf_targets" in needs:
        needs["sf_targets"] = sorted(needs["sf_targets"])
    # dedup templates
    seen, out = set(), []
    for t in templates:
        k = (t["target"], tuple(t["path"]), t["kind"], t.get("sobject"))
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out, needs


def instantiate(templates, ns):
    """Templates + a side's namespace -> concrete fixture overrides."""
    out = []
    for t in templates or []:
        value = None
        if t["kind"] == "jira_issue_key":
            value = ns.get("jira_target_key")
        elif t["kind"] == "jsm_request_key":
            value = ns.get("jsm_target_key")
        elif t["kind"] == "sf_record_id":
            value = (ns.get("sf_target_ids") or {}).get(t.get("sobject"))
        if value:
            out.append({"target": t["target"], "path": t["path"], "value": value})
    return out
