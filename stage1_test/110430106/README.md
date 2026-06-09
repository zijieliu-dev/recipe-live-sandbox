# Recipe #9 — `110430106` · Scheduled SF SOQL trigger → Snowflake (LIVE)

**Trigger event:** a **scheduled Salesforce SOQL query** (`salesforce::scheduled_sobject_soql_query`) over the **`Period`** object. On a schedule, Salesforce runs the query and fires the recipe per result row.

**Salesforce role = the TRIGGER, not an action** (like #4). The SOQL lives in the trigger; there is no separate live SF read step.

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger salesforce::scheduled_sobject_soql_query` (`Period`) | scheduled SOQL on Period; fires with each result row |
| 2 | `action workato_variable::declare_variable` | set up a working variable (mocked) |
| 3 | `action snowflake::sync_objects_to_snowflake_v2` | sync the row(s) into Snowflake (mocked) |

---

## Initialize Database Snapshot
**Not required.** No Salesforce writes. `Period` already has data (119 rows — standard fiscal periods).

## Verify Pre-Execution State (optional)
```bash
sf data query --target-org my-dev-org --query "SELECT Id, Type, StartDate, EndDate FROM Period LIMIT 3"
```
Expectation: real Period rows (e.g. `Type=Year, 2025-01-01 → 2025-12-31`).

jesseliu@Jesses-MacBook-Pro Desktop % sf data query --target-org my-dev-org --query "SELECT Id, Type, StartDate, EndDate FROM Period LIMIT 3"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.
┌────────────────────┬─────────┬────────────┬────────────┐
│ ID                 │ TYPE    │ STARTDATE  │ ENDDATE    │
├────────────────────┼─────────┼────────────┼────────────┤
│ 026g5000001Mm5RAAS │ Year    │ 2025-01-01 │ 2025-12-31 │
│ 026g5000001Mm5SAAS │ Quarter │ 2025-01-01 │ 2025-03-31 │
│ 026g5000001Mm5TAAS │ Quarter │ 2025-04-01 │ 2025-06-30 │
└────────────────────┴─────────┴────────────┴────────────┘

Total number of records retrieved: 3.
Querying Data... done

## Execute Logic Flow
```bash
python3 test_sandbox/run.py 110430106 --live --sample 0
```
- The harness reads a **real `Period` record** (via `realize_sf_trigger`) and uses it as the trigger event; Snowflake sync is mocked.

**Execution Result Snapshot:**
```json
{
  "id": "110430106",
  "status": "completed",
  "steps": 3,
  "side_effects": [
    {
      "provider": "snowflake",
      "operation": "sync_objects_to_snowflake_v2",
      "data": {
        "input": {
          "flatten_columns": "false",
          "flatten_level": "1",
          "key_columns": "Id",
          "rows": null,
          "table": "FORECASTING_PERIOD"
        }
      }
    }
  ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {
    "Id": "026g5000001Mm5RAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Year",
    "StartDate": "2025-01-01",
    "EndDate": "2025-12-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": false,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 1,
    "FullyQualifiedLabel": "FY 2025"
  }
}
```
**One-line result:** *a real Period record (Type=Year, 2025) is read as the trigger → recipe completes → Snowflake sync (mocked).*

## Confirm Resulting State (optional)
**No state change** — Period is read; nothing written. Counts unchanged.

## Environment Recovery
**Not needed.** No writes. `--reset` no-op; `recover_init_db.py` unnecessary.

---

### Notes
- Second **Salesforce-*triggered*** recipe (with #4). Now runs on **real Period data** via `realize_sf_trigger` (reads a real record of the watched object).
- Unlike #4, no setup was needed — `Period` already has rows, so no record had to be generated.

Data flow (what it does end to end)

[daily schedule]
      │
  [1] SF scheduled SOQL on Period  ──►  Period rows  (trigger output)
      │                                     │
  [2] set Table = "FORECASTING_PERIOD"       │
      │                                     ▼
  [3] snowflake.sync ◄── rows = Period rows, table = FORECASTING_PERIOD, key = Id
Net effect: every day, the org's fiscal Period records are synced into Snowflake's FORECASTING_PERIOD table.

Step 1 — Trigger: salesforce::scheduled_sobject_soql_query (on Period)
  
A scheduled Salesforce query. Config: sobject_name = Period, schedule = daily (with day-of-week flags + hour/minute, batch_size).

➡️  Logic: "Once a day, Salesforce runs a SOQL over the Period object and fires the recipe with the result rows." The trigger's output is the list of Period
records (readable as _ref(salesforce, ["Period"])).

(This is the SF-triggered kind — the query is the event source, not an action.)

Step 2 — Action: workato_variable::declare_variable

Sets a variable Table = "FORECASTING_PERIOD".

➡️  Logic: "Decide the destination Snowflake table name = FORECASTING_PERIOD." (Just stores a string for the next step.)

Step 3 — Action: snowflake::sync_objects_to_snowflake_v2

- rows: =_ref("salesforce", ["Period"]) → the Period records from the trigger
- table: #{_ref("workato_variable", ["Table"])} → FORECASTING_PERIOD
- key_columns: Id (upsert key)

➡️  Logic: "Upsert the Period records into the Snowflake table FORECASTING_PERIOD, keyed by Id."