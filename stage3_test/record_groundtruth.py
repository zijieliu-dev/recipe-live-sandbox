#!/usr/bin/env python3
"""
record_groundtruth.py - fire recipes live and record input/output ground truth.

For each candidate recipe it fires the live path ONCE (real Salesforce/Jira/Slack/
Sheets; everything else mocked deterministically), then records a ground-truth
document:

  {
    "id", "status", "success",            # success := status == "completed"
    "steps", "elapsed_sec",
    "connectors": {live_used, mocked_used, live_status},
    "live_effects": [{provider, operation, wrote, detail}],
    "input":  {trigger, config, reads},   # the exact input that produced the output
    "output": {status, side_effects, formula_errors, final_state, trace}
  }

Recipes that COMPLETE (no crash) are kept as ground truth (one json per recipe in
--outdir). Every attempt — kept or not — is logged to index.jsonl so the accounting
is honest (no silent drops). Stops once --target recipes are kept, or the pool ends.

Usage:
  python3 stage3_test/record_groundtruth.py --ids stage3_test/pool.txt --target 3000
  python3 stage3_test/record_groundtruth.py --all --limit 60 --outdir /tmp/pilot   # pilot
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.engine import loader              # noqa: E402
from test_sandbox.live import runner as live_runner  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.dirname(HERE)
CLEAN = os.path.join(SANDBOX, "recipes_clean")

LIVE = live_runner.LIVE_PROVIDERS
# classify() / live_effects() now live in live.runner so the Slack bridge and the
# CLI share the exact same ground-truth shape. Re-exported here for callers.
classify = live_runner.classify
live_effects = live_runner.live_effects


# --------------------------------------------------------------------------- #
# driver                                                                      #
# --------------------------------------------------------------------------- #
def candidate_ids(args):
    if args.ids:
        ids = [l.strip() for l in open(args.ids) if l.strip()]
    else:
        ids = sorted(f[:-5] for f in os.listdir(CLEAN) if f.endswith(".json"))
    if args.limit:
        ids = ids[:args.limit]
    return ids


def main():
    ap = argparse.ArgumentParser(description="Record live ground-truth for recipes.")
    ap.add_argument("--ids", help="file with recipe ids (one per line); default = all of recipes_clean")
    ap.add_argument("--all", action="store_true", help="explicit: use all recipes_clean ids")
    ap.add_argument("--limit", type=int, default=0, help="only consider the first N ids")
    ap.add_argument("--target", type=int, default=3000, help="stop after keeping this many completed recipes")
    ap.add_argument("--outdir", default=os.path.join(HERE, "groundtruth"))
    ap.add_argument("--org", default="my-dev-org")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds to sleep between recipes (rate-limit)")
    ap.add_argument("--no-reset", action="store_true", help="do NOT revert SF writes (default reverts)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    index_path = os.path.join(args.outdir, "index.jsonl")
    index = open(index_path, "a")

    ids = candidate_ids(args)
    clients = live_runner.build_live_clients(args.org)
    status = live_runner.live_provider_status(clients)
    sys.stderr.write("live providers wired: %s\n" % ", ".join(p for p, v in status.items() if v))
    sys.stderr.write("candidates: %d | target keep: %d | outdir: %s\n" % (len(ids), args.target, args.outdir))

    kept = crashed = errored = 0
    t0 = time.time()
    for n, rid in enumerate(ids, 1):
        path = os.path.join(CLEAN, "%s.json" % rid)
        if not os.path.exists(path):
            index.write(json.dumps({"id": rid, "status": "missing"}) + "\n"); index.flush(); continue
        doc = json.load(open(path))
        cls = classify(doc["recipe"])
        rec = {"id": rid, **{k: cls[k] for k in ("trigger_provider", "fireable", "live_used", "mocked_used", "sf_custom_schema")}}
        t = time.time()
        try:
            out = live_runner.run_one_live(doc, {}, clients, reset=not args.no_reset)
        except Exception as e:
            crashed += 1
            rec.update(status="crash", success=False, error=("%s: %s" % (type(e).__name__, e))[:160],
                       elapsed_sec=round(time.time() - t, 2))
            index.write(json.dumps(rec) + "\n"); index.flush()
            sys.stderr.write("[%d/%d] %s CRASH %s\n" % (n, len(ids), rid, rec["error"][:60]))
            continue
        elapsed = round(time.time() - t, 2)
        effs = live_effects(out["side_effects"])
        # success := ran end-to-end. "completed" = ran to the end; "stopped" = hit a
        # deliberate stop step (a clean early exit). Both are successful runs;
        # only "error" (a StepError) is a genuine failure.
        success = out["status"] in ("completed", "stopped")
        rec.update(status=out["status"], success=success,
                   steps=out["steps"], elapsed_sec=elapsed,
                   wrote=any(e["wrote"] for e in effs), live_effects=effs)

        if success:
            gt = {
                "id": rid,
                "status": out["status"],
                "success": True,
                "steps": out["steps"],
                "elapsed_sec": elapsed,
                "connectors": {"live_used": cls["live_used"], "mocked_used": cls["mocked_used"],
                               "live_status": status},
                "live_effects": effs,
                "input": {"trigger": out["trigger_fired"], "config": {}, "reads": {}},
                "output": {"status": out["status"], "side_effects": out["side_effects"],
                           "formula_errors": out["formula_errors"], "final_state": out["final_state"],
                           "trace": out["trace"]},
            }
            with open(os.path.join(args.outdir, "%s.json" % rid), "w") as f:
                json.dump(gt, f, ensure_ascii=False, default=str)
            kept += 1
        else:
            errored += 1
        index.write(json.dumps(rec, default=str) + "\n"); index.flush()

        if n % 25 == 0 or out["status"] != "completed":
            rate = kept / n * 100
            sys.stderr.write("[%d/%d] kept=%d (%.0f%%) err=%d crash=%d | %s %s %.1fs | %.1f rec/min\n" % (
                n, len(ids), kept, rate, errored, crashed, rid, out["status"], elapsed,
                n / ((time.time() - t0) / 60)))
        if kept >= args.target:
            sys.stderr.write("reached target %d\n" % args.target)
            break
        if args.sleep:
            time.sleep(args.sleep)

    index.close()
    summary = {"considered": n, "kept": kept, "errored": errored, "crashed": crashed,
               "keep_rate": round(kept / n, 3) if n else 0, "elapsed_min": round((time.time() - t0) / 60, 1)}
    with open(os.path.join(args.outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
