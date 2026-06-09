#!/usr/bin/env python3
"""
clean.py - deterministic normalization pass for Workato standalone recipes.

Fixes two purely-syntactic things before the sandbox engine ever runs, so the
engine only has to understand ONE reference format:

  Concern 1 (dialects):  recipes reference a prior step's output with TWO
                         different syntaxes for the same thing.
  Concern 4 (escaping):  datapills are buried under CSV + JSON quote escaping.

This pass does NOT evaluate formulas. A datapill embedded inside a formula keeps
its surrounding transformation untouched (e.g. `.split("/")[0].to_country_alpha2`);
only the *reference syntax* is normalized.

Dialects handled
----------------
  A (~98% of recipes):  _dp('{"pill_type":..,"provider":..,"line":..,"path":[..]}')
  B (~5%):              _('data.<provider>.<line>.<seg>.<seg>')

Both become a single canonical token:
  _ref("<provider>","<line>",[<path segments>])

Escaping is peeled for free: csv.DictReader removes the CSV quote-doubling and
json.loads(code_sanitized) removes the JSON backslash escaping, so by the time we
touch a leaf string the datapill is already in its clean Layer-C form.

Output
------
One JSON file per recipe in --outdir:
  { <meta cols>, "recipe": <normalized tree>, "_clean": <per-recipe ref counts> }
plus an aggregate --report JSON.

Usage
-----
  python3 clean.py --input standalone_recipes.csv --outdir test_sandbox/recipes_clean
  python3 clean.py --limit 30 --outdir /tmp/clean_test     # quick validation
"""
import argparse
import csv
import json
import os
import sys

csv.field_size_limit(sys.maxsize)


# --------------------------------------------------------------------------- #
# datapill normalization                                                      #
# --------------------------------------------------------------------------- #
def _scan_braced_json(s, start):
    """`start` points at a '{'. Return the index just past the matching '}'.

    Brace-counts while respecting double-quoted JSON strings and backslash
    escapes, so braces appearing inside string *values* don't fool it.
    """
    depth = 0
    in_str = False
    esc = False
    k = start
    n = len(s)
    while k < n:
        c = s[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return k + 1
        k += 1
    raise ValueError("unbalanced datapill JSON")


def _render_ref(provider, line, path):
    """Canonical, easily re-parsable reference token."""
    return "_ref(%s,%s,%s)" % (
        json.dumps(provider, ensure_ascii=False),
        json.dumps(line, ensure_ascii=False),
        json.dumps(path, ensure_ascii=False),
    )


def canonicalize(s, stats):
    """Rewrite every datapill reference inside leaf string `s` to _ref(...).

    Surrounding formula text is preserved verbatim.
    """
    # cheap bail-out: the vast majority of leaf strings have no datapill
    if "_dp(" not in s and "_('data." not in s:
        return s

    out = []
    i = 0
    n = len(s)
    while i < n:
        # dialect A: _dp('{...}')
        if s.startswith("_dp(", i):
            try:
                br = s.index("{", i)
                end = _scan_braced_json(s, br)
                obj = json.loads(s[br:end])
                j = end
                if j < n and s[j] == "'":
                    j += 1
                if j < n and s[j] == ")":
                    j += 1
                out.append(_render_ref(obj.get("provider"), obj.get("line"), obj.get("path", [])))
                stats["dp"] += 1
                i = j
                continue
            except Exception:
                stats["dp_fail"] += 1
                out.append(s[i])
                i += 1
                continue

        # dialect B: _('data.<provider>.<line>.<seg>...')
        if s.startswith("_('data.", i):
            close = s.find("')", i)
            if close != -1:
                content = s[i + 3:close]          # skip the `_('` prefix -> data.provider.line.seg...
                parts = content.split(".")
                if len(parts) >= 3 and parts[0] == "data":
                    provider, line, path = parts[1], parts[2], parts[3:]
                    out.append(_render_ref(provider, line, path))
                    stats["data"] += 1
                    i = close + 2
                    continue
            stats["data_fail"] += 1
            out.append(s[i])
            i += 1
            continue

        out.append(s[i])
        i += 1
    return "".join(out)


def walk(node, stats):
    """Recurse the recipe tree, canonicalizing every leaf string."""
    if isinstance(node, str):
        return canonicalize(node, stats)
    if isinstance(node, list):
        return [walk(x, stats) for x in node]
    if isinstance(node, dict):
        return {k: walk(v, stats) for k, v in node.items()}
    return node


# --------------------------------------------------------------------------- #
# driver                                                                      #
# --------------------------------------------------------------------------- #
META_COLS = [
    "id", "flow_id", "version_no", "created_at", "updated_at",
    "author_id", "has_comment", "category",
]


def main():
    ap = argparse.ArgumentParser(description="Normalize Workato recipe datapills.")
    ap.add_argument("--input", default="standalone_recipes.csv")
    ap.add_argument("--outdir", default="test_sandbox/recipes_clean")
    ap.add_argument("--report", default="test_sandbox/clean_report.json")
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most N recipes (0 = all)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    report_dir = os.path.dirname(args.report)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    totals = {
        "recipes": 0, "parse_errors": 0,
        "dp": 0, "dp_fail": 0, "data": 0, "data_fail": 0,
    }

    with open(args.input, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if args.limit and totals["recipes"] >= args.limit:
                break
            rid = row["id"]
            try:
                tree = json.loads(row["code_sanitized"])   # peels escaping layers A & B
            except Exception:
                totals["parse_errors"] += 1
                continue

            stats = {"dp": 0, "dp_fail": 0, "data": 0, "data_fail": 0}
            clean_tree = walk(tree, stats)

            doc = {c: row.get(c) for c in META_COLS}
            doc["recipe"] = clean_tree
            doc["_clean"] = stats

            with open(os.path.join(args.outdir, "%s.json" % rid), "w") as out:
                json.dump(doc, out, ensure_ascii=False)

            totals["recipes"] += 1
            for k in ("dp", "dp_fail", "data", "data_fail"):
                totals[k] += stats[k]

    with open(args.report, "w") as f:
        json.dump(totals, f, indent=2)
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
