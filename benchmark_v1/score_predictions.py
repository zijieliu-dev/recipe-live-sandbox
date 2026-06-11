#!/usr/bin/env python3
"""
score_predictions.py - score a predictions file against the benchmark.

Input:  predictions.jsonl, one row per task:
          {"task_id": "main_1k_000123", "output": "<raw model output string>"}
        ("output" may also be the already-parsed recipe object.)

Output: results/<name>.results.jsonl  per-task verdicts (with per-scenario detail)
        results/<name>.metrics.json   the headline + diagnostic metrics

Headline metric: pass@1_execution_equivalent_strict (no repair loop - a task
counts only if the FIRST emitted recipe passes every scenario).

Usage:
  python3 score_predictions.py predictions.jsonl [--name run1] [--tasks tasks/main_1k.jsonl]
"""
import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common  # noqa: E402
from test_sandbox.benchmark_v1.build_catalog import load_catalog  # noqa: E402
from test_sandbox.benchmark_v1.normalize_recipe import RecipeNormalizer  # noqa: E402
from test_sandbox.benchmark_v1.run_candidate import evaluate_one  # noqa: E402


def _rate(num, den):
    return round(num / den, 4) if den else None


def compute_metrics(results, tasks_by_id):
    n = len(results)
    by = lambda pred: [r for r in results if pred(r)]  # noqa: E731
    passed = by(lambda r: r["strict_pass"])

    def split_rate(key_fn):
        groups = defaultdict(lambda: [0, 0])
        for r in results:
            t = tasks_by_id.get(r["task_id"])
            if not t:
                continue
            k = key_fn(t)
            if k is None:
                continue
            groups[k][1] += 1
            groups[k][0] += 1 if r["strict_pass"] else 0
        return {k: _rate(a, b) for k, (a, b) in sorted(groups.items())}

    feats = lambda t: t.get("features") or {}  # noqa: E731
    metrics = {
        "n_tasks_scored": n,
        "pass@1_execution_equivalent_strict": _rate(len(passed), n),
        "pass@1_execution_equivalent_lenient": _rate(
            len(by(lambda r: r["lenient_pass"])), n),
        "valid_json_rate": _rate(len(by(lambda r: r.get("valid_json"))), n),
        "valid_recipe_schema_rate": _rate(len(by(lambda r: r.get("valid_recipe"))), n),
        "sandbox_run_success_rate": _rate(len(by(lambda r: r.get("ran"))), n),
        "effect_match_rate": _rate(len(by(lambda r: r.get("effect_match"))), n),
        "extra_write_rate": _rate(
            len(by(lambda r: r.get("extra_write_count", 0) > 0)), n),
        "missing_write_rate": _rate(
            len(by(lambda r: r.get("missing_effect_count", 0) > 0)), n),
        "fail_stage_counts": dict(sorted(
            ((s, len(by(lambda r, s=s: r.get("fail_stage") == s)))
             for s in ("invalid_json", "invalid_recipe_structure", "schema_error",
                       "run_error", "effect_mismatch", "pass")), key=lambda kv: -kv[1])),
        "by_tier": split_rate(lambda t: t.get("tier")),
        "by_primary_app": split_rate(lambda t: t.get("primary_app")),
        "read_task_pass_rate": split_rate(
            lambda t: "read" if t.get("tier") == "live_read" else None).get("read"),
        "write_task_pass_rate": split_rate(
            lambda t: "write" if t.get("tier") == "live_write" else None).get("write"),
        "linear_recipe_pass_rate": split_rate(
            lambda t: "linear" if feats(t).get("is_linear") else None).get("linear"),
        "control_flow_recipe_pass_rate": split_rate(
            lambda t: "cf" if not feats(t).get("is_linear") else None).get("cf"),
        "foreach_recipe_pass_rate": split_rate(
            lambda t: "fe" if feats(t).get("has_foreach") else None).get("fe"),
        "if_else_recipe_pass_rate": split_rate(
            lambda t: "ie" if feats(t).get("has_if") else None).get("ie"),
        "single_app_pass_rate": split_rate(
            lambda t: "single" if len([p for p in t.get("allowed_connectors", [])
                                       if p in ("salesforce", "jira", "jira_service_desk",
                                                "slack", "slack_bot", "google_sheets")]) <= 1
            else None).get("single"),
        "multi_app_pass_rate": split_rate(
            lambda t: "multi" if len([p for p in t.get("allowed_connectors", [])
                                      if p in ("salesforce", "jira", "jira_service_desk",
                                               "slack", "slack_bot", "google_sheets")]) > 1
            else None).get("multi"),
        "scenario_strict_pass_rate": _rate(
            sum(r.get("n_scenarios_passed_strict", 0) for r in results),
            sum(r.get("n_scenarios", 0) for r in results)),
    }
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions", help="predictions.jsonl: {task_id, output}")
    ap.add_argument("--name", default=None, help="run name for the result files")
    ap.add_argument("--tasks", default=common.MAIN_TASKS)
    args = ap.parse_args()

    common.ensure_dirs()
    name = args.name or os.path.splitext(os.path.basename(args.predictions))[0]
    tasks_by_id = {t["task_id"]: t for t in common.read_jsonl(args.tasks)}
    golds = {g["groundtruth_id"]: g for g in common.read_jsonl(common.GT_EFFECTS)}
    normalizer = RecipeNormalizer(catalog=load_catalog())

    results = []
    for i, pred in enumerate(common.read_jsonl(args.predictions)):
        task = tasks_by_id.get(pred.get("task_id"))
        if not task:
            results.append({"task_id": pred.get("task_id"), "pass": False,
                            "strict_pass": False, "lenient_pass": False,
                            "fail_stage": "unknown_task"})
            continue
        gold = golds[task["groundtruth_id"]]
        results.append(evaluate_one(task, gold, pred.get("output"),
                                    normalizer=normalizer))
        if (i + 1) % 100 == 0:
            print("  %d predictions scored" % (i + 1), file=sys.stderr)

    metrics = compute_metrics(results, tasks_by_id)
    res_path = os.path.join(common.RESULTS_DIR, "%s.results.jsonl" % name)
    met_path = os.path.join(common.RESULTS_DIR, "%s.metrics.json" % name)
    common.write_jsonl(res_path, results)
    with open(met_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))
    print("\nresults -> %s\nmetrics -> %s" % (res_path, met_path))


if __name__ == "__main__":
    main()
