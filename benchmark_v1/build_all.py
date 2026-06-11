#!/usr/bin/env python3
"""
build_all.py - run the whole benchmark build (stages 1-5) in order.

  python3 build_all.py                 # full main_1k build
  python3 build_all.py --limit 20      # quick pilot on the first 20 recipes
  python3 build_all.py --ids my.txt    # custom recipe-id list
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *extra):
    cmd = [sys.executable, os.path.join(HERE, script)] + list(extra)
    print("\n=== %s %s" % (script, " ".join(extra)))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-catalog", action="store_true",
                    help="reuse the existing schemas/ catalog")
    ap.add_argument("--selfcheck", action="store_true",
                    help="finish with the harness self-consistency check")
    args = ap.parse_args()

    fx_args = []
    if args.ids:
        fx_args += ["--ids", args.ids]
    if args.limit:
        fx_args += ["--limit", str(args.limit)]

    if not args.skip_catalog:
        run("build_catalog.py")                       # Stage 1
    run("build_fixtures.py", *fx_args)                # Stages 2+3
    run("run_original.py")                            # Stage 4
    run("gen_tasks.py")                               # Stage 5
    run("build_prompts.py")                           # model-facing prompts
    if args.selfcheck:
        run("selfcheck.py")


if __name__ == "__main__":
    main()
