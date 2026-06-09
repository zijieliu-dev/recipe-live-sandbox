# Recipe #7 — `117979300` · Search Opportunities by name (READ-only)

**Trigger event:** a **Slack dynamic-menu / typeahead** (`slack_bot::dynamic_menu`). As a user types, the recipe searches Salesforce Opportunities by `Name` and returns menu options.

**Salesforce function:** `search_sobjects_soql` on **Opportunity** → SOQL **query** (`NAME LIKE '%…%'`, limit 150). Read-only.

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger slack_bot::dynamic_menu` | fires with the user's typed value (`typeahead.value`) |
| 2 | `action salesforce::search_sobjects_soql` | run `SELECT Id, Name FROM Opportunity WHERE NAME LIKE '%<typed>%' LIMIT 150` |
| 3 | `action slack_bot::generate_menu_options` | turn matched Opportunities into Slack menu options (mocked) |

---

## Initialize Database Snapshot
**Not required.** Reads existing Opportunity data; writes nothing.

## Verify Pre-Execution State (optional)
```bash
sf data query --target-org my-dev-org --query "SELECT Id, Name FROM Opportunity WHERE Name LIKE '%Dic%'"
```
Expectation: 1 row — **Dickenson Mobile Generators**.

## Execute Logic Flow
```bash
python3 test_sandbox/run.py 117979300 --live --sample 0
```
- Sample 0's trigger = `{"typeahead": {"value": "Dic"}}` (seeded from a real Opportunity name).

**Execution Result Snapshot:**
```json
{
  "id": "117979300",
  "status": "completed",
  "steps": 3,
  "side_effects": [ { "provider": "slack_bot", "operation": "generate_menu_options" } ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": { "typeahead": { "value": "Dic" } }
}
```
Live SOQL executed: `SELECT Id, Name FROM Opportunity WHERE NAME LIKE '%Dic%' LIMIT 150` → **1 row read: `Dickenson Mobile Generators` (006g5000003ukw5AAA)`.**

**One-line result:** *typed "Dic" → live Opportunity search returned "Dickenson Mobile Generators" → menu built.*

## Confirm Resulting State (optional)
**No state change** — read only. Opportunity count unchanged (31).

## Environment Recovery
**Not needed.** No writes. `--reset` no-op; `recover_init_db.py` unnecessary.

---

### Notes
- Other samples type different real Opportunity-name prefixes, so the live query returns the corresponding Opportunity(ies).
- As with #6, two SOQL calls appear: the realizer fetching a real `Name` to type, then the recipe's actual search.
