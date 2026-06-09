# Recipe #4 — `107245910` · Salesforce-TRIGGERED → Pub/Sub (LIVE)

**Trigger:** `salesforce::new_custom_object` **monitoring `OpportunityFieldHistory`**. This object gets a new row **automatically whenever a *tracked field* on an existing Opportunity changes** (e.g. `Amount`). The recipe fires on that new row and publishes the change to a pub/sub topic.

It does **not** fire on creating an Account or even creating an Opportunity — only on **changing a tracked field of an existing Opportunity** (that's what writes an `OpportunityFieldHistory` row).

---

## How "monitoring" works (live vs local)

- **Live Workato:** the recipe **polls `OpportunityFieldHistory` every 5 seconds** automatically. You don't run anything — the moment someone edits an Opportunity's `Amount`, a history row appears and the recipe fires on its own.
- **Local sandbox:** there is **no background poller.** Instead you *cause* the change, then *fire once* — `run.py --live` reads the latest real history row and runs the recipe on it. (If no history row exists yet, it auto-generates one by bumping an Opportunity's `Amount`.)

So "monitoring" = Workato's job in production; locally we reproduce the *event* + a single fire.

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger salesforce::new_custom_object` (`OpportunityFieldHistory`) | fires on a new field-change row; that row is the trigger payload |
| 2 | `action workato_pub_sub::publish_to_topic` | publish the changed-field record to a pub/sub topic (mocked) |

---

## One-time Setup (already applied)
Field-history tracking had to be enabled once (metadata deploy to the org): Opportunity `enableHistory=true` + `Amount` field `trackHistory=true`. After this, changing `Amount` on any Opportunity creates a real history row.

---

## Step-by-step: cause the change, then fire it

### Step A — pick an Opportunity and note its Amount
```bash
sf data query --target-org my-dev-org --query "SELECT Id, Name, Amount FROM Opportunity LIMIT 1"
```
Copy its `Id`.

jesseliu@Jesses-MacBook-Pro Desktop % sf data query --target-org my-dev-org --query "SELECT Id, Name, Amount FROM Opportunity LIMIT 1"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.
┌────────────────────┬─────────────────────────────┬────────┐
│ ID                 │ NAME                        │ AMOUNT │
├────────────────────┼─────────────────────────────┼────────┤
│ 006g5000003ukw5AAA │ Dickenson Mobile Generators │ 15000  │
└────────────────────┴─────────────────────────────┴────────┘

Total number of records retrieved: 1.
Querying Data... done

### Step B — CHANGE the Opportunity's Amount (this is the event Workato would "see")
```bash
sf data update record --target-org my-dev-org --sobject Opportunity --record-id 006g5000003ukw5AAA --values "Amount=20000"
```
jesseliu@Jesses-MacBook-Pro Desktop % sf data update record --target-org my-dev-org --sobject Opportunity --record-id 006g5000003ukw5AAA --values "Amount=20000"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.
Successfully updated record: 006g5000003ukw5AAA.
Updating Record... Success

### Step C — verify Salesforce created the history row (the trigger event)
```bash
sf data query --target-org my-dev-org --query "SELECT Id, Field, OldValue, NewValue, OpportunityId, CreatedDate FROM OpportunityFieldHistory ORDER BY CreatedDate DESC LIMIT 1"
```
Expect a row like: `Field=Amount, OldValue=15000, NewValue=20000`.

jesseliu@Jesses-MacBook-Pro Desktop % sf data query --target-org my-dev-org --query "SELECT Id, Field, OldValue, NewValue, OpportunityId, CreatedDate FROM OpportunityFieldHistory ORDER BY CreatedDate DESC LIMIT 1"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.
┌────────────────────┬────────┬──────────┬──────────┬────────────────────┬──────────────────────────────┐
│ ID                 │ FIELD  │ OLDVALUE │ NEWVALUE │ OPPORTUNITYID      │ CREATEDDATE                  │
├────────────────────┼────────┼──────────┼──────────┼────────────────────┼──────────────────────────────┤
│ 017g500000CxgnkAAB │ Amount │ 15000    │ 20000    │ 006g5000003ukw5AAA │ 2026-06-03T23:51:24.000+0000 │
└────────────────────┴────────┴──────────┴──────────┴────────────────────┴──────────────────────────────┘

Total number of records retrieved: 1.
Querying Data... done

### Step D — FIRE the recipe (it reads that real row and publishes it)
```bash
python3 test_sandbox/run.py 107245910 --live --sample 0
```
**Result snapshot:**
```json
{
  "id": "107245910",
  "status": "completed",
  "steps": 2,
  "side_effects": [
    {
      "provider": "workato_pub_sub",
      "operation": "publish_to_topic",
      "data": {
        "input": {
          "message": {
            "CreatedDate": "2026-06-03T23:51:24.000+0000",
            "Field": "Amount",
            "ID": "017g500000CxgnkAAB",
            "NewValue": "20000",
            "OldValue": "15000",
            "ParentID": "006g5000003ukw5AAA"
          },
          "topic_id": "30314"
        }
      }
    }
  ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {
    "Id": "017g500000CxgnkAAB",
    "IsDeleted": false,
    "OpportunityId": "006g5000003ukw5AAA",
    "CreatedById": "005g5000006qRIPAA2",
    "CreatedDate": "2026-06-03T23:51:24.000+0000",
    "Field": "Amount",
    "DataType": "Currency",
    "OldValue": "15000",
    "NewValue": "20000"
  }
}
```
`trigger_fired` = the **real history row**; `side_effects` shows it published to pub/sub. *(Shortcut: you can skip Steps A–C and just run Step D — `run.py --live` auto-generates a history row if none exists.)*

### Step E — (optional) revert the Opportunity Amount
Use the **Opportunity** id (`006…` from Step A) — NOT the history-row id (`017…`):
```bash
sf data update record --target-org my-dev-org --sobject Opportunity --record-id 006g5000003ukw5AAA --values "Amount=15000"
```
jesseliu@Jesses-MacBook-Pro Desktop % sf data update record --target-org my-dev-org --sobject Opportunity --record-id 006g5000003ukw5AAA --values "Amount=15000"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.
Successfully updated record: 006g5000003ukw5AAA.
Updating Record... Success

(The history row persists — that's the point of field history. The recipe itself wrote nothing to undo.)

---

## Before / After
| | Opportunity `Amount` | `OpportunityFieldHistory` |
|---|---|---|
| before Step B | 15000 | (no Amount-change row) |
| after Step B | 20000 | **+1 row** `Amount: 15000→20000` ← the trigger event |
| after Step D (fire) | 20000 | unchanged (recipe only *reads* it) |
| after Step E (revert) | 15000 | row persists (history is permanent) |

## Environment Recovery
The recipe writes nothing, so nothing to undo. The only mutation is *your* Step-B `Amount` change, which you revert in Step E (or via `--reset`). History rows are permanent by design.

"Monitoring" isn't something you run locally.
  - Live Workato: the recipe auto-polls OpportunityFieldHistory every 5s — editing an Opportunity fires it automatically.
  - Local: no poller. You cause the change, then fire once with run.py --live (which reads the resulting real history row).

