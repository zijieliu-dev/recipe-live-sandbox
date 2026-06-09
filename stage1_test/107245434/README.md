# Recipe #6 — `107245434` · Search Accounts by name (READ-only)

**Trigger event:** a **Slack dynamic-menu / typeahead** (`slack_bot::dynamic_menu`). As a user types in a Slack picklist, the recipe searches Salesforce Accounts whose `Name` matches what they typed and returns menu options.

**Salesforce function:** `search_sobjects_soql` on **Account** → a SOQL **query** (`Name LIKE '%…%'`). Read-only.

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger slack_bot::dynamic_menu` | fires with the user's typed value (`typeahead.value`) |
| 2 | `action salesforce::search_sobjects_soql` | run `SELECT Name, Id FROM Account WHERE Name LIKE '%<typed>%' LIMIT 20` |
| 3 | `action slack_bot::generate_menu_options` | turn the matched Accounts into Slack menu options (mocked) |

---

## Initialize Database Snapshot
**Not required.** Reads existing Account data; writes nothing. (Uses your org's real Accounts as the read context.)

## Verify Pre-Execution State (optional)
```bash
sf data query --target-org my-dev-org --query "SELECT Id, Name FROM Account WHERE Name LIKE '%Edg%'"
```
Expectation: 1 row — **Edge Communications**.

## Execute Logic Flow
```bash
python3 test_sandbox/run.py 107245434 --live --sample 0
```
- Sample 0's trigger = `{"typeahead": {"value": "Edg"}}` (the realizer seeds the typed value from a real Account name).

**Execution Result Snapshot:**
```json
{
  "id": "107245434",
  "status": "completed",
  "steps": 3,
  "side_effects": [ { "provider": "slack_bot", "operation": "generate_menu_options" } ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": { "typeahead": { "value": "Edg" } }
}
```
Live SOQL executed: `SELECT Name, Id FROM Account WHERE Name LIKE '%Edg%' LIMIT 20` → **1 row read: `Edge Communications` (001g500000MKbA2AAL)`.**

**One-line result:** *typed "Edg" → live Account search returned "Edge Communications" → menu built.*

## Confirm Resulting State (optional)
**No state change** — read only. Account count unchanged (16).

## Environment Recovery
**Not needed.** No writes. `--reset` no-op; `recover_init_db.py` unnecessary.

---

### Notes
- Different samples type different prefixes (each picks a real Account name, e.g. `Bur` → *Burlington Textiles…*), so the live query returns the matching Account(s).
- Two SOQL calls appear at runtime: the first is the realizer fetching a real `Name` to type; the second is the recipe's actual search.
