#!/usr/bin/env python3
"""
run_original.py - Stage 4: run each ORIGINAL recipe on its fixture scenarios
and record the canonical ground truth.

Per recipe -> one gold row (gold/groundtruth_effects.jsonl):

  {
    "groundtruth_id": "gt_<rid>",
    "recipe_id": "<rid>",
    "scenarios": [
      {"scenario_id": "positive",
       "status": "completed|stopped",
       "effects_canonical": [...],     # the scored answer (writes)
       "reads_canonical": [...],       # diagnostic (reads signature)
       "state_diff": {...},            # lookup/db-table writes
       "required_tokens": [...]}       # BENCH marker + key literals (lenient)
      ...
    ]
  }

Diagnostic step traces go to gold/original_traces.jsonl. Recipes whose gold
run errors are excluded (gold/excluded.jsonl) - the benchmark only keeps tasks
whose ground truth is clean.

Usage:  python3 run_original.py [--ids file] [--limit N]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common, sandbox, canonicalizers  # noqa: E402


def required_tokens(effects_canonical, marker):
    """Semantic tokens a lenient match must reproduce: the BENCH marker (when
    it reached an effect) plus channel/project/sheet targets."""
    toks = set()
    blob = json.dumps(effects_canonical, ensure_ascii=False, default=str)
    if marker in blob:
        toks.add(marker)
    for e in effects_canonical:
        for k in ("channel", "project", "sheet", "spreadsheet", "sobject"):
            v = e.get(k)
            if v and re.match(r"^[\w#@\-\. :/]{1,60}$", str(v)):
                toks.add(str(v))
    return sorted(toks)


def gold_for(recipe_id):
    doc = common.load_recipe_doc(recipe_id)
    recipe = doc["recipe"]
    with open(os.path.join(common.FIXTURES_DIR, "%s.json" % recipe_id)) as f:
        fixture = json.load(f)
    marker = common.bench_marker(recipe_id)

    scen_rows, trace_rows = [], []
    for scen in fixture.get("scenarios") or [{"scenario_id": "positive", "overrides": []}]:
        record, _ = sandbox.run_on_fixture(recipe, fixture, overrides=scen["overrides"])
        if record["status"] == "error":
            return None, {"recipe_id": recipe_id, "reason": "gold_run_error",
                          "scenario": scen["scenario_id"],
                          "error": str((record["trace"] or [{}])[-1])[:200]}
        canon = canonicalizers.canonicalize_run(record)
        scen_rows.append({
            "scenario_id": scen["scenario_id"],
            "status": canon["status"],
            "effects_canonical": canon["effects_canonical"],
            "reads_canonical": canon["reads_canonical"],
            "state_diff": canon["state_diff"],
            "required_tokens": required_tokens(canon["effects_canonical"], marker),
        })
        trace_rows.append({
            "recipe_id": recipe_id,
            "scenario_id": scen["scenario_id"],
            "control_trace": canon["control_trace"],
            "n_calls": len(record["calls"]),
            "formula_errors": len(record["formula_errors"]),
        })
    gold = {"groundtruth_id": "gt_%s" % recipe_id, "recipe_id": recipe_id,
            "scenarios": scen_rows}
    return (gold, trace_rows), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="file of recipe ids; default = built fixtures")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    common.ensure_dirs()
    if args.ids:
        ids = [l.strip() for l in open(args.ids) if l.strip()]
    else:
        ids = sorted(f[:-5] for f in os.listdir(common.FIXTURES_DIR)
                     if f.endswith(".json"))
    if args.limit:
        ids = ids[:args.limit]

    golds, traces, excluded = [], [], []
    for i, rid in enumerate(ids):
        try:
            ok, err = gold_for(rid)
        except Exception as e:
            ok, err = None, {"recipe_id": rid, "reason": "exception",
                             "error": repr(e)[:200]}
        if err:
            excluded.append(err)
        else:
            gold, trows = ok
            golds.append(gold)
            traces.extend(trows)
        if (i + 1) % 200 == 0:
            print("  %d/%d gold runs" % (i + 1, len(ids)), file=sys.stderr)

    common.write_jsonl(common.GT_EFFECTS, golds)
    common.write_jsonl(common.GT_TRACES, traces)
    common.write_jsonl(common.GT_EXCLUDED, excluded)
    n_eff = sum(len(s["effects_canonical"]) for g in golds for s in g["scenarios"])
    print("gold: %d recipes (%d scenarios, %d effects), %d excluded -> %s"
          % (len(golds), sum(len(g["scenarios"]) for g in golds), n_eff,
             len(excluded), common.GOLD_DIR))


if __name__ == "__main__":
    main()
