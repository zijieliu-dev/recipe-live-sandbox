"""Salesforce canonicalizer: object type + the semantic record (field map),
volatile/system fields dropped."""
from . import generic

_SYSTEM = {"sobject_name", "object", "object_type", "id", "Id",
           "all_or_none", "batch_size"}


def _record_fields(inp):
    out = {}
    for k, v in inp.items():
        if k in _SYSTEM or k in generic.VOLATILE:
            continue
        if isinstance(v, (dict, list)):
            out[k] = generic.scrub(v)
        elif v not in (None, ""):
            out[k] = generic.norm_text(v) if isinstance(v, str) else v
    return out


def canonicalize(effect):
    inp = effect.get("input") or {}
    if not isinstance(inp, dict):
        inp = {}
    out = {
        "provider": "salesforce",
        "family": generic.family("salesforce", effect.get("operation")),
        "sobject": effect.get("object")
        or generic.norm_text(inp.get("sobject_name")) or None,
        "record": _record_fields(inp),
    }
    rid = inp.get("id") or inp.get("Id")
    if rid and effect.get("operation") != "create_sobject":
        out["record_ref"] = generic.norm_text(rid)
    return out
