#!/usr/bin/env python3
"""
run_candidate_live.py - Stage 8: run candidate recipes live.

For each prediction: parse -> normalize -> validate (same gates as the
sandbox track), then execute in the CANDIDATE namespace with real writes and
read-back. Results are written per run name; score_predictions_live.py
compares them against the live gold.

Usage:
  python3 run_candidate_live.py predictions.jsonl --name run1 [--limit N] [--keep]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from test_sandbox.benchmark_v1 import common  # noqa: E402
from test_sandbox.benchmark_v1.build_catalog import load_catalog  # noqa: E402
from test_sandbox.benchmark_v1.normalize_recipe import (RecipeNormalizer,  # noqa: E402
                                                        RecipeNormalizationError)
from test_sandbox.benchmark_v1.run_candidate import strip_json_fences  # noqa: E402
from test_sandbox.benchmark_v1.live import config as live_config  # noqa: E402
from test_sandbox.benchmark_v1.live import runner_lib  # noqa: E402
import json  # noqa: E402


def prepare_candidate(pred, task, normalizer):
    """raw output -> (recipe, None) or (None, fail_row)."""
    out = pred.get("output")
    if isinstance(out, (dict, list)):
        raw = out
    else:
        try:
            raw = json.loads(strip_json_fences(str(out)))
        except json.JSONDecodeError as e:
            return None, {"fail_stage": "invalid_json", "detail": str(e)[:300]}
    try:
        doc = normalizer.normalize(raw)
    except RecipeNormalizationError as e:
        return None, {"fail_stage": "invalid_recipe_structure", "detail": str(e)[:300]}
    errors, warnings = normalizer.validate(doc["recipe"],
                                           task.get("allowed_connectors"))
    if errors:
        return None, {"fail_stage": "schema_error",
                      "detail": "; ".join(errors[:10]),
                      "validation_warnings": warnings[:10]}
    return doc["recipe"], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("--name", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--providers", nargs="*")
    args = ap.parse_args()

    cfg = live_config.load_env()
    clients = live_config.build_clients(
        cfg, only=set(args.providers) if args.providers else None)
    targets = live_config.bench_targets(cfg, clients)
    print("live clients wired: %s" % [k for k, v in clients.items() if v],
          file=sys.stderr)

    tasks_by_id = {t["task_id"]: t for t in common.read_jsonl(common.MAIN_TASKS)}
    live_gold = {g["task_id"]: g for g in common.read_jsonl(
        os.path.join(common.GOLD_DIR, "live_groundtruth_effects.jsonl"))}
    normalizer = RecipeNormalizer(catalog=load_catalog())

    preds = common.read_jsonl(args.predictions)
    if args.limit:
        preds = preds[:args.limit]

    rows = []
    n = len(preds)
    for i, pred in enumerate(preds):
        task = tasks_by_id.get(pred.get("task_id"))
        base = {"task_id": pred.get("task_id")}
        if not task:
            rows.append({**base, "fail_stage": "unknown_task"})
            continue
        if task["task_id"] not in live_gold:
            rows.append({**base, "fail_stage": "no_live_gold"})
            continue
        recipe, fail = prepare_candidate(pred, task, normalizer)
        if fail:
            rows.append({**base, **fail, "scenarios": []})
            continue
        try:
            # candidates reuse the gold run's provider groups, update-target
            # patch templates and materialization needs - same world, own side
            g = live_gold[task["task_id"]]
            scen_rows = runner_lib.run_task_live(
                task, recipe, "candidate", clients, cfg, targets,
                keep=args.keep, groups=g.get("live_groups"),
                live_overrides=g.get("live_overrides"),
                needs=g.get("live_needs"))
        except Exception as e:
            rows.append({**base, "fail_stage": "live_run_error",
                         "detail": repr(e)[:300], "scenarios": []})
            continue
        rows.append({**base, "fail_stage": None, "scenarios": scen_rows})
        runner_lib.progress(i, n)

    out = os.path.join(common.RESULTS_DIR, "%s.live_candidate_effects.jsonl" % args.name)
    common.write_jsonl(out, rows)
    print("candidate live runs -> %s" % out)


if __name__ == "__main__":
    main()
