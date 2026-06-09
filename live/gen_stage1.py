#!/usr/bin/env python3
"""
gen_stage1.py - materialize the stage-1 test set.

For each of the 10 selected recipes, create stage1_test/<id>/ with:
  recipe.md        - the recipe spec (trigger, SF ops, workflow, branch conditions)
  test_samples.md  - >=10 input samples covering each trigger-driven branch

Input samples are trigger-event bundles (the recipe's entry input). For live
runs, Salesforce reads come from the real org (seeded), so samples vary the
trigger payload: persona variations + per-condition true/false coverage.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.engine import loader, refs   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.dirname(HERE)
OUT = os.path.join(os.path.dirname(SANDBOX), "stage1_test")

NAMES = ["Alice Anderson", "Bob Brown", "Carol Clark", "David Davis", "Emma Evans",
         "Frank Foster", "Grace Green", "Henry Hill", "Ivy Irwin", "Jack Jones"]


# --------------------------------------------------------------------------- #
# schema + condition extraction                                               #
# --------------------------------------------------------------------------- #
def flatten(schema, prefix=""):
    out = []
    if not isinstance(schema, list):
        return out
    for f in schema:
        if not isinstance(f, dict):
            continue
        name = f.get("name")
        if not name:
            continue
        path = "%s.%s" % (prefix, name) if prefix else name
        t = (f.get("type") or "").lower()
        if t == "object" and f.get("properties"):
            out += flatten(f["properties"], path)
        else:
            out.append({"path": path, "type": t, "label": f.get("label", name)})
    return out


def refs_into_trigger(recipe, alias):
    """Dotted paths the recipe actually reads from the trigger output (via _ref)."""
    paths = set()

    def scan(n):
        if isinstance(n, str):
            for r in refs.find_refs(n):
                if r["line"] == alias:
                    segs = [p for p in r["path"] if isinstance(p, str)]
                    if segs:
                        paths.add(".".join(segs))
        elif isinstance(n, list):
            for x in n:
                scan(x)
        elif isinstance(n, dict):
            for v in n.values():
                scan(v)

    scan(recipe)
    return paths


def get_fields(recipe, trig, alias):
    """Merge schema-declared scalar fields with the fields the recipe actually
    reads from the trigger (the latter reveal sub-fields of opaque objects)."""
    schema_leaves = flatten(trig.get("extended_output_schema") or []) if trig else []
    refpaths = refs_into_trigger(recipe, alias) if alias else set()
    fields, seen = [], set()
    for p in sorted(refpaths):
        fields.append({"path": p, "type": "", "label": p})
        seen.add(p)
    for f in schema_leaves:
        if f["type"] == "object" or f["path"] in seen:
            continue
        if any(rp == f["path"] or rp.startswith(f["path"] + ".") for rp in refpaths):
            continue
        fields.append(f)
        seen.add(f["path"])
    return fields


def conditions(recipe, trig_alias):
    """List branch conditions, mapping lhs to a trigger field path when possible."""
    res = []

    def walk_cond(node):
        if not isinstance(node, dict):
            return
        if node.get("type") == "compound":
            for c in node.get("conditions", []):
                walk_cond(c)
            return
        op = node.get("operand")
        lhs = node.get("lhs", "")
        rhs = node.get("rhs", "")
        field = None
        if isinstance(lhs, str):
            for r in refs.find_refs(lhs):
                if r["line"] == trig_alias:
                    field = ".".join(str(p) for p in r["path"] if isinstance(p, str))
        res.append({"operand": op, "field": field, "rhs": rhs, "lhs": lhs})

    for s in loader.iter_steps(recipe):
        if s.get("keyword") in ("if", "elsif"):
            walk_cond(s.get("input"))
    return res


# --------------------------------------------------------------------------- #
# value generation                                                            #
# --------------------------------------------------------------------------- #
def val_for(field, i, variant="base"):
    name = field["path"].lower()
    t = field["type"]
    person = NAMES[i % len(NAMES)]
    if variant == "blank":
        return ""
    if "email" in name:
        return "%s@example.com" % person.split()[0].lower()
    if "first" in name:
        return person.split()[0]
    if "last" in name:
        return person.split()[1]
    if "name" in name:
        return person
    if t in ("integer", "number"):
        return 10 + i
    if t == "boolean":
        return variant != "false"
    if "id" in name:
        return "%s_%03d" % (name.split(".")[-1], i)
    if "date" in name or t in ("date", "date_time"):
        return "2026-06-%02d" % (i % 27 + 1)
    return "%s_value_%d" % (name.split(".")[-1], i)


def set_path(d, dotted, value):
    keys = dotted.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def base_sample(fields, i):
    trig = {}
    for f in fields:
        set_path(trig, f["path"], val_for(f, i))
    return trig


def condition_samples(fields, conds, idx0):
    """For each condition tied to a trigger field, a TRUE and FALSE sample."""
    samples = []
    i = idx0
    for c in conds:
        if not c["field"]:
            continue
        op = c["operand"]
        rhs = c["rhs"]
        for truth in (True, False):
            trig = base_sample(fields, i)
            if op in ("present",):
                set_path(trig, c["field"], "present_value" if truth else "")
            elif op in ("blank",):
                set_path(trig, c["field"], "" if truth else "nonblank_value")
            elif op in ("equals_to", "is"):
                set_path(trig, c["field"], rhs if truth else (str(rhs) + "_DIFF"))
            elif op in ("not_equals_to",):
                set_path(trig, c["field"], (str(rhs) + "_DIFF") if truth else rhs)
            elif op in ("contains",):
                set_path(trig, c["field"], ("x%sx" % rhs) if truth else "no_match")
            elif op in ("greater_than", "less_than"):
                try:
                    base = float(rhs)
                except (TypeError, ValueError):
                    base = 10
                delta = 1 if (op == "greater_than") == truth else -1
                set_path(trig, c["field"], int(base + delta))
            elif op in ("is_true",):
                set_path(trig, c["field"], truth)
            else:
                set_path(trig, c["field"], "value" if truth else "")
            samples.append({
                "intent": "condition `%s %s %s` -> %s" % (c["field"], op, rhs, truth),
                "trigger": trig,
            })
            i += 1
    return samples


# --------------------------------------------------------------------------- #
# markdown writers                                                            #
# --------------------------------------------------------------------------- #
def recipe_md(meta, recipe, fields, conds):
    steps = list(loader.iter_steps(recipe))
    L = []
    L.append("# Recipe `%s`" % meta["id"])
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append("| **Mode** | %s |" % ("READ-only" if meta["readonly"] else "WRITE (mutates org)"))
    L.append("| **SF function(s)** | %s |" % ", ".join(meta["cats"]))
    L.append("| **SF operation(s)** | %s |" % ", ".join(meta["ops"]))
    L.append("| **Salesforce object(s)** | %s |" % ", ".join(meta["objects"]))
    L.append("| **Triggered by** | `%s` (%s) |" % (meta["trigger"], meta["task"]))
    L.append("| **Total steps** | %d |" % meta["steps"])
    L.append("")
    L.append("## Trigger input fields")
    if fields:
        L.append("| field | type |")
        L.append("|---|---|")
        for f in fields:
            L.append("| `%s` | %s |" % (f["path"], f["type"] or "?"))
    else:
        L.append("_No structured trigger input fields (event/scheduled/SF-triggered)._")
    L.append("")
    L.append("## Branch conditions")
    if conds:
        for c in conds:
            tag = "trigger field `%s`" % c["field"] if c["field"] else "non-trigger (SF/computed) data"
            L.append("- `%s %s %s` — on %s" % (c["field"] or c["lhs"][:40], c["operand"], c["rhs"], tag))
    else:
        L.append("_No if/elsif branches._")
    L.append("")
    L.append("## Workflow (step sequence)")
    for s in steps:
        kw = s.get("keyword")
        if kw in ("action", "trigger"):
            L.append("- #%s %s `%s::%s`" % (s.get("number"), kw, s.get("provider"), s.get("name")))
        else:
            L.append("- #%s %s" % (s.get("number"), kw))
    L.append("")
    return "\n".join(L)


def samples_md(meta, samples):
    L = []
    L.append("# Test samples — recipe `%s`" % meta["id"])
    L.append("")
    L.append("%d input samples. Each is a trigger-event bundle (the recipe's entry "
             "input). Salesforce reads come from the live org (seeded per run); "
             "these samples vary the trigger payload to exercise branches." % len(samples))
    L.append("")
    for i, s in enumerate(samples, 1):
        L.append("## Sample %d — %s" % (i, s["intent"]))
        L.append("```json")
        L.append(json.dumps({"trigger": s["trigger"]}, indent=2))
        L.append("```")
        L.append("")
    return "\n".join(L)


def main():
    selected = json.load(open(os.path.join(HERE, "selected.json")))
    os.makedirs(OUT, exist_ok=True)
    for meta in selected:
        rid = meta["id"]
        recipe = loader.load(os.path.join(SANDBOX, "recipes_clean", "%s.json" % rid))["recipe"]
        trig = loader.get_trigger(recipe)
        trig_alias = trig.get("as") if trig else None
        fields = get_fields(recipe, trig, trig_alias)
        conds = conditions(recipe, trig_alias)

        # >=10 samples: personas + per-condition true/false coverage
        samples = [{"intent": "persona %s (all fields populated)" % NAMES[i],
                    "trigger": base_sample(fields, i)} for i in range(10)]
        samples += condition_samples(fields, conds, 100)

        folder = os.path.join(OUT, rid)
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, "recipe.md"), "w").write(recipe_md(meta, recipe, fields, conds))
        open(os.path.join(folder, "test_samples.md"), "w").write(samples_md(meta, samples))
        print("  %s -> %d samples, %d fields, %d conditions"
              % (rid, len(samples), len(fields), len(conds)))

    print("\nwrote %d recipe folders to %s" % (len(selected), OUT))


if __name__ == "__main__":
    main()
