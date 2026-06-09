#!/usr/bin/env python3
"""
save_recipes.py - put both the RAW and CLEANED recipe into each stage-1 folder,
and verify that cleaning changed only datapill *syntax*, not the recipe logic.

  recipe_raw.json   - original code_sanitized straight from the CSV
  recipe_clean.json - after clean.py (datapill dialects -> _ref, escaping peeled)

Verification: step count and the keyword sequence must be identical between raw
and clean (cleaning normalizes _dp(...) / _('data...') strings only).
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
csv.field_size_limit(sys.maxsize)

from test_sandbox.engine import loader   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.dirname(HERE)
DESKTOP = os.path.dirname(SANDBOX)
STAGE1 = os.path.join(DESKTOP, "stage1_test")
CSV = os.path.join(DESKTOP, "standalone_recipes.csv")


def keyword_seq(recipe):
    return [(s.get("number"), s.get("keyword")) for s in loader.iter_steps(recipe)]


def main():
    ids = {m["id"] for m in json.load(open(os.path.join(HERE, "selected.json")))}

    # pull the raw recipe JSON for each id from the CSV
    raw = {}
    with open(CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["id"] in ids:
                raw[row["id"]] = json.loads(row["code_sanitized"])
                if len(raw) == len(ids):
                    break

    print("recipe       raw-steps  clean-steps  same-structure")
    for rid in sorted(ids):
        clean = json.load(open(os.path.join(SANDBOX, "recipes_clean", "%s.json" % rid)))["recipe"]
        rawr = raw[rid]
        same = keyword_seq(rawr) == keyword_seq(clean)
        folder = os.path.join(STAGE1, rid)
        json.dump(rawr, open(os.path.join(folder, "recipe_raw.json"), "w"), indent=2, ensure_ascii=False)
        json.dump(clean, open(os.path.join(folder, "recipe_clean.json"), "w"), indent=2, ensure_ascii=False)
        print("  %-10s %7d   %9d      %s"
              % (rid, len(keyword_seq(rawr)), len(keyword_seq(clean)), "YES" if same else "NO"))

    print("\nwrote recipe_raw.json + recipe_clean.json into each stage1_test/<id>/")


if __name__ == "__main__":
    main()
