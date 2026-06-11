# Stage-3 live benchmark

Built by `build_benchmark.py` from `groundtruth/`. Two splits.

## main_1k  (SCORED, n=1000)
Recipes that executed at least one **live action** (a real Salesforce / Slack /
Jira / Google-Sheets read or write) and had **no failed live effect** — i.e. they
cleanly exercised the real software. Use this as the scored benchmark.

Per-recipe fields: `id`, `tier`, `primary_app`, `apps`, `live_action_steps`,
`status`, and (for writes) `live_write_ops`.

- `tier`: {'live_read': 511, 'live_write': 489}
- `primary_app`: {'Slack': 387, 'SF': 207, 'Jira': 207, 'Sheets': 199}

"Read-only" recipes (`tier=live_read`) genuinely hit the live API but only read
(no write side-effect) — accepted as success per the benchmark definition.

Selection: all clean live-writes + all non-Slack clean reads + Slack reads to
fill 1000 (Slack is ~46% of the clean pool; this trims it for connector
diversity). Deterministic by id.

## partials_split  (NOT scored, n=321)
Recipes that landed some live effect but had a blocked one. Kept as a labelled
platform-limited / stress split — **not counted as success**.

- `label`:
  - `platform_limited` — blocked by `block_kit_modals`, which needs a real,
    single-use Slack `trigger_id` from a live interaction (no API to mint one).
    These genuinely exercise live Slack; the modal-open is a Slack platform limit.
  - `mock_blank` — a Slack/Sheets write whose content came from mocked upstream
    steps returning empty, or was blank-by-design. Not honestly fixable in batch.
- label counts: {'platform_limited': 287, 'mock_blank': 34}

Per-recipe fields: `id`, `label`, `blocker`, `did_live_write`, `apps`, `failed_ops`.
