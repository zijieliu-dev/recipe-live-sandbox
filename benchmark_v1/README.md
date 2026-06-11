# benchmark_v1 — execution-equivalent recipe generation

Scores whether a model can **generate a runnable recipe JSON that reproduces
the behavior of a hidden original recipe** — not whether it can copy it. The
evaluation unit is always:

> generated recipe behavior == original recipe behavior, under the same fixture

Two tracks, reported separately:

| Track | Metric | What it proves |
|-------|--------|----------------|
| **sandbox** (this dir) | `pass@1_execution_equivalent_strict` | the candidate emits write *calls* equivalent to the original's, in the deterministic mocked sandbox — large-scale, cheap, reproducible; 1,000 tasks |
| **live** (`live/`) | `pass@1_live_write_verified_strict` | the candidate produces equivalent **real external state** in Slack / Jira / Google Sheets / Salesforce, verified by real API **read-back** — a connector's `ok:true` is only an ack, never the truth |

Source recipes: the 1,000-recipe `../stage3_test/benchmark/main_1k` split
(489 live-write / 511 live-read; Slack/SF/Jira/Sheets). Both tracks run on the
deterministic engine in `../engine` + `../comps` (fixed clock, hash-seeded
fabrication).

## Quick start

```bash
# build the benchmark (stages 1-5) + validate the harness
python3 build_all.py --selfcheck            # --limit 20 for a pilot

# score a model run (sandbox track)
python3 score_predictions.py predictions.jsonl --name myrun
#   predictions.jsonl rows: {"task_id": "main_1k_000123", "output": "<raw model text>"}

# live track (write tasks only; needs ../.env credentials)
cd live
python3 run_original_live.py --write-apps Sheets Jira Slack SF --limit 50   # live gold
python3 run_candidate_live.py ../results/predictions.jsonl --name myrun     # real writes
python3 score_predictions_live.py --name myrun                              # verdicts
python3 selfcheck_live.py                                                   # harness check
python3 cleanup_live.py                                                     # sweep leftovers
```

## Directory layout

```
benchmark_v1/
  build_all.py            stages 1-5 orchestrator
  build_catalog.py        S1: action/control-flow schema catalog
  semantic_graph.py       S2: recipe -> executed-dataflow graph (lib)
  build_fixtures.py       S3: fixtures + branch scenarios + BENCH markers
  run_original.py         S4: sandbox gold (canonical effects per scenario)
  gen_tasks.py            S5: tasks + NL descriptions
  build_prompts.py        model-facing prompts
  sandbox.py              fixture-backed dispatch + trace recorder
  normalize_recipe.py     RecipeNormalizer (metadata-only fixes + validation)
  canonicalizers/         per-app effect normal forms (slack/jira/sheets/sf)
  compare_effects.py      strict/lenient effect-set comparison
  run_candidate.py        per-task evaluator
  score_predictions.py    sandbox scorer + metrics
  selfcheck.py            sandbox harness validation

  schemas/  tasks/  gold/         committed dataset
  fixtures/ graphs/ prompts/ results/   regenerable (gitignored)

  live/                   the live-write track
    config.py live_env.json      env, clients, bench targets
    namespace.py                 per-run namespaces + target materialization + cleanup
    rebind.py                    update-target fixture patching (templates)
    dispatch.py                  LiveWriteDispatch: the write gateway
    readback.py                  real-API read-back verifiers
    canonical_live.py            live id normalization
    runner_lib.py                shared per-task live runner
    run_original_live.py         S7: live gold        run_candidate_live.py  S8
    score_predictions_live.py    S9: live verdicts    cleanup_live.py        S10
    selfcheck_live.py            live harness validation
    materialized/                per-run namespace records (gitignored)
```

## What a model sees / must produce

Per task (`prompts/<task_id>.txt`): the natural-language task description,
runtime inputs, the action/control-flow schema catalog for the allowed
connectors (atomic schemas only — never recipe fragments, so the benchmark
tests generation, not retrieval), reference syntax, and an output-only-JSON
instruction. **The source recipe is never shown.** The model returns the
minimal contract:

```json
{"recipe": {"keyword": "trigger", "provider": ..., "name": ..., "as": "t1",
            "input": {...}, "block": [ ...steps... ]}}
```

The harness normalizer fills metadata (numbers, uuids, toggleCfg, extended
schemas, …); semantic mistakes (wrong provider/op/field/ref/condition) are
**never** repaired. Hard validation errors (unknown provider/operation,
disallowed connector) fail the candidate; structural smells the engine
tolerates and the original corpus itself contains (dangling refs, vestigial
steps) are reported as warnings and left to execution equivalence to judge.

## Build pipeline (stages 1-5)

| Stage | Script | Output |
|-------|--------|--------|
| 1 catalog | `build_catalog.py` | `schemas/action_catalog.jsonl` (1,298 atomic op schemas from `../manifest_schemas.json`), `provider_catalog.jsonl`, `control_flow.json`, `recipe_minimal_schema.json` |
| 2 graph | `semantic_graph.py` (lib) | `graphs/<rid>.json` — executed-dataflow graph (refs, condition leaves, foreach sources); never trusts comments |
| 3 fixtures | `build_fixtures.py` | `fixtures/<rid>.json` — trigger event + recorded read/write world state + `BENCH_<rid>` markers + branch satisfaction + scenario variants |
| 4 gold | `run_original.py` | `gold/groundtruth_effects.jsonl` (canonical effects/reads/state-diff per scenario), `original_traces.jsonl`, `excluded.jsonl` |
| 5 tasks | `gen_tasks.py`, `build_prompts.py` | `tasks/main_1k.jsonl`, `tasks/control_flow_stress.jsonl` (204 multi-scenario tasks), `prompts/` |

### The core idea: fixture-backed dispatch

The engine normally fabricates connector outputs from each step's
`extended_output_schema` — which candidate recipes don't have. So the
benchmark sandbox (`sandbox.py`) serves every external read from a recorded
**fixture** keyed by `provider::operation[::object]`, with graceful fallbacks
(same provider+object via a different op → same data, so a *different but
equivalent* read strategy still works). Writes are logged as canonical
**effects** and answered with recorded (or deterministic stub) outputs. Three
schema-dependent primitives (`lookup_table`, `workato_db_table`,
`workato_smart_list` empty-state reads) are fixture-backed the same way.
Gold and candidate therefore see *exactly the same world*.

Fixture build also:
- injects a unique `BENCH_<rid>` marker into free-text fields that do **not**
  feed any branch condition (used by lenient matching);
- runs a branch-satisfaction loop: if-conditions with a pure-ref lhs into
  fixtured data are toggled TRUE so the positive path executes (re-recording
  reads that only become reachable once a branch opens);
- emits scenario variants: `positive` plus a verified `branch_<n>_false`
  negative override where a taken branch is statically flippable. A candidate
  passes a task only if it passes **all** scenarios (control-flow stress).

## Sandbox scoring

Per task: parse → normalize (metadata only) → validate → run every scenario on
the fixture → canonicalize → compare vs gold. Fail stages:
`invalid_json | invalid_recipe_structure | schema_error | run_error |
effect_mismatch | pass`.

**Canonicalization** (`canonicalizers/`): per-app effect normal forms — Slack
(channel, extracted plain text, button titles/params, modal title), Jira
(project, issue type, summary, description, labels, priority), Sheets (sheet,
column order, row value matrix), Salesforce (sobject, semantic field map).
Volatile data (ts/uuid/run ids) is dropped; op-name variants collapse into
families (`post_bot_message`/`post_message_to_channel` →
`slack.post_message`). Block order, aliases, UUIDs and equivalent
formulations never matter — only behavior.

**Verdicts**
- `strict_pass` (leaderboard): status matches ∧ canonical effects match 1:1 ∧
  **no extra writes** ∧ state-diff matches; read-only tasks additionally need
  the expected reads signature covered and zero writes.
- `lenient_pass` (debugging): per-effect family+target match with required
  tokens (markers/targets) present, no extra writes.

**Metrics** (`results/<name>.metrics.json`): the headline pass rate plus
valid_json / valid_recipe_schema / run-success / effect-match / extra- &
missing-write rates, fail-stage counts, and breakdowns by tier, primary app,
read/write, linear vs control-flow, foreach, if/else, single vs multi app,
and per-scenario pass rate.

## Live track (`live/`) — pass@1_live_write_verified_strict

Hybrid design per the live-track review: **fixture-backed reads + REAL writes
+ read-back verification**. Original and candidate see the identical fixture
world, but their writes hit the actual test connectors, and the verdict comes
from the real external state read back through the APIs.

- **Isolation (no cross-pollution):** original and candidate run in equivalent
  but separate namespaces — Sheets: a fresh tab per run
  (`b<rid>_<scen>_<side>`); Jira: bench project + marker label + created-key
  registry; Slack: bench channel + exact-`ts` registry (history read-back,
  never search); SF: created-id registry with pre-state snapshots and reverts
  for updates. Physical ids map to logical names / placeholders
  (`logical.sheets.main`, `<JIRA_ISSUE_KEY>`, `<TS>`) before comparison; the
  canonical target is what the recipe *requested*, the physical namespace is
  an environment detail.
- **Write gateway (`dispatch.py`):** every write is rebound into the
  namespace, allowlist-checked (violations are blocked and scored
  `live_policy_violation`), fully logged (extra-write detection never relies
  on read-back alone), and registered for read-after-write, read-back and
  cleanup. Real responses (issue key, message ts) are returned to the recipe
  so downstream refs keep working.
- **Update-target materialization (`rebind.py` + `namespace.py`):** recipes
  that update/comment-on objects carry fabricated keys from fixture data. The
  harness statically finds which fixture paths feed those key inputs,
  materializes a real bench target per run (bench Jira issue; minimal SF
  records with per-sobject required fields), and patches the fixture so the
  refs resolve to the real key — identically for gold and candidate.
- **Salesforce reads go live** (stage3 precedent): update/composite flows
  carry record ids from reads, and fabricated fixture ids would 404 against
  the real org. Original and candidate run back-to-back with cleanup-revert
  between them, so both see the same org.
- **Gold/candidate parity is a contract:** the gold records `live_groups`
  (which provider groups ran live), `live_overrides` (fixture patch
  templates) and `live_needs` (targets to materialize); candidate runs are
  pinned to all three. Changing dispatch semantics invalidates existing live
  gold — rebuild it.
- **Exclusions are honest:** tasks whose live gold cannot be established
  (gold run error, failed materialization — e.g. custom objects absent from
  the dev org —, failed read-back) land in `gold/live_excluded.jsonl` and are
  never scored.
- **Cleanup is a metric:** per-run cleanup plans execute automatically
  (`cleanup_success_rate`); "already gone" counts as success;
  `cleanup_live.py` retries anything pending.

**Scoring** (`score_predictions_live.py`): per scenario, strict pass requires
status match ∧ canonical live diff == gold ∧ no extra writes ∧ no policy
violation ∧ read-back success; read-only gold (no effects AND no write
attempts) requires zero candidate writes; a task passes only if all scenarios
pass. Fail stages: `invalid_json | invalid_recipe_structure | schema_error |
live_run_error | live_readback_error | live_effect_mismatch |
live_extra_write | live_missing_write | live_policy_violation | pass`.
Metrics add `live_write_ack_rate`, `cleanup_success_rate`,
`flake_retry_rate`, and `sandbox_pass_live_fail` / `live_pass_sandbox_fail`
when sandbox results exist under the same run name.

Config: secrets stay in `../.env` (used by the existing live clients);
track settings in `live/live_env.json` (bench Jira project, SF org, read-back
retries). The bench Slack channel comes from `SLACK_CHANNEL_OVERRIDE`, the
bench spreadsheet from `SHEETS_SPREADSHEET_ID`.

## Harness validation status

- **Sandbox:** `selfcheck.py` (original recipes stripped to the minimal
  contract, scored against their own gold) — **1000/1000 strict**.
- **Live:** `selfcheck_live.py` (same, against live gold, in the candidate
  namespace) — **32/32 strict across all four connectors** (2026-06-11),
  cleanup 100%, zero leftover artifacts verified by org-wide sweeps (tabs /
  channel history / JQL / SOQL).
- **Adversarial:** corrupted candidates fail with the right stage in every
  app (extra write / missing write / effect mismatch / schema error /
  invalid JSON / disallowed connector).
- Known live-unsupported (4 excluded): fabricated ids embedded in raw SOQL,
  a nonexistent external-id field and custom object in the dev org, one
  `=`-formula the engine evaluates to None.

## Known limitations / next steps

- Task descriptions are deterministic templates from the semantic graph —
  faithful but mechanical. An optional LLM polish pass over
  `tasks/main_1k.jsonl[].description` would improve readability (keep the
  behavior-contract section intact).
- One negative scenario max per task; "multiple matching items" fixtures and
  deeper branch matrices are future work.
- Foreach keeps the engine's semantics (empty/unresolvable source falls back
  to 2 stub iterations, capped at 3) — identical for gold and candidate.
- Sandbox reads are scored only for read-only tasks (coverage); reads are
  otherwise diagnostic.
- Many recipes' write content comes from org data that is empty in the dev
  org, so their live behavior is a consistent no-op on both sides (visible in
  `live_write_ack_rate`). Seeding the org with realized data would deepen
  SF/Sheets content coverage.
- The live track is costlier by design — run subsets
  (`live_write_verified_100/250`), not all 1,000. Keep runs sequential (one
  task at a time); namespaces isolate sides, not concurrent runs.
- This is **pass@1 without repair**. A "with validator feedback" track can be
  layered on by re-prompting with the `schema_error` detail — report it as a
  separate number.
- The stage3 `partials_split` (321 platform-limited / mock-blank recipes) is
  not scored; if needed, build fixtures via
  `build_fixtures.py --ids ../stage3_test/benchmark/partials_split_ids.txt`
  and evaluate plausibility/fail-safety only.
