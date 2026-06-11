#!/usr/bin/env python3
"""
cleanup_live.py - Stage 10: re-run pending/failed cleanups.

Every live run saves its namespace (with cleanup_plan + cleanup_results) under
live/materialized/. This tool retries everything that is not confirmed ok -
covering --keep runs, crashed runs, and transient API failures.

Usage:
  python3 cleanup_live.py            # retry all non-ok cleanups
  python3 cleanup_live.py --dry-run  # list what would be cleaned
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from test_sandbox.benchmark_v1.live import config as live_config  # noqa: E402
from test_sandbox.benchmark_v1.live import namespace  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(namespace.MATERIALIZED_DIR,
                                          "*", "*", "*.json")))
    pending = []
    for p in paths:
        with open(p) as f:
            ns = json.load(f)
        # a plan step is pending unless an identical result row is ok
        todo = []
        results = ns.get("cleanup_results") or []
        for s in ns.get("cleanup_plan") or []:
            ok = any(all(r.get(k) == v for k, v in s.items()) and r.get("ok")
                     for r in results)
            if not ok:
                todo.append(s)
        if todo:
            pending.append((p, ns, todo))

    print("%d namespaces with pending cleanup steps" % len(pending))
    if args.dry_run:
        for p, ns, todo in pending:
            for s in todo:
                print("  %s: %s" % (os.path.relpath(p, namespace.MATERIALIZED_DIR), s))
        return

    if not pending:
        return
    cfg = live_config.load_env()
    clients = live_config.build_clients(cfg)
    n_ok = n_fail = 0
    for p, ns, todo in pending:
        ns2 = dict(ns)
        ns2["cleanup_plan"] = todo
        results = namespace.cleanup(ns2, clients)
        ns["cleanup_results"] = (ns.get("cleanup_results") or []) + results
        with open(p, "w") as f:
            json.dump(ns, f, indent=1, default=str)
        n_ok += sum(1 for r in results if r["ok"])
        n_fail += sum(1 for r in results if not r["ok"])
    print("cleanup retried: %d ok, %d failed" % (n_ok, n_fail))


if __name__ == "__main__":
    main()
