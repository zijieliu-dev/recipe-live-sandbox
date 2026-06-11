#!/usr/bin/env python3
"""
build_fixtures.py - Stage 3: synthetic inputs + initial sandbox state per recipe.

For each source recipe:
  1. record-run it (external reads fabricated from the ORIGINAL's schemas,
     seeded provider::operation -> recipe-independent) to capture the world
     state the recipe touches: trigger event + read outputs + write outputs;
  2. inject a unique benchmark marker (BENCH_<id>) into free-text fields that
     do NOT feed any branch condition;
  3. branch-satisfaction loop: mutate the fixture so if-conditions whose lhs is
     a pure reference into fixtured data evaluate TRUE (positive path), re-
     recording any reads that only become reachable once a branch opens;
  4. emit scenario variants: "positive" (the fixture as built) plus, when a
     taken branch is statically flippable, a "branch_<n>_false" negative
     scenario expressed as value overrides.

Outputs: fixtures/<recipe_id>.json and graphs/<recipe_id>.json

Usage:
  python3 build_fixtures.py --ids <file|->        # default: stage3 main_1k ids
  python3 build_fixtures.py --limit 20
"""
import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common, ops, sandbox, semantic_graph  # noqa: E402

_PURE_REF = re.compile(r"^\s*#\{\s*_ref\(.*\)\s*\}\s*$", re.S)
_TEXTY = {"subject", "title", "summary", "description", "body", "text",
          "message", "comment", "note", "content", "details"}
_MAX_ROUNDS = 3


# --------------------------------------------------------------------------- #
# branch fixing                                                               #
# --------------------------------------------------------------------------- #
def desired_value(operand, rhs, want_true):
    """Value for the lhs field so that (lhs operand rhs) == want_true.
    Returns (ok, value). Only literal rhs values are handled."""
    if isinstance(rhs, str) and ("#{" in rhs or "_ref(" in rhs):
        return False, None
    neg = {"equals_to": "not_equals_to", "not_equals_to": "equals_to",
           "present": "blank", "blank": "present",
           "contains": "not_contains", "not_contains": "contains",
           "starts_with": "not_starts_with", "not_starts_with": "starts_with",
           "ends_with": "not_ends_with", "not_ends_with": "ends_with",
           "is_true": "is_not_true", "is_not_true": "is_true",
           "greater_than": "less_than", "less_than": "greater_than"}
    if not want_true:
        operand = neg.get(operand)
        if operand is None:
            return False, None
    other = "__BENCH_OTHER__"
    if operand == "present":
        return True, "BENCH_PRESENT"
    if operand == "blank":
        return True, ""
    if operand == "is_true":
        return True, True
    if operand == "is_not_true":
        return True, False
    if operand == "equals_to":
        return True, rhs
    if operand == "not_equals_to":
        return True, other if str(rhs) != other else other + "2"
    if operand == "contains":
        return (True, str(rhs)) if rhs not in (None, "") else (False, None)
    if operand == "not_contains":
        v = other if str(rhs) not in other else "zz9"
        return True, v
    if operand == "starts_with":
        return (True, str(rhs) + "_x") if rhs not in (None, "") else (False, None)
    if operand == "not_starts_with":
        return True, other if not other.startswith(str(rhs)) else "zz9"
    if operand == "ends_with":
        return (True, "x_" + str(rhs)) if rhs not in (None, "") else (False, None)
    if operand == "not_ends_with":
        return True, other if not other.endswith(str(rhs)) else "zz9"
    if operand in ("greater_than", "less_than"):
        try:
            n = float(rhs)
        except (TypeError, ValueError):
            return False, None
        v = n + 1 if operand == "greater_than" else n - 1
        return True, int(v) if v == int(v) else v
    return False, None


def _enclosing_foreach(graph_nodes, node):
    by_num = {n["number"]: n for n in graph_nodes}
    cur = node
    while cur and cur.get("parent") is not None:
        cur = by_num.get(cur["parent"])
        if cur and cur["keyword"] == "foreach":
            return cur
    return None


def leaf_target(leaf, if_node, graph, trig_alias, alias_keys):
    """Resolve a condition leaf's lhs to (fixture_target, path) or None.
    fixture_target is "trigger" or "reads:<key>"."""
    if not isinstance(leaf.get("lhs"), str) or not _PURE_REF.match(leaf["lhs"]):
        return None
    if len(leaf["lhs_refs"]) != 1:
        return None
    ref = leaf["lhs_refs"][0]
    alias, path, special = ref["source_alias"], list(ref["path"]), ref["special"]
    if special and special != ["current_item"]:
        return None
    if special == ["current_item"]:
        # lhs digs into the current foreach item: retarget to the loop's source
        fe = _enclosing_foreach(graph["nodes"], if_node)
        if not fe or len(fe.get("source_refs") or []) != 1:
            return None
        src = fe["source_refs"][0]
        if src["special"]:
            return None
        alias = src["source_alias"]
        path = list(src["path"]) + path
    if alias == trig_alias:
        return "trigger", path
    key = alias_keys.get(alias)
    if key:
        return "reads:%s" % key, path
    return None


def branch_overrides(if_node, graph, trig_alias, alias_keys, want_true):
    """Overrides making EVERY leaf of this if evaluate to want_true (sound for
    any and/or compound). None when any leaf is not statically fixable."""
    leaves = if_node.get("conditions") or []
    if not leaves:
        return None
    out = []
    for leaf in leaves:
        tgt = leaf_target(leaf, if_node, graph, trig_alias, alias_keys)
        if not tgt:
            return None
        ok, value = desired_value(leaf.get("operand"), leaf.get("rhs"), want_true)
        if not ok:
            return None
        out.append({"target": tgt[0], "path": tgt[1], "value": value})
    return out


def apply_to_fixture(fixture, overrides):
    """Mutate the fixture in place with branch-fix overrides. Returns #applied."""
    n = 0
    for ov in overrides:
        if ov["target"] == "trigger":
            base = fixture.get("trigger_event")
        else:
            base = (fixture.get("reads") or {}).get(ov["target"][6:])
        if base is not None and sandbox.set_path(base, ov["path"], ov["value"]):
            n += 1
    return n


# --------------------------------------------------------------------------- #
# marker injection                                                            #
# --------------------------------------------------------------------------- #
def _protected_fields(graph):
    """Field names that feed any branch condition - never inject markers there."""
    names = set()
    for dotted in graph["condition_field_paths"]:
        path = dotted.split(":", 1)[1]
        if path:
            names.add(path.split(".")[-1])
    return names


def inject_markers(obj, marker, protected):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if (isinstance(v, str) and k in _TEXTY and k not in protected
                    and marker not in v):
                obj[k] = (v + " " + marker).strip()
            else:
                inject_markers(v, marker, protected)
    elif isinstance(obj, list):
        for x in obj:
            inject_markers(x, marker, protected)


# --------------------------------------------------------------------------- #
# per-recipe build                                                            #
# --------------------------------------------------------------------------- #
def build_one(recipe_id):
    doc = common.load_recipe_doc(recipe_id)
    recipe = doc["recipe"]
    graph = semantic_graph.build(recipe)
    trig_alias = sandbox.trigger_alias(recipe)
    marker = common.bench_marker(recipe_id)

    # 1. initial record run (trigger fabricated by the engine)
    rd = sandbox.RecordingDispatch()
    record, ctx = sandbox.run_recipe(recipe, rd, trigger_event=None, config={})
    trigger_event = copy.deepcopy(ctx.step_outputs.get(trig_alias)) or {}

    fixture = {
        "fixture_id": "fixture_%s" % recipe_id,
        "recipe_id": recipe_id,
        "clock": {"now": common.DEFAULT_NOW},
        "config": {},
        "trigger_event": trigger_event,
        "reads": rd.reads_state,
        "writes_out": rd.writes_out,
        "alias_keys": rd.alias_keys,
        "state": {},
    }

    # 2. benchmark marker into branch-safe free-text fields
    protected = _protected_fields(graph)
    inject_markers(fixture["trigger_event"], marker, protected)
    for v in fixture["reads"].values():
        inject_markers(v, marker, protected)

    # 3. branch satisfaction (positive path), re-recording newly reachable reads
    if_nodes = [n for n in graph["nodes"] if n["keyword"] in ("if", "elsif")]
    for _ in range(_MAX_ROUNDS):
        rd = sandbox.RecordingDispatch(seed_reads=fixture["reads"],
                                       seed_writes=fixture["writes_out"],
                                       alias_keys=fixture["alias_keys"])
        record, ctx = sandbox.run_recipe(
            recipe, rd, trigger_event=fixture["trigger_event"],
            config=fixture["config"])
        taken = {e["step"]: e["taken"] for e in record["control_trace"]
                 if e["keyword"] in ("if", "elsif")}
        progressed = False
        for n in if_nodes:
            if taken.get(n["number"]) is False:
                ovs = branch_overrides(n, graph, trig_alias,
                                       fixture["alias_keys"], want_true=True)
                if ovs and apply_to_fixture(fixture, ovs):
                    progressed = True
        if not progressed:
            break

    # 4. final positive run + scenario variants
    final_record, _ = sandbox.run_on_fixture(recipe, fixture)
    taken = {e["step"]: e["taken"] for e in final_record["control_trace"]
             if e["keyword"] in ("if", "elsif")}
    scenarios = [{"scenario_id": "positive", "overrides": []}]
    for n in if_nodes:
        if taken.get(n["number"]) is True:
            ovs = branch_overrides(n, graph, trig_alias,
                                   fixture["alias_keys"], want_true=False)
            if not ovs:
                continue
            # record any reads only reachable on the negative path, so gold and
            # candidate see the same world there too (no schema fallback)
            fx_neg = sandbox.apply_overrides(fixture, ovs)
            rd_neg = sandbox.RecordingDispatch(seed_reads=fx_neg["reads"],
                                               seed_writes=fx_neg["writes_out"],
                                               alias_keys=dict(fixture["alias_keys"]))
            sandbox.run_recipe(recipe, rd_neg,
                               trigger_event=fx_neg["trigger_event"],
                               config=fx_neg["config"])
            for k, v in rd_neg.reads_state.items():
                if k not in fixture["reads"]:
                    inject_markers(v, marker, protected)
                    fixture["reads"][k] = v
            for k, v in rd_neg.writes_out.items():
                fixture["writes_out"].setdefault(k, v)
            fixture["alias_keys"].update(rd_neg.alias_keys)

            neg_record, _ = sandbox.run_on_fixture(recipe, fixture, overrides=ovs)
            neg_taken = {e["step"]: e["taken"] for e in neg_record["control_trace"]
                         if e["keyword"] in ("if", "elsif")}
            if neg_taken.get(n["number"]) is False:    # flip verified end-to-end
                scenarios.append({"scenario_id": "branch_%s_false" % n["number"],
                                  "overrides": ovs})
            break                                       # one negative scenario

    fixture["scenarios"] = scenarios
    summary = {
        "recipe_id": recipe_id,
        "status": final_record["status"],
        "n_effects": len(final_record["effects"]),
        "n_reads": len(final_record["reads"]),
        "branches_taken": sum(1 for v in taken.values() if v),
        "branches_total": len(taken),
        "n_scenarios": len(scenarios),
    }
    return fixture, graph, summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="file of recipe ids; default = stage3 main_1k")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    common.ensure_dirs()
    if args.ids:
        ids = [l.strip() for l in open(args.ids) if l.strip()]
    else:
        ids = [e["id"] for e in common.main_1k_entries()]
    if args.limit:
        ids = ids[:args.limit]

    n_ok, n_fail = 0, 0
    summaries = []
    for i, rid in enumerate(ids):
        try:
            fixture, graph, summary = build_one(rid)
        except Exception as e:
            n_fail += 1
            summaries.append({"recipe_id": rid, "error": repr(e)[:200]})
            continue
        with open(os.path.join(common.FIXTURES_DIR, "%s.json" % rid), "w") as f:
            json.dump(fixture, f, ensure_ascii=False, default=str)
        with open(os.path.join(common.GRAPHS_DIR, "%s.json" % rid), "w") as f:
            json.dump(graph, f, ensure_ascii=False, default=str)
        summaries.append(summary)
        n_ok += 1
        if (i + 1) % 100 == 0:
            print("  %d/%d fixtures built" % (i + 1, len(ids)), file=sys.stderr)

    common.write_jsonl(os.path.join(common.FIXTURES_DIR, "build_summary.jsonl"),
                       summaries)
    print("fixtures: %d ok, %d failed -> %s" % (n_ok, n_fail, common.FIXTURES_DIR))


if __name__ == "__main__":
    main()
