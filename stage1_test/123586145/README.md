# Recipe #5 — `123586145` · Scheduled → SF adhoc-HTTP → Snowflake (LIVE)

**Trigger event:** a **schedule** (`clock::scheduled_event`). Job: *fetch deleted `OpportunityTeamMember` records from Salesforce (via a raw REST call) and sync them to Snowflake.*

**Salesforce function:** `__adhoc_http_action` — a **raw REST call** (`GET /services/data/vXX/sobjects/<obj>/deleted/?start=…&end=…`, the Salesforce *getDeleted* resource). Read-only. **Now mapped to a real live call.**

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger clock::scheduled_event` | fires on a schedule |
| 2 | `action workato_variable::declare_variable` | set object name + start/end window (mocked vars) |
| 3 | `action salesforce::__adhoc_http_action` | **GET** `/sobjects/OpportunityTeamMember/deleted/?start=…&end=…` (real REST) |
| 4 | `action workato_variable::declare_list` | build a list (mocked) |
| 5 | `if <condition>` | branch on the result |
| 6 | `action snowflake::sync_objects_to_snowflake_v2` | sync deleted records to Snowflake (mocked) |

---

## Initialize Database Snapshot
**Not required.** Read-only; no rows written.

## Verify Pre-Execution State (optional)
The `getDeleted` endpoint works on objects that support it. Confirm on Account (returns recently-deleted records):
```bash
# (the adhoc handler builds this same call shape)
# GET /services/data/v59.0/sobjects/Account/deleted/?start=2026-05-31T00:00:00Z&end=2026-06-03T00:00:00Z
```
Proven result: Account → `deletedRecords` (e.g. 6 rows), plus `earliestDateAvailable`, `latestDateCovered`.

## Execute Logic Flow
```bash
python3 test_sandbox/run.py 123586145 --live --sample 0
```

**Execution Result Snapshot:**
```json
{
  "id": "123586145",
  "status": "completed",
  "steps": 6,
  "side_effects": [ { "provider": "salesforce", "operation": "__adhoc_http_action" } ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {}
}
```
**Live call actually made:** `GET /services/data/v63.0/sobjects/OpportunityTeamMember/deleted/?start=2026-05-31T00:00:00Z&end=2026-06-02T00:00:00Z`.

**One-line result:** *scheduled job makes a real Salesforce `getDeleted` REST call; for `OpportunityTeamMember` the org returns `NOT_FOUND` (see below); Snowflake sync is mocked.*

## Confirm Resulting State (optional)
**No state change** — read-only (`getDeleted` is a read). Nothing written.

## Environment Recovery
**Not needed.** No writes.

---

### Status: now LIVE (with one org caveat)
- ✅ **Fixed:** `__adhoc_http_action` is mapped in `live/salesforce.py` → it issues the real `verb` + `path` to Salesforce. (Before, it returned `{}` with no call.)
- ✅ **Mechanism proven:** the same `getDeleted` call on **`Account`** returns **6 deleted records** live.
- ⚠️ **This recipe's object** (`OpportunityTeamMember`) returns **`NOT_FOUND`** in this dev org — its `getDeleted` resource isn't available (Team Selling not enabled). That's a real Salesforce response, captured gracefully (the recipe still completes). To see real data, point the recipe's `salesforce_object_name` variable at a supported object (e.g. `Account`).
