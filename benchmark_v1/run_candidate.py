"""run_candidate.py - evaluate ONE candidate recipe against one task.

Pipeline (mirrors the design doc's evaluator):
  raw model output -> json parse -> RecipeNormalizer (metadata-only fixes)
  -> semantic validation (catalog + allowed connectors)
  -> run on EVERY fixture scenario of the task -> canonicalize
  -> compare_effects vs gold -> per-scenario + aggregate verdict

Fail stages are reported distinctly so the diagnostics metrics can tell WHY
models fail: invalid_json | invalid_recipe_structure | schema_error |
run_error | effect_mismatch | pass.
"""
import json
import os

from test_sandbox.benchmark_v1 import common, sandbox, canonicalizers
from test_sandbox.benchmark_v1.compare_effects import (compare_scenario,
                                                       aggregate_scenarios)
from test_sandbox.benchmark_v1.normalize_recipe import (RecipeNormalizer,
                                                        RecipeNormalizationError)


def _fail(task_id, stage, detail):
    return {"task_id": task_id, "pass": False, "strict_pass": False,
            "lenient_pass": False, "fail_stage": stage,
            "detail": str(detail)[:500],
            "valid_json": stage != "invalid_json",
            "valid_recipe": stage not in ("invalid_json", "invalid_recipe_structure",
                                          "schema_error"),
            "ran": False}


def load_fixture(recipe_id):
    with open(os.path.join(common.FIXTURES_DIR, "%s.json" % recipe_id)) as f:
        return json.load(f)


def strip_json_fences(s):
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def evaluate_one(task, gold, candidate_output, normalizer=None):
    """task: tasks/main_1k.jsonl row. gold: groundtruth row. candidate_output:
    raw string (or dict) the model produced. Returns the result row."""
    task_id = task["task_id"]
    normalizer = normalizer or RecipeNormalizer()

    # 1. parse
    if isinstance(candidate_output, (dict, list)):
        raw = candidate_output
    else:
        try:
            raw = json.loads(strip_json_fences(str(candidate_output)))
        except json.JSONDecodeError as e:
            return _fail(task_id, "invalid_json", e)

    # 2. normalize harmless metadata
    try:
        doc = normalizer.normalize(raw)
    except RecipeNormalizationError as e:
        return _fail(task_id, "invalid_recipe_structure", e)
    recipe = doc["recipe"]

    # 3. semantic validation (hard errors fail; warnings are diagnostic only)
    errors, warnings = normalizer.validate(recipe, task.get("allowed_connectors"))
    if errors:
        out = _fail(task_id, "schema_error", "; ".join(errors[:10]))
        out["validation_warnings"] = warnings[:10]
        return out

    # 4-7. run every scenario against the SAME fixture the gold used
    fixture = load_fixture(task["source_recipe_id"])
    scen_by_id = {s["scenario_id"]: s for s in fixture.get("scenarios") or []}
    per_scenario = []
    for gscen in gold["scenarios"]:
        overrides = (scen_by_id.get(gscen["scenario_id"]) or {}).get("overrides") or []
        try:
            record, _ = sandbox.run_on_fixture(recipe, fixture, overrides=overrides)
        except Exception as e:
            return _fail(task_id, "run_error", repr(e))
        observed = canonicalizers.canonicalize_run(record)
        verdict = compare_scenario(gscen, observed)
        verdict["scenario_id"] = gscen["scenario_id"]
        per_scenario.append(verdict)

    agg = aggregate_scenarios(per_scenario)
    return {
        "task_id": task_id,
        "pass": agg["strict_pass"],
        "strict_pass": agg["strict_pass"],
        "lenient_pass": agg["lenient_pass"],
        "fail_stage": "pass" if agg["strict_pass"] else "effect_mismatch",
        "valid_json": True, "valid_recipe": True, "ran": True,
        "status_match": agg["status_match"],
        "effect_match": agg["effect_match"],
        "extra_write_count": agg["extra_write_count"],
        "missing_effect_count": agg["missing_effect_count"],
        "n_scenarios": agg["n_scenarios"],
        "n_scenarios_passed_strict": agg["n_scenarios_passed_strict"],
        "validation_warnings": warnings[:10],
        "scenarios": per_scenario,
    }
