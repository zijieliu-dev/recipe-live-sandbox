"""benchmark_v1 - execution-equivalence recipe-generation benchmark.

Pipeline (all stages reuse the deterministic mocked sandbox in ../engine):

  Stage 1  build_catalog.py    action/control-flow schema catalog (the model's manual)
  Stage 2  semantic_graph.py   recipe -> semantic execution graph (lib, no CLI)
  Stage 3  build_fixtures.py   per-recipe initial-state fixture + branch scenarios
  Stage 4  run_original.py     gold run -> canonical effects / reads / control trace
  Stage 5  gen_tasks.py        task descriptions + tasks/main_1k.jsonl + prompts

  Scoring  normalize_recipe.py + run_candidate.py + compare_effects.py
           + score_predictions.py  (strict & lenient execution-equivalence)

  build_all.py orchestrates stages 1-5; selfcheck.py validates the harness by
  scoring the original recipes against their own ground truth.
"""
