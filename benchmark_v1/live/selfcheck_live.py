#!/usr/bin/env python3
"""
selfcheck_live.py - live-harness validation.

The ORIGINAL recipe, stripped to the minimal model-output contract, runs as a
candidate in the CANDIDATE namespace and is scored against its own live gold
(produced in the ORIGINAL namespace). Should be ~100%; anything lower means
the live harness drops tasks: incomplete rebinding, unstable read-back,
un-normalized dynamic ids, environment pollution, or eventual consistency.

Usage:
  python3 selfcheck_live.py --apps Sheets --limit 10
  (requires run_original_live.py to have produced live gold for these tasks)
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from test_sandbox.benchmark_v1 import common  # noqa: E402
from test_sandbox.benchmark_v1.selfcheck import minimalize  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps", nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    gold_ids = {g["task_id"] for g in common.read_jsonl(
        os.path.join(common.GOLD_DIR, "live_groundtruth_effects.jsonl"))}
    tasks = [t for t in common.read_jsonl(common.MAIN_TASKS)
             if t["task_id"] in gold_ids
             and (not args.apps or t.get("primary_app") in args.apps)]
    if args.limit:
        tasks = tasks[:args.limit]

    preds = []
    for t in tasks:
        doc = common.load_recipe_doc(t["source_recipe_id"])
        preds.append({"task_id": t["task_id"],
                      "output": json.dumps({"recipe": minimalize(doc["recipe"])},
                                           ensure_ascii=False)})
    path = os.path.join(common.RESULTS_DIR, "selfcheck_live.predictions.jsonl")
    common.write_jsonl(path, preds)
    print("wrote %d live self-predictions" % len(preds), file=sys.stderr)

    cmd = [sys.executable, os.path.join(HERE, "run_candidate_live.py"),
           path, "--name", "selfcheck_live"]
    if args.keep:
        cmd.append("--keep")
    subprocess.run(cmd, check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "score_predictions_live.py"),
                    "--name", "selfcheck_live"], check=True)


if __name__ == "__main__":
    main()
