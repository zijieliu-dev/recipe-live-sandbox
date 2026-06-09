#!/usr/bin/env python3
"""
verify.py - check a candidate recipe against a gold reference.

  python3 verify.py <gold-id|path> <candidate-id|path>

Runs gold, forces the candidate to use gold's trigger event, and diffs the
observable side-effects. Prints a PASS/FAIL verdict with the call diff.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_sandbox.engine import verifier               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(arg):
    path = arg if os.path.exists(arg) else os.path.join(HERE, "recipes_clean", "%s.json" % arg)
    if not os.path.exists(path):
        raise SystemExit("recipe not found: %s" % arg)
    return json.load(open(path))["recipe"]


def main():
    ap = argparse.ArgumentParser(description="Verify a candidate recipe vs gold.")
    ap.add_argument("gold", help="gold recipe id or path")
    ap.add_argument("candidate", help="candidate recipe id or path")
    ap.add_argument("--input", help="optional input bundle json")
    args = ap.parse_args()

    bundle = json.load(open(args.input)) if args.input else None
    verdict = verifier.verify(_load(args.gold), _load(args.candidate), bundle=bundle)

    print("PASS" if verdict["match"] else "FAIL")
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
