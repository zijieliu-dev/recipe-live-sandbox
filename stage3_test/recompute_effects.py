#!/usr/bin/env python3
"""Recompute live_effects for every recorded groundtruth file from its saved raw
output.side_effects, using the (now corrected) live_runner.live_effects. Rewrites
each groundtruth/<id>.json's "live_effects" and rebuilds index.jsonl to match.

No recipes are re-run: the raw side-effects are already on disk, so this only
re-derives the WRITE/read classification. Safe to re-run (idempotent)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from test_sandbox.live import runner as live_runner  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GT_DIR = os.path.join(HERE, "groundtruth")
INDEX = os.path.join(GT_DIR, "index.jsonl")


def recompute_one(d):
    se = (d.get("output") or {}).get("side_effects") or []
    return live_runner.live_effects(se)


def main():
    # 1. rewrite per-recipe files; build id -> new live_effects map
    new_le = {}
    changed = 0
    for fn in os.listdir(GT_DIR):
        if not fn.endswith(".json") or fn == "index.jsonl":
            continue
        p = os.path.join(GT_DIR, fn)
        d = json.load(open(p))
        if "id" not in d:                      # e.g. summary.json, not a recipe
            continue
        le = recompute_one(d)
        new_le[str(d["id"])] = le
        if d.get("live_effects") != le:
            d["live_effects"] = le
            json.dump(d, open(p, "w"))
            changed += 1
    print("per-recipe files updated:", changed)

    # 2. rebuild index.jsonl (only the live_effects field per line)
    lines = []
    idx_changed = 0
    for line in open(INDEX):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        rid = str(d.get("id"))
        if rid in new_le and d.get("live_effects") != new_le[rid]:
            d["live_effects"] = new_le[rid]
            idx_changed += 1
        lines.append(json.dumps(d))
    with open(INDEX, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("index.jsonl lines updated:", idx_changed)


if __name__ == "__main__":
    main()
