#!/usr/bin/env python3
"""
selfcheck.py - harness validation: the ORIGINAL recipe, stripped down to the
minimal model-output contract (no uuids, numbers, schemas, toggleCfg, ...),
must pass its own ground truth. Anything below ~100%% strict means the
normalizer/sandbox/comparator pipeline - not the model - drops tasks.

Writes results/selfcheck.predictions.jsonl, then scores it like a model run.

Usage:  python3 selfcheck.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common  # noqa: E402

# Everything the minimal output contract keeps; the rest the harness must fill.
_KEEP = ("keyword", "provider", "name", "as", "input", "block")


def minimalize(step):
    out = {}
    for k in _KEEP:
        if k not in step:
            continue
        if k == "block":
            out[k] = [minimalize(c) for c in (step[k] or [])
                      if isinstance(c, dict) and c.get("keyword")]
        else:
            out[k] = step[k]
    return out


def main():
    common.ensure_dirs()
    tasks = common.read_jsonl(common.MAIN_TASKS)
    preds = []
    for t in tasks:
        doc = common.load_recipe_doc(t["source_recipe_id"])
        minimal = {"recipe": minimalize(doc["recipe"])}
        preds.append({"task_id": t["task_id"],
                      "output": json.dumps(minimal, ensure_ascii=False)})
    path = os.path.join(common.RESULTS_DIR, "selfcheck.predictions.jsonl")
    common.write_jsonl(path, preds)
    print("wrote %d self-predictions -> %s" % (len(preds), path))

    from test_sandbox.benchmark_v1 import score_predictions
    sys.argv = ["score_predictions.py", path, "--name", "selfcheck"]
    score_predictions.main()


if __name__ == "__main__":
    main()
