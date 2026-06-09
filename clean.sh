#!/usr/bin/env bash
# clean.sh - run the deterministic recipe normalization over the full CSV.
#
# Peels escaping (concern 4) and unifies the two datapill dialects (concern 1)
# into a single canonical _ref(...) form. Does NOT evaluate formulas.
#
# Usage:
#   ./clean.sh                       # defaults: ../standalone_recipes.csv -> ./recipes_clean
#   ./clean.sh /path/in.csv /path/outdir /path/report.json
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INPUT="${1:-$HERE/../standalone_recipes.csv}"
OUTDIR="${2:-$HERE/recipes_clean}"
REPORT="${3:-$HERE/clean_report.json}"

echo "Input : $INPUT"
echo "Outdir: $OUTDIR"
echo "Report: $REPORT"
echo

mkdir -p "$OUTDIR"
python3 "$HERE/clean.py" --input "$INPUT" --outdir "$OUTDIR" --report "$REPORT"

echo
echo "Done. $(find "$OUTDIR" -name '*.json' | wc -l | tr -d ' ') cleaned recipe files in $OUTDIR"
