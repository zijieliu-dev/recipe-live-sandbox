# benchmark_v1 — execution-equivalent recipe generation

A benchmark that scores whether a model can **generate a runnable recipe JSON
that produces the same sandbox behavior as a hidden original recipe** — not
whether it can copy the original. The evaluation unit is:

> generated recipe behavior == original recipe behavior, under the same fixture

Built on the deterministic mocked sandbox in `../engine` + `../comps`
(fixed clock, hash-seeded fabrication — every run is reproducible). Source
recipes are the 1,000-recipe `stage3_test/benchmark/main_1k` split
(489 live-write / 511 live-read; Slack/SF/Jira/Sheets).

## What a model sees / must produce

Per task (see `prompts/<task_id>.txt`): the natural-language task description,
runtime inputs, the action/control-flow schema catalog for the allowed
connectors, reference syntax, and an output-only-JSON instruction.
**The source recipe is never shown.** The model returns the minimal contract:

```json
{"recipe": {"keyword": "trigger", "provider": ..., "name": ..., "as": "t1",
            "input": {...}, "block": [ ...steps... ]}}
```

Metadata (numbers, uuids, toggleCfg, extended schemas, …) is filled by the
harness normalizer; semantic mistakes (wrong provider/op/field/ref/condition)
are **never** repaired.

## Pipeline

| Stage | Script | Output |
|-------|--------|--------|
| 1 catalog | `build_catalog.py` | `schemas/action_catalog.jsonl` (1,298 atomic op schemas from `../manifest_schemas.json`), `provider_catalog.jsonl`, `control_flow.json`, `recipe_minimal_schema.json` |
| 2 graph | `semantic_graph.py` (lib) | `graphs/<rid>.json` — executed-dataflow graph (refs, condition leaves, foreach sources); never trusts comments |
| 3 fixtures | `build_fixtures.py` | `fixtures/<rid>.json` — trigger event + recorded read/write world state + `BENCH_<rid>` markers + branch-satisfaction + scenario variants |
| 4 gold | `run_original.py` | `gold/groundtruth_effects.jsonl` (canonical effects/reads/state-diff per scenario), `gold/original_traces.jsonl`, `gold/excluded.jsonl` |
| 5 tasks | `gen_tasks.py`, `build_prompts.py` | `tasks/main_1k.jsonl`, `tasks/control_flow_stress.jsonl`, `prompts/` |

`build_all.py` runs 1→5 (`--limit N` for pilots, `--selfcheck` to validate).

## The one idea: fixture-backed dispatch

The engine normally fabricates connector outputs from each step's
`extended_output_schema` — which candidate recipes don't have. So the
benchmark sandbox (`sandbox.py`) serves every external read from a recorded
**fixture** keyed by `provider::operation[::object]`, with graceful fallbacks
(same provider+object via a different op → same data, so a *different but
equivalent* read strategy still works). Writes are logged as canonical
**effects** and answered with the recorded (or deterministic stub) write
output. Three schema-dependent primitives (`lookup_table`,
`workato_db_table`, `workato_smart_list` empty-state reads) are fixture-backed
the same way. Gold and candidate therefore see *exactly the same world*.

Fixture build also:
- injects a unique `BENCH_<rid>` marker into free-text fields that do **not**
  feed any branch condition (used by lenient matching);
- runs a branch-satisfaction loop: if-conditions with a pure-ref lhs into
  fixtured data are toggled TRUE so the positive path executes (re-recording
  reads that only become reachable once a branch opens);
- emits scenario variants: `positive` plus a verified `branch_<n>_false`
  negative override where a taken branch is statically flippable. A candidate
  passes the task only if it passes **all** scenarios (control-flow stress).

## Scoring

```
python3 score_predictions.py predictions.jsonl --name myrun
# predictions.jsonl rows: {"task_id": "main_1k_000123", "output": "<raw model text>"}
```

Per task: parse → normalize (metadata only) → validate (catalog + allowed
connectors + refs) → run every scenario on the fixture → canonicalize →
compare vs gold. Fail stages: `invalid_json | invalid_recipe_structure |
schema_error | run_error | effect_mismatch | pass`.

**Canonicalization** (`canonicalizers/`): per-app effect normal forms —
Slack (channel, extracted plain text, button titles/params, modal title),
Jira (project, issue type, summary, description, labels, priority), Sheets
(sheet, column order, row value matrix), Salesforce (sobject, semantic field
map). Volatile data (ts/uuid/run ids) is dropped; op-name variants collapse
into families (`post_bot_message`/`post_message_to_channel` →
`slack.post_message`), so block order, aliases, UUIDs and equivalent
formulations never matter — only behavior.

**Verdicts**
- `strict_pass` (leaderboard): status matches ∧ canonical effects match 1:1 ∧
  **no extra writes** ∧ state-diff matches; read-only tasks additionally need
  the expected reads signature covered and zero writes.
- `lenient_pass` (debugging): per-effect family+target match with the
  required tokens (markers/targets) present, no extra writes.

**Metrics** (`results/<name>.metrics.json`): headline
`pass@1_execution_equivalent_strict` plus valid_json / valid_recipe_schema /
run-success / effect-match / extra- & missing-write rates, fail-stage counts,
and breakdowns by tier (live_read/live_write), primary app, read/write,
linear vs control-flow, foreach, if/else, single vs multi app, and per-scenario
pass rate.

## Harness validation

`selfcheck.py` strips each original recipe down to the minimal model-output
contract and scores it against its own ground truth — strict pass must be
~100%, otherwise the harness (not the model) is dropping tasks.

## Repair track

This is **pass@1 without repair** by design. A "with validator feedback"
track can be layered on by re-prompting with the `schema_error` detail and
re-calling `evaluate_one` — keep it as a separate reported number.

## partials_split

The stage3 `partials_split` (321 platform-limited / mock-blank recipes) is
**not scored** here; if needed, build fixtures for it with
`build_fixtures.py --ids stage3_test/benchmark/partials_split_ids.txt` and
evaluate plausibility/fail-safety only.

## Known limitations / next steps

- Task descriptions are deterministic templates from the semantic graph —
  faithful but mechanical. An optional LLM polish pass over
  `tasks/main_1k.jsonl[].description` would improve readability (keep the
  behavior contract section intact).
- One negative scenario max per task; "multiple matching items" fixtures and
  deeper branch matrices are future work.
- Foreach keeps the engine's semantics (empty/unresolvable source falls back
  to 2 stub iterations, capped at 3) — identical for gold and candidate, so
  comparison stays fair.
- Reads are scored only for read-only tasks (coverage), matching the design's
  "reads are diagnostic" rule.
