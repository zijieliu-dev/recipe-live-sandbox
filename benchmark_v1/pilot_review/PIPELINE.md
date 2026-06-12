# The eval pipeline, end to end

What happens between "a task exists" and "a strict/lenient verdict exists".
Two halves: the **build side** (done once, produces the dataset + gold) and
the **scoring side** (run per model).

```
BUILD (once)                                   SCORE (per model run)
============                                   =====================
source recipe (hidden)                          prompts/<tid>.txt
  | semantic_graph.py                              | gen_predictions.py
  v                                                v   (Claude API, 1 user msg,
executed-dataflow graph                            |    adaptive thinking, raw text saved)
  | build_fixtures.py                           results/<name>.predictions.jsonl
  v                                                | score_predictions.py -> run_candidate.py
fixture: trigger event + recorded reads            v
+ BENCH markers + branch scenarios            1. PARSE        raw text -> JSON          (fail: invalid_json)
  | run_original.py  (runs the ORIGINAL       2. NORMALIZE    metadata only; semantics  (fail: invalid_recipe_structure
  v   recipe in the sandbox)                       never repaired; unknown op/provider     / schema_error)
gold/groundtruth_effects.jsonl                3. EXECUTE      sandbox, same fixture,    (fail: run_error)
(canonical effects+reads+status                    every scenario
 +state-diff per scenario)                    4. CANONICALIZE per-app normal forms
  | gen_tasks.py + build_prompts.py           5. COMPARE      vs gold, per scenario     (fail: effect_mismatch)
  v                                                |
tasks/main_1k.jsonl + prompts/                     v
                                              strict / lenient verdict; task passes
                                              only if ALL scenarios pass
```

## Build side (stages 1–5)

1. **Catalog** (`build_catalog.py`): extracts 1,298 atomic action/trigger
   schemas from the connector manifest. These are what the model gets to see —
   atomic op schemas only, never recipe fragments, so the benchmark tests
   generation, not retrieval.
2. **Graph** (`semantic_graph.py`): parses the source recipe into its executed
   dataflow — which refs feed which inputs, which fields feed conditions,
   what a foreach iterates. Never trusts comments.
3. **Fixtures** (`build_fixtures.py`): records a deterministic world per
   recipe: the trigger event, every external read's response, plus
   - a unique `BENCH_<rid>` marker injected into free-text fields that do NOT
     feed any branch condition (this is what lenient matching keys on);
   - a branch-satisfaction loop: if-conditions whose lhs is a pure ref into
     fixtured data are toggled TRUE so the positive path executes;
   - scenario variants: `positive` plus `branch_<n>_false` negatives where a
     taken branch is statically flippable (control-flow stress — see case
     000006, which has 2 scenarios).
4. **Gold** (`run_original.py`): runs the ORIGINAL recipe in the sandbox on
   the fixture, records canonical effects / reads / status / state-diff per
   scenario into `gold/groundtruth_effects.jsonl`.
5. **Tasks + prompts** (`gen_tasks.py`, `build_prompts.py`): generates the NL
   description from the dataflow graph (deterministic template), and
   assembles the model-facing prompt.

## What the model receives (see any `cases/*/1_prompt_model_input.txt`)

One user message containing, in order:
- the task description (goal, trigger, steps, branch conditions, and an
  "Expected observable behavior" contract line);
- runtime inputs (if any);
- the action/control-flow schema catalog for the ALLOWED connectors only
  (`allowed_connectors` in the task row) — input/output field schemas per op;
- the recipe grammar: tree structure, `#{_ref("provider","alias",[path])}`
  reference syntax, condition-tree shape, operand list;
- "Return ONLY the recipe JSON object. No markdown, no prose."

The source recipe is never shown. The model must output:
`{"recipe": {"keyword": "trigger", ..., "block": [...steps...]}}`.

## Generation (`gen_predictions.py` — added for this pilot)

Per task: read the prompt file, call the Claude API (model `claude-opus-4-8`,
`thinking={"type":"adaptive"}`, streaming, `max_tokens=16000`), save the raw
text response unmodified to `results/<name>.predictions.jsonl`
(`{"task_id", "output"}`). Resumable: re-running skips task_ids already in
the file. No retry-on-refusal, no output cleanup, no repair loop — pass@1.

## Scoring (`score_predictions.py` → `run_candidate.py`), per task

1. **Parse.** `json.loads` of the raw output (one tolerated variation:
   markdown fences are stripped if present). Fail stage: `invalid_json`.
2. **Normalize** (`normalize_recipe.py`). Fills metadata the harness owns:
   step numbers, uuids, toggleCfg, extended_*_schema. Semantic content
   (provider, operation, field names, refs, conditions) is NEVER repaired.
   Unknown provider/op or a disallowed connector → `schema_error`. Structural
   smells the engine tolerates (dangling refs, vestigial steps) become
   warnings only — execution equivalence is the judge.
3. **Execute** (`sandbox.py`) on the same fixture the gold used, once per
   scenario. Reads are served from the fixture keyed by
   `provider::operation[::object]`, with a graceful fallback: same
   provider+object via a DIFFERENT op returns the same data, so an equivalent
   read strategy still works. Writes are intercepted, logged as effects, and
   answered with recorded or deterministic stub outputs. Foreach keeps engine
   semantics (empty/unresolvable source → 2 stub iterations, capped 3) —
   identical for gold and candidate. Fail stage: `run_error`.
4. **Canonicalize** (`canonicalizers/`). Per-app effect normal forms:
   - Slack: channel, extracted plain text, button titles/params, modal title
   - Jira: project, issue type, summary, description, labels, priority
   - Sheets: sheet, column order, row value matrix
   - Salesforce: sobject, semantic field map
   Volatile data (ts/uuid/run ids) dropped; op-name variants collapsed into
   families (`post_bot_message`/`post_message_to_channel` →
   `slack.post_message`). Block order, aliases, UUIDs, equivalent
   formulations never matter.
5. **Compare** (`compare_effects.py`), per scenario:
   - **strict**: status match ∧ canonical effect multiset == gold 1:1 ∧ no
     extra writes ∧ state-diff match; read-only gold additionally requires
     the gold read signature covered and zero candidate writes.
   - **lenient**: every gold effect has a candidate effect with same
     family+target containing the required tokens (BENCH markers / targets);
     no extra writes.
   A task passes only if ALL scenarios pass. Fail stage: `effect_mismatch`.

## Fail stages (mutually exclusive, in order)

`invalid_json` → `invalid_recipe_structure` → `schema_error` → `run_error`
→ `effect_mismatch` → `pass`. The metrics file counts each, so you can see
WHERE candidates die, not just how many.

## Why the harness is trustworthy (validation status)

- `selfcheck.py`: all 1,000 original recipes, stripped to the minimal
  contract a model would emit, scored against their own gold → 1000/1000
  strict. (If the harness were lossy, originals would fail their own gold.)
- Adversarial corruptions (extra write / missing write / wrong field /
  disallowed connector / broken JSON) fail with the correct stage in every
  app.
- The live track (real Slack/Jira/Sheets/SF writes + API read-back) is
  validated separately: 474/474 strict on live selfcheck; see the main
  README for details. This pilot is sandbox-track only.
