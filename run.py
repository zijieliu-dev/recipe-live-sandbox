#!/usr/bin/env python3
"""
run.py - execute one recipe in the sandbox and print its result.

  python3 run.py <recipe-id|path>                 # fabricate all inputs (mocked)
  python3 run.py 129122215 --input bundle.json     # supply trigger/reads/state
  python3 run.py 129122215 --full-state            # also dump final primitive state

  python3 run.py 93505634 --live                   # FIRE live: real Salesforce, rest mocked
  python3 run.py 93505634 --live --reset           # ...and restore the init table after
  python3 run.py 93505634 --live --trace           # ...show the full step trace

Input bundle (all keys optional):
  {
    "trigger": {...},                  # trigger event; omit -> fabricated from schema
    "reads":   {"<step-alias>": {...}},# override an external read's output
    "config":  {...},                  # recipe input[...] config
    "state":   {"lookup_tables": {}, "variables": {}, ...},
    "clock":   {"now": "2026-06-01T00:00:00+00:00"}
  }
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_sandbox.engine import interpreter            # noqa: E402
from test_sandbox.engine.context import RunContext      # noqa: E402
from test_sandbox import comps                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def resolve(recipe_arg):
    if os.path.exists(recipe_arg):
        return recipe_arg
    p = os.path.join(HERE, "recipes_clean", "%s.json" % recipe_arg)
    if os.path.exists(p):
        return p
    raise SystemExit("recipe not found: %s" % recipe_arg)


def main():
    ap = argparse.ArgumentParser(description="Run one recipe in the sandbox.")
    ap.add_argument("recipe", help="recipe id or path to a cleaned recipe json")
    ap.add_argument("--input", help="path to an input bundle json")
    ap.add_argument("--full-state", action="store_true",
                    help="include final primitive state in the output")
    ap.add_argument("--trace", action="store_true", help="include the full step trace")
    ap.add_argument("--live", action="store_true",
                    help="fire against REAL Salesforce (others mocked); auth via sf CLI")
    ap.add_argument("--reset", action="store_true",
                    help="with --live: restore the init table after firing")
    ap.add_argument("--diff", action="store_true",
                    help="with --live: print the old->new DB changes the run made (via the change-tracker)")
    ap.add_argument("--org", default="my-dev-org", help="sf CLI target org (with --live)")
    ap.add_argument("--sample", type=int, default=0,
                    help="with --live: which sample to fire (0-9); each targets a different row")
    args = ap.parse_args()

    doc = json.load(open(resolve(args.recipe)))
    bundle = json.load(open(args.input)) if args.input else {}
    recipe = doc["recipe"]

    if args.live:
        # fire against the real org; recipe builds its own trigger from real data.
        # All live-run logic lives in live/runner.py (shared with the recorder).
        from test_sandbox.live import runner as live_runner

        clients = live_runner.build_live_clients(args.org)
        status = live_runner.live_provider_status(clients)
        sys.stderr.write("live providers: %s\n" % " ".join(
            p for p in ("salesforce", "jira", "slack", "google_sheets") if status.get(p)))
        full = live_runner.run_one_live(doc, bundle, clients, sample=args.sample,
                                        reset=args.reset, want_diff=args.diff)
        out = {k: full[k] for k in
               ("id", "status", "steps", "side_effects", "formula_errors")}
        out["sample"] = full["sample"]
        out["trigger_fired"] = full["trigger_fired"]
        if args.trace:
            out["trace"] = full["trace"]
        if args.full_state:
            out["final_state"] = full["final_state"]
        if args.diff:
            out["db_diff"] = full["db_diff"]
            _print_diff(full["db_diff"], reverted=args.reset)
    else:
        fixtures = {
            "trigger": bundle.get("trigger"),
            "config": bundle.get("config", {}),
            "reads": bundle.get("reads", {}),
        }
        ctx = RunContext(
            fixtures=fixtures,
            initial_state=bundle.get("state"),
            now=(bundle.get("clock") or {}).get("now"),
        )
        res = interpreter.run(recipe, ctx, dispatch=comps.dispatch)
        out = {
            "id": doc.get("id"),
            "status": res["status"],
            "steps": len(res["trace"]),
            "side_effects": res["side_effects"],
            "formula_errors": ctx.formula_errors,
        }
        if args.trace:
            out["trace"] = res["trace"]
        if args.full_state:
            out["final_state"] = res["final_state"]
    print(json.dumps(out, indent=2, default=str))


def _print_diff(diff, reverted=False):
    """Human-readable old->new DB change log (to stderr, above the JSON)."""
    sys.stderr.write("\n=== DB changes this run%s ===\n"
                     % (" (reverted by --reset)" if reverted else ""))
    if not diff:
        sys.stderr.write("  (none)\n\n"); return
    for d in diff:
        if d["op"] == "create":
            sys.stderr.write("  + create %s %s  %s\n" % (
                d["sobject"], d["id"], d.get("new") or ""))
        elif d["op"] == "update":
            sys.stderr.write("  ~ update %s %s\n" % (d["sobject"], d["id"]))
            for f, ov in d.get("fields", {}).items():
                sys.stderr.write("       %s: %r -> %r\n" % (f, ov.get("old"), ov.get("new")))
        elif d["op"] == "delete":
            sys.stderr.write("  - delete %s %s\n" % (d["sobject"], d["id"]))
    sys.stderr.write("\n")


if __name__ == "__main__":
    main()
