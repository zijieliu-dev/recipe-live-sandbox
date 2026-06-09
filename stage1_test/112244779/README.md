# Recipe #10 — `112244779` · SOQL query on Product2 (READ-only)

**Trigger event:** a **recipe-ops process action** (`byin_…recipe_ops…::run_process_action_trigger`) — the recipe is invoked as a "process action" step by the recipe-ops platform (internal, not an external request).

**Salesforce function:** `search_sobjects_soql_v2` — a full **SOQL query** on **Product2** (standard Products). Read-only.

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger byin_…recipe_ops…::run_process_action_trigger` | the recipe is invoked as a process action |
| 2 | `action salesforce::search_sobjects_soql_v2` | run `select id, name, Description, IsActive from Product2 where IsActive = true` |
| 3 | `action byin_…recipe_ops…::complete_run_process_action` | report the result back / complete the process (mocked) |

---

## Initialize Database Snapshot
**Not required.** Reads existing Product2 data; writes nothing.

## Verify Pre-Execution State (optional)
```bash
sf data query --target-org my-dev-org --query "SELECT COUNT() FROM Product2 WHERE IsActive = true"
```
Expectation: ~17 active products.

## Execute Logic Flow
```bash
python3 test_sandbox/run.py 112244779 --live --sample 0
```

**Execution Result Snapshot:**
```json
{
  "id": "112244779",
  "status": "completed",
  "steps": 3,
  "side_effects": [ { "provider": "byin_…recipe_ops…", "operation": "complete_run_process_action" } ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {}
}
```
Live SOQL executed: `select id, name, Description, IsActive from Product2 where IsActive = true` → **17 rows read** (fields `Id, Name, Description, IsActive`).

**One-line result:** *process-action trigger → live SOQL on Product2 returned 17 active products → process completed.*

## Confirm Resulting State (optional)
**No state change** — read only. Product2 count unchanged.

## Environment Recovery
**Not needed.** No writes. `--reset` no-op; `recover_init_db.py` unnecessary.

---

### Notes
- This is a **clean live action query** (unlike #4/#9 which are SF-triggered, or #5 whose adhoc op is unmapped): the SOQL is a real `search_sobjects_soql_v2` call returning real Product2 rows.
- `trigger_fired` is `{}` because the SOQL is hard-coded in the recipe and doesn't read any trigger field.
