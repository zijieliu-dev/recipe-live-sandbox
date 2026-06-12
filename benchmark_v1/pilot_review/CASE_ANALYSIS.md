# Per-case analysis — opus_pilot (10 tasks)

For every claim below, the evidence is in `cases/<task_id>/`:
`1_prompt_model_input.txt` (exact model input), `2_model_output_raw.txt`
(exact model output), `3_groundtruth_gold.json` (gold canonical
effects/reads), `4_verdict.json` (per-scenario diffs).

A note on this slice: tasks 0–9 are all `live_read` tier. Most have ZERO gold
write effects — for those, strict pass = "completed with the same status,
zero writes, and the gold read signature covered". Two (000002, 000009) have
one write effect; one (000003) writes a service reply then stops.

---

## ✅ Successes (7)

### 000000 — Slack dynamic menu (pass)
Gold: status `completed`, no effects, reads
`[workato_custom_code::invoke_custom_ruby_code, slack_bot::generate_menu_options]`.
The model rebuilt the chain: custom-ruby step computing the menu payload →
`generate_menu_options`. Both required reads observed, zero writes → strict
pass. (Contrast with 000006, the same pattern, where it skipped the steps.)

### 000001 — Slack dynamic menu with try/catch (pass)
Same read signature as 000000 but the original wraps the work in try/catch.
The model emitted the try/catch structure and the right steps. Note the
harness does NOT require try/catch per se — block structure never matters —
only that the run completes with the same reads/effects.

### 000002 — recipe function → Google Sheets (pass)
The only success with a real write effect: gold has one
`google_sheets::add_spreadsheet_row_v4` plus a
`workato_recipe_function::return_result` read. The model's add-row effect
canonicalized to the identical sheet/row-value matrix (column ORDER is
normalized away by the Sheets canonicalizer, so a different column ordering
would still have passed). 1:1 effect match, no extras → strict pass.

### 000004 — app home opened (pass)
Smallest task: trigger `app_home_opened` → `open_bot_app_home`. The model's
2-step recipe produced the single required read and no writes. This case is a
good "minimum viable pass" to read first if you want to trace the pipeline
end to end — the prompt is ~3K tokens and the output is 5 lines.

### 000005 — dynamic menu (currencies) (pass)
Reads include a CUSTOM connector (`countries_connector_...::list_currencies`).
Shows the catalog mechanism working: the custom connector's schema was in the
allowed catalog, the model used it, the fixture answered it.

### 000007 — dynamic menu (office locations, parameterized) (pass)
Like 000000 but the menu takes a `parameters` input from the trigger. The
model wired the trigger ref into the custom-code input correctly.

### 000008 — dynamic menu (timezones) (pass)
Same family as 000000/000005. Nothing notable; included for completeness.

---

## ❌ Failures (3)

### 000003 — Salesforce lead-conversion service — `effect_mismatch` (strict FAIL, lenient PASS)
**Hardest task in the slice** (~8.7K-token prompt, try/catch + 4 if-branches
+ stop steps). Gold: status `stopped`, one effect —
`workato_service::send_reply` with:
```json
{"reply": {"converted_account_id":     "convertedaccountid_793",
           "converted_contact_id":     "convertedcontactid_930",
           "converted_opportunity_id": "convertedopportunityid_39"},
 "reply_type": "success"}
```
Model's reply (the `extra_writes_strict` entry in `4_verdict.json`):
```json
{"reply": {"converted_contact_id": ["convertedcontactid_930", "convertedcontactid_905"]},
 "reply_type": "success"}
```
Two distinct mistakes:
1. **Wrong ref altitude**: the value is a LIST of two ids — the model
   referenced the field across the whole `search_sobjects` result list
   instead of the single matched record (`records.first` / current-item
   style ref).
2. **Dropped fields**: `converted_account_id` and `converted_opportunity_id`
   are missing even though the description's reply_schema lists all three.

Status (`stopped`) and branch routing were CORRECT — it took the
"ConvertedContactId is present → success reply → stop" path. Lenient passes
because family+target match and the marker token is present.
**Verdict on the verdict**: legitimate fail; a real caller of this service
would receive a malformed reply.

### 000006 — Slack dynamic menu (Namely job titles) — `effect_mismatch` (strict FAIL, lenient FAIL, both scenarios)
The only task in the slice with 2 scenarios (`positive`,
`branch_8_false`) and the only one that also fails LENIENT. Gold (both
scenarios): completed, no effects, reads
`[invoke_custom_ruby_code, generate_menu_options]`. The model's recipe
completed with zero writes (status ✓, writes ✓) but produced NEITHER required
read — it skipped the custom-ruby transformation and the menu-options step
entirely in both scenarios (`missing_reads` in `4_verdict.json`).
The model solved 000000/000007/000008 — the same pattern — so this is a
per-instance miss, not a systematic inability.
**Verdict on the verdict**: correct under the current rule (read-only tasks
require the gold read signature). This is the case to look at for design
question #2 in the README: a recipe that "does nothing visible, differently"
— is read-signature coverage the right equivalence test for read-only tasks?
(Supporting the rule: without it, an EMPTY recipe would pass every read-only
task, which would be absurd. The fixture read-fallback already tolerates a
different op on the same provider+object, so reasonable strategy variation
is allowed; wholesale skipping is not.)

### 000009 — scheduled Slack→Snowflake sync — `effect_mismatch` (strict FAIL, lenient PASS)
Gold: one `snowflake::sync_objects_to_snowflake_v2` effect on object
`SLACK.USERS`. Diff the missing-vs-extra entries in `4_verdict.json`: the row
DATA is byte-identical; the input map differs only in:

| field | gold | model |
|---|---|---|
| rows param name | `rows: [...]` | `source: [...]` |
| `flatten_columns` | `"true"` (string) | `true` (bool) |
| `flatten_level` | `"1"` (string) | `1` (int) |

The model picked a plausible-but-wrong parameter name and used JSON-native
types where the original recipe (built in Workato's UI) stored strings.
**Verdict on the verdict**: this is the borderline case — design question #1
in the README. Options: (a) keep as-is (the connector schema in the prompt
does name the field, so this is a schema-following error the benchmark
arguably SHOULD punish); (b) make the canonicalizer coerce boolean-ish
scalars (`"true"`/`true`, `"1"`/`1`) before comparison, which would still
fail this case on `rows`/`source` but make the metric less brittle overall;
(c) add per-app parameter-alias tables like the existing op-name families.
Recommend (b) as a low-risk improvement; (c) only with evidence the aliases
are truly equivalent in the real connector.

---

## Pattern summary

- All 10 outputs were valid, schema-clean, runnable recipes — the funnel
  losses are entirely at semantic equivalence, which is where you want a
  benchmark to discriminate.
- 2 of 3 strict failures are payload-content misses (ref altitude, dropped
  fields, type/name variants) — the strict metric is doing exactly its job
  of separating "plausible recipe" from "execution-equivalent recipe".
- 1 of 3 failures (000006) is a genuine behavior miss (skipped logic), and
  it is also the only lenient failure — consistent with lenient's purpose.
- Control-flow is the weak spot: `control_flow_recipe_pass_rate` 0.0 vs
  `linear_recipe_pass_rate` 0.875 (small n: 2 control-flow tasks, both
  failed; 8 linear, 7 passed).
