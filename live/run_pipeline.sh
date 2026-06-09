#!/usr/bin/env bash
# run_pipeline.sh - end-to-end stage-1 live Salesforce pipeline.
#
# Runs from ~/Desktop. Salesforce auth uses the `sf` CLI (org: my-dev-org).
# Each stage is idempotent; re-running refreshes the stage1_test/ folders.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."          # -> ~/Desktop

echo "===================================================================="
echo " STAGE-1 LIVE SALESFORCE PIPELINE"
echo "===================================================================="

# --- one-time upstream (skipped if already present) ----------------------
if [ ! -d test_sandbox/recipes_clean ]; then
  echo "[0] clean: CSV -> recipes_clean/ (normalize datapills, peel escaping)"
  ./test_sandbox/clean.sh
  echo "[1] manifest: inventory connectors/operations/formulas"
  python3 test_sandbox/manifest.py
else
  echo "[0-1] recipes_clean/ + manifest already present (skip clean/manifest)"
fi

# selected.json (the 10 recipes) is produced by the selection step; assumed present.
echo "[2] selection: $(python3 -c "import json;print(len(json.load(open('test_sandbox/live/selected.json'))))") recipes in selected.json"

# --- verify live Salesforce connectivity ---------------------------------
echo "[3] auth check (sf CLI -> my-dev-org)"
python3 test_sandbox/sf_check.py | head -1

# --- materialize the stage-1 folders -------------------------------------
echo "[4] save raw + cleaned recipe JSON into each folder"
python3 test_sandbox/live/save_recipes.py | tail -1

echo "[5] generate recipe.md specs"
python3 test_sandbox/live/gen_stage1.py | tail -1

# --- run live: per recipe x sample -> seed/realize -> run -> teardown -----
echo "[6] run live (writes test_samples.md + results.md per recipe)"
python3 test_sandbox/live/run_stage1.py

echo
echo "Done. Inspect stage1_test/<id>/ : recipe.md, recipe_raw.json,"
echo "recipe_clean.json, test_samples.md, results.md  (see stage1_test/README.md)"
