"""common.py - paths, IO helpers, and recipe access shared by every stage."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.dirname(HERE)                      # .../test_sandbox
ROOT = os.path.dirname(SANDBOX)                      # importable parent

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RECIPES_DIR = os.path.join(SANDBOX, "recipes_clean")
MANIFEST_SCHEMAS = os.path.join(SANDBOX, "manifest_schemas.json")
STAGE3_BENCH = os.path.join(SANDBOX, "stage3_test", "benchmark")

# output layout (mirrors the design doc's benchmark/ tree)
SCHEMAS_DIR = os.path.join(HERE, "schemas")
TASKS_DIR = os.path.join(HERE, "tasks")
GOLD_DIR = os.path.join(HERE, "gold")
FIXTURES_DIR = os.path.join(HERE, "fixtures")
GRAPHS_DIR = os.path.join(HERE, "graphs")
PROMPTS_DIR = os.path.join(HERE, "prompts")
RESULTS_DIR = os.path.join(HERE, "results")

ACTION_CATALOG = os.path.join(SCHEMAS_DIR, "action_catalog.jsonl")
PROVIDER_CATALOG = os.path.join(SCHEMAS_DIR, "provider_catalog.jsonl")
MAIN_TASKS = os.path.join(TASKS_DIR, "main_1k.jsonl")
STRESS_TASKS = os.path.join(TASKS_DIR, "control_flow_stress.jsonl")
GT_EFFECTS = os.path.join(GOLD_DIR, "groundtruth_effects.jsonl")
GT_TRACES = os.path.join(GOLD_DIR, "original_traces.jsonl")
GT_EXCLUDED = os.path.join(GOLD_DIR, "excluded.jsonl")

DEFAULT_NOW = "2026-06-01T00:00:00+00:00"


def ensure_dirs():
    for d in (SCHEMAS_DIR, TASKS_DIR, GOLD_DIR, FIXTURES_DIR, GRAPHS_DIR,
              PROMPTS_DIR, RESULTS_DIR):
        os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# IO                                                                          #
# --------------------------------------------------------------------------- #
def load_recipe_doc(recipe_id):
    path = os.path.join(RECIPES_DIR, "%s.json" % recipe_id)
    with open(path) as f:
        return json.load(f)


def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def main_1k_entries():
    """The stage3 main_1k split: [{id, tier, primary_app, apps, ...}]."""
    return read_jsonl(os.path.join(STAGE3_BENCH, "main_1k.jsonl"))


def task_id_for(recipe_id, seq):
    return "main_1k_%06d" % seq


def stable_hash(s, n=8):
    return hashlib.md5(str(s).encode("utf-8")).hexdigest()[:n]


def bench_marker(recipe_id):
    return "BENCH_%s" % recipe_id


# --------------------------------------------------------------------------- #
# recipe tree helpers (thin wrappers over engine.loader)                      #
# --------------------------------------------------------------------------- #
def iter_steps(recipe):
    from test_sandbox.engine import loader
    return loader.iter_steps(recipe)


def get_trigger(recipe):
    from test_sandbox.engine import loader
    return loader.get_trigger(recipe)


def recipe_features(recipe):
    """Static control-flow features of a recipe (used for metric breakdowns)."""
    kws = set()
    n_actions = 0
    for s in iter_steps(recipe):
        kws.add(s.get("keyword"))
        if s.get("keyword") == "action":
            n_actions += 1
    return {
        "has_if": bool(kws & {"if", "elsif", "else"}),
        "has_foreach": "foreach" in kws,
        "has_repeat": "repeat" in kws,
        "has_try": "try" in kws,
        "has_stop": "stop" in kws,
        "n_actions": n_actions,
        "is_linear": not (kws & {"if", "elsif", "else", "foreach", "repeat"}),
    }
