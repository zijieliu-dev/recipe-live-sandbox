#!/usr/bin/env python3
"""
report.py - run every cleaned recipe through the sandbox and summarize coverage.

  python3 report.py                 # all recipes -> report.json + console summary
  python3 report.py --limit 500     # quick sample

Produces the coverage dashboard: status distribution, terminal %, the share of
recipes with zero formula errors, and the formula-gap list split into
missing-data (awaiting better inputs) vs. real engine gaps (the to-do list).
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_sandbox.engine import interpreter            # noqa: E402
from test_sandbox.engine.context import RunContext      # noqa: E402
from test_sandbox import comps                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

_DATA = re.compile(r"not (numeric|a date)|NoneType|MISSING")
_UNIMPL = re.compile(r"unimplemented method \.(\w+[?!]?)")


def _classify(err):
    if _DATA.search(err):
        return "missing-data", "missing-data (None)"
    m = _UNIMPL.search(err)
    if m:
        return "engine", "method:%s" % m.group(1)
    return "engine", err[:48]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipes-dir", default=os.path.join(HERE, "recipes_clean"))
    ap.add_argument("--out", default=os.path.join(HERE, "report.json"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.recipes_dir, "*.json")))
    if args.limit:
        files = files[:args.limit]

    status = Counter()
    causes = Counter()
    crashes = []
    clean = n_data = n_engine = total_steps = total_se = 0
    n = 0
    t0 = time.time()

    for fp in files:
        n += 1
        ctx = RunContext()
        try:
            res = interpreter.run(json.load(open(fp))["recipe"], ctx,
                                  dispatch=comps.dispatch)
        except Exception as e:
            status["CRASH"] += 1
            if len(crashes) < 10:
                crashes.append({"recipe": os.path.basename(fp), "error": repr(e)})
            continue
        status[res["status"]] += 1
        total_steps += len(res["trace"])
        total_se += len(res["side_effects"])
        if not ctx.formula_errors:
            clean += 1
        for e in ctx.formula_errors:
            kind, cause = _classify(e)
            causes[cause] += 1
            if kind == "missing-data":
                n_data += 1
            else:
                n_engine += 1

    terminal = status["completed"] + status["stopped"]
    report = {
        "recipes": n,
        "elapsed_sec": round(time.time() - t0, 1),
        "status": dict(status.most_common()),
        "terminal_pct": round(100 * terminal / max(1, n), 2),
        "crashes": status.get("CRASH", 0),
        "recipes_zero_formula_errors": clean,
        "recipes_zero_formula_errors_pct": round(100 * clean / max(1, n), 1),
        "formula_errors": {"missing_data": n_data, "engine_gap": n_engine},
        "avg_steps": round(total_steps / max(1, n), 1),
        "avg_side_effects": round(total_se / max(1, n), 1),
        "top_causes": dict(causes.most_common(25)),
        "crash_samples": crashes,
    }
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)

    # console summary
    print("recipes=%d  (%.1fs)" % (n, report["elapsed_sec"]))
    for k, v in status.most_common():
        print("  %-12s %5d (%.1f%%)" % (k, v, 100 * v / n))
    print("terminal: %.2f%%  | crashes: %d" % (report["terminal_pct"], report["crashes"]))
    print("recipes with ZERO formula errors: %d (%.1f%%)"
          % (clean, report["recipes_zero_formula_errors_pct"]))
    print("formula errors: %d missing-data + %d engine-gap" % (n_data, n_engine))
    print("avg steps/recipe=%.1f  avg side-effects/recipe=%.1f"
          % (report["avg_steps"], report["avg_side_effects"]))
    print("\ntop formula-gap causes (the to-do list):")
    for c, v in causes.most_common(15):
        print("  %5d  %s" % (v, c))
    print("\nwrote %s" % args.out)


if __name__ == "__main__":
    main()
