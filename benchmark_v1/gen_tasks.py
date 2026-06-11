#!/usr/bin/env python3
"""
gen_tasks.py - Stage 5: benchmark task items + natural-language descriptions.

The description is generated from the EXECUTED structure (semantic graph +
gold control trace), never from recipe comments, and reveals intended behavior
without leaking block ids/UUIDs/aliases or the recipe JSON itself.

Outputs:
  tasks/main_1k.jsonl              one item per recipe with clean gold
  tasks/control_flow_stress.jsonl  the subset with >1 fixture scenario

Usage:  python3 gen_tasks.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common  # noqa: E402

_OPERAND_WORDS = {
    "equals_to": "is", "not_equals_to": "is not", "present": "is present",
    "blank": "is blank", "contains": "contains", "not_contains": "does not contain",
    "starts_with": "starts with", "not_starts_with": "does not start with",
    "ends_with": "ends with", "not_ends_with": "does not end with",
    "greater_than": "is greater than", "less_than": "is less than",
    "is_true": "is true", "is_not_true": "is not true",
}


def _humanize_op(name):
    return str(name or "").replace("_", " ").strip()


def _pill(ref):
    path = ".".join(str(p) for p in ref.get("path", []))
    if ref.get("special") == ["current_item"]:
        return "the current item" + ((".%s" % path) if path else "")
    return path or "its output"


def _cond_text(node):
    parts = []
    for leaf in node.get("conditions") or []:
        lhs = (_pill(leaf["lhs_refs"][0]) if len(leaf.get("lhs_refs") or []) == 1
               else "the value")
        op = _OPERAND_WORDS.get(leaf.get("operand"), leaf.get("operand") or "matches")
        rhs = leaf.get("rhs")
        if leaf.get("operand") in ("present", "blank", "is_true", "is_not_true") \
                or rhs in (None, ""):
            parts.append("%s %s" % (lhs, op))
        else:
            parts.append("%s %s \"%s\"" % (lhs, op, rhs))
    joiner = " %s " % ("or" if node.get("condition_combine") == "or" else "and")
    return joiner.join(parts) if parts else "the condition holds"


def _literals_text(lits, limit=4):
    if not lits:
        return ""
    pairs = []
    for k, v in list(lits.items())[:limit]:
        s = str(v)
        pairs.append("%s=%s" % (k, s if len(s) <= 60 else s[:60] + "..."))
    return " (" + ", ".join(pairs) + ")"


def _trigger_sentence(node):
    prov, name = node.get("provider"), node.get("name") or ""
    lits = node.get("literal_inputs") or {}
    if prov == "clock":
        bits = [lits[k] for k in ("trigger_every", "time_unit", "trigger_at",
                                  "timezone") if lits.get(k)]
        sched = " ".join(str(b) for b in bits)
        return ("Build an automation that runs on a schedule%s."
                % ((": " + sched) if sched else ""))
    if name.startswith("new_or_updated"):
        what = _humanize_op(name[len("new_or_updated"):]) or "record"
        return ("Build an automation that fires when a %s is created or updated in %s%s."
                % (what.strip(" _"), prov, _literals_text(lits)))
    if name.startswith(("new_", "created_")):
        what = _humanize_op(name.split("_", 1)[1]) or "record"
        return ("Build an automation that fires when a new %s appears in %s%s."
                % (what, prov, _literals_text(lits)))
    if name.startswith("updated_"):
        what = _humanize_op(name.split("_", 1)[1]) or "record"
        return ("Build an automation that fires when a %s is updated in %s%s."
                % (what, prov, _literals_text(lits)))
    return ("Build an automation triggered by the '%s' event from %s%s."
            % (_humanize_op(name), prov, _literals_text(lits)))


def _action_sentence(node, alias_steps):
    prov, name = node.get("provider"), node.get("name")
    lits = node.get("literal_inputs") or {}
    refs = node.get("refs") or []
    feeds = sorted({alias_steps.get(r["source_alias"]) for r in refs
                    if alias_steps.get(r["source_alias"])}, key=str)
    feed_txt = ""
    if feeds:
        feed_txt = ", using data from %s" % (
            " and ".join("the trigger" if f == "trigger" else "step %s" % f
                         for f in feeds[:3]))
    obj = node.get("object")
    obj_txt = (" on '%s'" % obj) if obj and str(obj) not in json.dumps(list(lits.values()), default=str) else ""
    return "%s: %s%s%s%s." % (prov, _humanize_op(name), obj_txt,
                              _literals_text(lits), feed_txt)


def describe(graph, gold):
    """Deterministic imperative description + behavior contract."""
    nodes = graph["nodes"]
    alias_steps = {}
    for n in nodes:
        if n.get("alias"):
            alias_steps[n["alias"]] = ("trigger" if n["keyword"] == "trigger"
                                       else n["number"])
    lines = []
    trig = nodes[0] if nodes else {}
    lines.append(_trigger_sentence(trig))
    lines.append("Then:")
    for n in nodes[1:]:
        indent = "  " * max(n.get("depth", 1) - 1, 0)
        kw = n["keyword"]
        if kw == "action":
            lines.append("%s- %s" % (indent, _action_sentence(n, alias_steps)))
        elif kw in ("if", "elsif"):
            word = "If" if kw == "if" else "Otherwise, if"
            lines.append("%s- %s %s:" % (indent, word, _cond_text(n)))
        elif kw == "else":
            lines.append("%s- Otherwise:" % indent)
        elif kw == "foreach":
            src = n.get("source_refs") or []
            src_txt = (_pill(src[0]) + " from step %s" % alias_steps.get(
                src[0]["source_alias"], "?")) if len(src) == 1 else "the list"
            lines.append("%s- For each item in %s:" % (indent, src_txt))
        elif kw == "stop":
            lines.append("%s- Stop the run here." % indent)
        elif kw == "try":
            lines.append("%s- Try the following (continue via the error handler on failure):" % indent)
        elif kw == "catch":
            lines.append("%s- On error:" % indent)
        elif kw == "repeat":
            lines.append("%s- Repeat:" % indent)

    # behavior contract from the gold positive scenario
    pos = next((s for s in gold["scenarios"] if s["scenario_id"] == "positive"),
               gold["scenarios"][0])
    eff = pos["effects_canonical"]
    contract = []
    if eff:
        contract.append("Expected observable behavior on the provided fixture: "
                        "%d external write(s):" % len(eff))
        for e in eff[:8]:
            tgt = e.get("channel") or e.get("project") or e.get("sheet") \
                or e.get("sobject") or e.get("object") or ""
            contract.append("  * %s -> %s%s" % (
                e.get("family"), tgt, "" if not e.get("text") else
                " (message includes the referenced record data)"))
        if len(eff) > 8:
            contract.append("  * ... and %d more" % (len(eff) - 8))
    else:
        contract.append("Expected observable behavior on the provided fixture: "
                        "no external writes - the run only reads "
                        "(it must still complete with the same reads and no writes).")
    if pos["status"] == "stopped":
        contract.append("The run is expected to end via a stop step (status 'stopped').")
    return "\n".join(lines) + "\n\n" + "\n".join(contract)


def main():
    common.ensure_dirs()
    golds = {g["recipe_id"]: g for g in common.read_jsonl(common.GT_EFFECTS)}
    meta = {e["id"]: e for e in common.main_1k_entries()}

    tasks, stress = [], []
    seq = 0
    for rid in sorted(golds, key=lambda x: int(x) if x.isdigit() else 0):
        gpath = os.path.join(common.GRAPHS_DIR, "%s.json" % rid)
        fpath = os.path.join(common.FIXTURES_DIR, "%s.json" % rid)
        if not (os.path.exists(gpath) and os.path.exists(fpath)):
            continue
        with open(gpath) as f:
            graph = json.load(f)
        with open(fpath) as f:
            fixture = json.load(f)
        gold = golds[rid]
        doc = common.load_recipe_doc(rid)
        feats = common.recipe_features(doc["recipe"])

        catalog_ids = sorted({"%s::%s" % (n["provider"], n["name"])
                              for n in graph["nodes"] if n.get("provider")})
        controls = sorted({"control.%s" % n["keyword"] for n in graph["nodes"]
                           if n["keyword"] not in ("trigger", "action")})
        m = meta.get(rid, {})
        task = {
            "task_id": common.task_id_for(rid, seq),
            "source_recipe_id": rid,
            "description": describe(graph, gold),
            "runtime_inputs": fixture.get("config") or {},
            "initial_state_id": fixture["fixture_id"],
            "allowed_connectors": graph["providers"],
            "action_catalog_ids": catalog_ids + controls,
            "output_format": "recipe_json",
            "groundtruth_id": gold["groundtruth_id"],
            "scenarios": [s["scenario_id"] for s in gold["scenarios"]],
            "tier": m.get("tier"),
            "primary_app": m.get("primary_app"),
            "features": feats,
        }
        tasks.append(task)
        if len(gold["scenarios"]) > 1:
            stress.append({"task_id": task["task_id"],
                           "source_recipe_id": rid,
                           "scenarios": task["scenarios"]})
        seq += 1

    common.write_jsonl(common.MAIN_TASKS, tasks)
    common.write_jsonl(common.STRESS_TASKS, stress)
    print("tasks: %d (control-flow stress subset: %d) -> %s"
          % (len(tasks), len(stress), common.TASKS_DIR))


if __name__ == "__main__":
    main()
