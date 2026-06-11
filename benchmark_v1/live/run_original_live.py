#!/usr/bin/env python3
"""
run_original_live.py - Stage 7: live ground truth.

Runs each ORIGINAL recipe against the REAL test connectors in its `original`
namespace, reads the resulting external state back through the real APIs, and
saves the canonicalized live state diff as gold.

Outputs (gold/):
  live_groundtruth_effects.jsonl   {groundtruth_id, task_id, scenarios:[
                                     {scenario_id, status, live_effects_canonical,
                                      write_log, ...}]}     <- the live gold
  live_original_readback.jsonl     raw read-back snapshots (audit)
  live_original_traces.jsonl       control traces / errors (diagnostic)

Usage:
  python3 run_original_live.py --apps Sheets --limit 10        # Sheets pilot
  python3 run_original_live.py --ids ids.txt --keep            # keep artifacts
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from test_sandbox.benchmark_v1 import common  # noqa: E402
from test_sandbox.benchmark_v1.live import config as live_config  # noqa: E402
from test_sandbox.benchmark_v1.live import runner_lib  # noqa: E402

_APP_GROUPS = {"Sheets": "google_sheets", "Jira": "jira", "Slack": "slack",
               "SF": "salesforce"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--apps", nargs="*", help="primary apps: Sheets Jira Slack SF")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep", action="store_true", help="skip cleanup (debug)")
    ap.add_argument("--providers", nargs="*",
                    help="override which live providers to wire")
    args = ap.parse_args()

    cfg = live_config.load_env()
    only = set(args.providers) if args.providers else (
        {_APP_GROUPS[a] for a in args.apps} if args.apps else None)
    clients = live_config.build_clients(cfg, only=only)
    targets = live_config.bench_targets(cfg, clients)
    wired = [k for k, v in clients.items() if v is not None]
    print("live clients wired: %s | targets: %s" % (wired, targets),
          file=sys.stderr)

    tasks = runner_lib.select_tasks(args.ids, args.apps, limit=args.limit)
    print("running %d tasks live (original side)" % len(tasks), file=sys.stderr)

    golds, readbacks, traces = [], [], []
    for i, t in enumerate(tasks):
        doc = common.load_recipe_doc(t["source_recipe_id"])
        try:
            rows = runner_lib.run_task_live(t, doc["recipe"], "original",
                                            clients, cfg, targets, keep=args.keep)
        except Exception as e:
            traces.append({"task_id": t["task_id"], "fatal": repr(e)[:300]})
            continue
        golds.append({
            "groundtruth_id": "live_gt_%s" % t["source_recipe_id"],
            "task_id": t["task_id"],
            "recipe_id": t["source_recipe_id"],
            "live_groups": rows[0]["live_groups"] if rows else [],
            "scenarios": [
                {"scenario_id": r["scenario_id"], "status": r["status"],
                 "live_effects_canonical": r["live_effects_canonical"],
                 "n_real_writes": r["n_real_writes"],
                 "write_log": r["write_log"],
                 "readback_error": r.get("readback_error"),
                 "cleanup_ok": r["cleanup_ok"]}
                for r in rows],
        })
        for r in rows:
            readbacks.append({"task_id": t["task_id"],
                              "scenario_id": r["scenario_id"],
                              "raw": r.get("readback_raw")})
            traces.append({k: r.get(k) for k in
                           ("task_id", "scenario_id", "status", "control_trace",
                            "live_errors", "policy_violations", "flake_retries",
                            "cleanup_results")})
        runner_lib.progress(i, len(tasks))

    common.write_jsonl(os.path.join(common.GOLD_DIR, "live_groundtruth_effects.jsonl"), golds)
    common.write_jsonl(os.path.join(common.GOLD_DIR, "live_original_readback.jsonl"), readbacks)
    common.write_jsonl(os.path.join(common.GOLD_DIR, "live_original_traces.jsonl"), traces)
    ok = sum(1 for g in golds
             if all(s["live_effects_canonical"] is not None
                    and not s.get("readback_error") for s in g["scenarios"]))
    print("live gold: %d tasks (%d clean read-back) -> gold/live_groundtruth_effects.jsonl"
          % (len(golds), ok))


if __name__ == "__main__":
    main()
