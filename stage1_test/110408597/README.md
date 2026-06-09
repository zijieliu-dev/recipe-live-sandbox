# Recipe #8 — `110408597` · Look up a User by Id (READ-only)

**Trigger event:** a **recipe function** (`workato_recipe_function::execute`) — a reusable sub-recipe other recipes call, passing parameters (here a `salesforce_object.owner_id`). Not an external request; it's invoked internally.

**Salesforce function:** `search_sobjects` on **User** → a find-by-field **query** (`WHERE Id = '<owner_id>'`). Read-only.

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger workato_recipe_function::execute` | called with `parameters.salesforce_object.owner_id` |
| 2 | `action salesforce::search_sobjects` (User) | run `SELECT Email, Name FROM User WHERE Id = '<owner_id>' LIMIT 1` |
| 3 | `action byin_…recipe_ops…::start_process` | start a downstream process with the result (mocked) |

---

## Initialize Database Snapshot
**Not required.** Reads existing User data; writes nothing.

## Verify Pre-Execution State (optional)
```bash
sf data query --target-org my-dev-org --query "SELECT Id, Name, Email FROM User WHERE IsActive=true AND UserType='Standard' LIMIT 1"
```
Gives a real active User to look up.

## Execute Logic Flow
```bash
python3 test_sandbox/run.py 110408597 --live --sample 0
```
- Sample 0's trigger = `{"parameters": {"salesforce_object": {"owner_id": "005g…"}}}` (seeded from a real active Standard User Id).

**Execution Result Snapshot:**
```json
{
  "id": "110408597",
  "status": "completed",
  "steps": 3,
  "side_effects": [ { "provider": "byin_…recipe_ops…", "operation": "start_process" } ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": { "parameters": { "salesforce_object": { "owner_id": "005g5000006ezEDAAY" } } }
}
```
Live SOQL executed: `SELECT Email, Name FROM User WHERE Id = '005g5000006ezEDAAY' LIMIT 1` → **1 row read: `OrgFarm EPIC` / `epic.orgfarm@salesforce.com`.**

**One-line result:** *given a real User Id, the live lookup returned that User's Name + Email → process started.*

## Confirm Resulting State (optional)
**No state change** — read only. User count unchanged.

## Environment Recovery
**Not needed.** No writes. `--reset` no-op; `recover_init_db.py` unnecessary.

---

### Notes
- The realizer restricts the User Id to an **active Standard user** (so the lookup returns a normal user, not an integration/automated account).
- Two SOQL calls at runtime: the realizer picking a real User Id, then the recipe's actual lookup.
