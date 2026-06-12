# Pilot review package — `opus_pilot` (Claude Opus 4.8, 10 tasks, sandbox track)

Everything from the first end-to-end test of benchmark_v1, packaged for review.
Run date: 2026-06-12. Model: `claude-opus-4-8` (adaptive thinking, single-shot,
no repair). Tasks: `main_1k_000000` … `main_1k_000009` (the first 10 of the
1,000-task `main_1k` split — all happen to be `live_read` tier).

## Headline scores

| Metric | Value | Meaning |
|---|---|---|
| `pass@1_execution_equivalent_strict` | **0.7** (7/10) | run status matches AND canonical effects match gold 1:1 AND no extra writes AND state-diff matches; read-only tasks additionally need the gold read signature covered and zero writes. **This is the leaderboard number.** |
| `pass@1_execution_equivalent_lenient` | 0.9 (9/10) | per-effect family+target match with required tokens present, no extra writes. Debugging metric — "right operation to the right place, payload may differ". |
| `valid_json_rate` | 1.0 | every output parsed as JSON |
| `valid_recipe_schema_rate` | 1.0 | every recipe passed normalization + validation (no unknown providers/ops) |
| `sandbox_run_success_rate` | 1.0 | every recipe executed without a run error |
| `effect_match_rate` | 0.8 | scenarios where canonical effects matched exactly |
| `extra_write_rate` | 0.2 / `missing_write_rate` 0.2 | the strict failures are payload near-misses, not crashes |
| `scenario_strict_pass_rate` | 0.636 (7/11) | per-scenario rate (task 000006 has 2 scenarios) |

Baseline for comparison: `haiku_pilot` (claude-haiku, same 10 tasks) scored
0.2 strict / 0.5 lenient. Harness sanity check: `selfcheck` (original recipes
stripped to the minimal contract and scored against their own gold) is
1000/1000 strict — so a failure here is a model failure, not a harness failure.

Full metrics: `metrics.json`. One-line verdict per task: `case_index.json`.

## What's in `cases/<task_id>/`

| File | What it is |
|---|---|
| `0_task_meta.json` | task row from `tasks/main_1k.jsonl`: description, allowed connectors, allowed action ids, tier, features, scenario list |
| `1_prompt_model_input.txt` | the EXACT text sent to the model (description + runtime inputs + schema catalog + recipe grammar + output instruction). The source recipe is never in here. |
| `2_model_output_raw.txt` | the raw model response, byte-for-byte as scored |
| `2_model_output_pretty.json` | same, pretty-printed (present only if it parsed) |
| `3_groundtruth_gold.json` | the gold: canonical effects, reads, status and state-diff per scenario, produced by running the ORIGINAL hidden recipe through the same sandbox + canonicalizer |
| `4_verdict.json` | the full scoring result: per-scenario strict/lenient, and the exact `missing_effects_strict` / `extra_writes_strict` / `missing_reads` diffs |

## Verdict summary (details in CASE_ANALYSIS.md)

| Task | App | Verdict | One-liner |
|---|---|---|---|
| 000000 | Slack | **pass** | dynamic-menu read, reads covered, zero writes |
| 000001 | Slack | **pass** | dynamic-menu + try/catch, reads covered |
| 000002 | Sheets | **pass** | recipe-function → sheets search, reads covered |
| 000003 | SF | **FAIL** strict (lenient pass) | `send_reply` payload wrong: 1 of 3 fields, value from a record LIST instead of the matched record |
| 000004 | Slack | **pass** | app-home-opened → open bot app home |
| 000005 | Slack | **pass** | dynamic-menu (currencies) |
| 000006 | Slack | **FAIL** strict+lenient | read-only task; skipped 2 required reads (`invoke_custom_ruby_code`, `generate_menu_options`) in BOTH scenarios — behaviorally not equivalent |
| 000007 | Slack | **pass** | dynamic-menu (office locations, parameterized) |
| 000008 | Slack | **pass** | dynamic-menu (timezones) |
| 000009 | Slack→Snowflake | **FAIL** strict (lenient pass) | snowflake sync: param named `source` instead of `rows`; `true`/`1` as bool/int instead of strings |

## How to reproduce / scale up

```bash
# generate (resumable; --offset/--limit to pick a slice)
/tmp/nlenv/bin/python gen_predictions.py --limit 10 --name opus_pilot

# score
python3 score_predictions.py results/opus_pilot.predictions.jsonl --name opus_pilot
```

## Things to judge (open design questions)

1. **Strictness of payload equality (cases 000003, 000009).** Strict compares
   the full semantic input map after canonicalization. 000009 fails on
   `"true"` (string) vs `true` (bool) and a parameter-name variant
   (`rows` vs `source`) for the same connector op. Is that the behavior you
   want, or should the canonicalizer normalize boolean-ish strings and known
   parameter aliases per app (the way it already collapses op-name variants)?
   Counter-argument: a real connector may genuinely treat them differently,
   and selfcheck proves the original formulation passes.
2. **Read-signature requirement on read-only tasks (case 000006).** The task
   fails because the model skipped internal steps (`custom ruby code`,
   `generate_menu_options`) whose effects are invisible. The description says
   "must complete with the same reads" — but is requiring internal read
   coverage testing behavior equivalence or testing implementation copying?
3. **Sample bias.** Tasks 0–9 are all `live_read`; `write_task_pass_rate` is
   null in this pilot. A pilot with stratified sampling (write tasks, foreach,
   multi-app) would be more informative — use `--offset` or sample by tier.
4. **Description leakage of internals (case 000003/000006).** Descriptions
   mention step-level details ("using data from step 3"). That's faithful to
   the template generator, but if the NL-polish pass (`polish_descriptions.py`)
   replaces them, scores may drop — worth re-running the pilot on
   `description_natural` once merged.
5. **Single-shot, no repair.** schema_error feedback re-prompting is
   deliberately excluded (pass@1). Fine for the headline; a "with validator
   feedback" track can be added later as a separate number.

## Pipeline

See `PIPELINE.md` for the full input→output→verdict walkthrough, and
`CASE_ANALYSIS.md` for the per-case evidence.
