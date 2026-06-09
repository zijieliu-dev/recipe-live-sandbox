#!/usr/bin/env python3
"""
manifest.py - Phase 0 inventory.

Reads the cleaned recipes (recipes_clean/*.json) and extracts the *complete*
surface area the sandbox must cover to run all recipes faithfully (Level B):

  - control-flow keywords           (interpreter scope)
  - (provider, operation) pairs      (comps to generate)
  - formula method frequency         (formula-engine checklist, by priority)
  - formula standalone tokens        (today/now/field/index/input/skip/...)
  - _ref source-provider stats       (which providers are read as data sources)

Outputs:
  manifest.json          machine catalog + counts (also our one-time glance)
  manifest_schemas.json  (provider::operation) -> {input_schema, output_schema}
                         first-seen, for Phase 4 comp generation & fabrication

Usage:
  python3 manifest.py --indir test_sandbox/recipes_clean
"""
import argparse
import glob
import json
import os
import re
from collections import Counter, defaultdict


# --------------------------------------------------------------------------- #
# formula scanning                                                            #
# --------------------------------------------------------------------------- #
def find_formulas(s):
    """Return every #{...} fragment in string s (brace-balanced, string-aware)."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "#" and i + 1 < n and s[i + 1] == "{":
            depth = 0
            in_str = False
            esc = False
            quote = ""
            k = i + 1
            while k < n:
                c = s[k]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == quote:
                        in_str = False
                else:
                    if c == '"' or c == "'":
                        in_str = True
                        quote = c
                    elif c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            out.append(s[i:k + 1])
                            break
                k += 1
            i = k + 1
        else:
            i += 1
    return out


_STR = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')
_REF = re.compile(r"_ref\(.*?\)")
_METHOD = re.compile(r"\.([a-zA-Z_]\w*[?!]?)")
_WORD = re.compile(r"\b([a-z_][a-zA-Z0-9_]*[?!]?)\b")
_REF_SRC = re.compile(r'_ref\("([^"]*)"')


def analyze_formula(fragment, methods, tokens):
    """Count method calls and standalone tokens inside one #{...} fragment.

    Returns True if the fragment is a *pure* reference (just #{_ref(...)} with
    no surrounding logic), False otherwise.
    """
    inner = fragment[2:-1].strip()            # strip #{ and }
    is_pure = (_REF.sub("", inner).strip() == "")

    cleaned = _REF.sub(" ", inner)            # drop reference internals
    cleaned = _STR.sub(" ", cleaned)          # drop string literals
    for m in _METHOD.findall(cleaned):
        methods[m] += 1
    no_methods = _METHOD.sub(" ", cleaned)    # so receivers aren't double-counted
    for w in _WORD.findall(no_methods):
        tokens[w] += 1
    return is_pure


# --------------------------------------------------------------------------- #
# tree walk                                                                   #
# --------------------------------------------------------------------------- #
def walk_strings(node, cb):
    if isinstance(node, str):
        cb(node)
    elif isinstance(node, list):
        for x in node:
            walk_strings(x, cb)
    elif isinstance(node, dict):
        for v in node.values():
            walk_strings(v, cb)


def walk_steps(node, cb):
    """Call cb(step_dict) for every node that has a 'keyword' (a recipe step)."""
    if isinstance(node, dict):
        if "keyword" in node:
            cb(node)
        for v in node.values():
            walk_steps(v, cb)
    elif isinstance(node, list):
        for x in node:
            walk_steps(x, cb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default="test_sandbox/recipes_clean")
    ap.add_argument("--out", default="test_sandbox/manifest.json")
    ap.add_argument("--schemas", default="test_sandbox/manifest_schemas.json")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    keywords = Counter()
    providers = defaultdict(lambda: {"steps": 0, "ops": Counter()})
    methods = Counter()
    tokens = Counter()
    ref_by_src = Counter()
    schemas = {}

    state = {"recipes": 0, "steps": 0, "formulas": 0, "pure_ref": 0, "refs": 0}

    files = sorted(glob.glob(os.path.join(args.indir, "*.json")))
    if args.limit:
        files = files[:args.limit]

    for fp in files:
        with open(fp) as f:
            recipe = json.load(f).get("recipe")
        state["recipes"] += 1

        def on_step(step):
            state["steps"] += 1
            keywords[step.get("keyword")] += 1
            prov, op = step.get("provider"), step.get("name")
            if prov:
                providers[prov]["steps"] += 1
                if op:
                    providers[prov]["ops"][op] += 1
                    key = "%s::%s" % (prov, op)
                    if key not in schemas:
                        schemas[key] = {
                            "input_schema": step.get("extended_input_schema"),
                            "output_schema": step.get("extended_output_schema"),
                        }

        def on_str(s):
            c = s.count("_ref(")
            if c:
                state["refs"] += c
                for m in _REF_SRC.findall(s):
                    ref_by_src[m] += 1
            for frag in find_formulas(s):
                state["formulas"] += 1
                if analyze_formula(frag, methods, tokens):
                    state["pure_ref"] += 1

        walk_steps(recipe, on_step)
        walk_strings(recipe, on_str)

    manifest = {
        "recipes": state["recipes"],
        "total_steps": state["steps"],
        "n_providers": len(providers),
        "n_operations": sum(len(p["ops"]) for p in providers.values()),
        "keywords": dict(keywords.most_common()),
        "formula": {
            "n_formulas": state["formulas"],
            "n_pure_ref": state["pure_ref"],
            "n_with_logic": state["formulas"] - state["pure_ref"],
            "n_distinct_methods": len(methods),
            "methods": dict(methods.most_common()),
            "tokens": dict(tokens.most_common(60)),
        },
        "refs": {
            "total": state["refs"],
            "by_source_provider": dict(ref_by_src.most_common()),
        },
        "providers": {
            prov: {"steps": d["steps"], "operations": dict(d["ops"].most_common())}
            for prov, d in sorted(providers.items(), key=lambda kv: -kv[1]["steps"])
        },
    }

    with open(args.out, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    with open(args.schemas, "w") as f:
        json.dump(schemas, f, ensure_ascii=False)

    # --- one-time glance ---
    print("recipes=%d  steps=%d  providers=%d  operations=%d"
          % (state["recipes"], state["steps"], len(providers), manifest["n_operations"]))
    print("\nkeywords:", dict(keywords.most_common()))
    print("\nformulas: total=%d  pure_ref=%d  with_logic=%d  distinct_methods=%d"
          % (state["formulas"], state["pure_ref"],
             state["formulas"] - state["pure_ref"], len(methods)))
    print("\ntop 40 formula methods (the engine checklist):")
    for m, c in methods.most_common(40):
        print("  %6d  .%s" % (c, m))
    print("\ntop standalone tokens:")
    for t, c in tokens.most_common(20):
        print("  %6d  %s" % (c, t))
    print("\ntop 20 providers by steps:")
    for prov, d in list(manifest["providers"].items())[:20]:
        print("  %6d  %-34s (%d ops)" % (d["steps"], prov, len(d["operations"])))
    print("\nwrote %s and %s" % (args.out, args.schemas))


if __name__ == "__main__":
    main()
