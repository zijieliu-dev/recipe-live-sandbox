# Recipe `87092508` — scheduled SF query → Snowflake sync (RUNS; write is MOCKED)

**Mode:** read SF + sync out &nbsp;|&nbsp; **Trigger:** `salesforce::scheduled_sobject_soql_query_v2` &nbsp;|&nbsp; **Live:** Salesforce (read) &nbsp;|&nbsp; **Mocked:** Snowflake

> **Status:** ✅ runs to completion, but its only write goes to **Snowflake**, which is
> **not one of our three live connectors** — so there is **no observable Salesforce effect**.
> The Salesforce *read* (the scheduled query) is live.

## What it does
1. **Trigger** — scheduled SOQL_v2 on Salesforce: "retrieve the new and delta records since yesterday." (live read)
2. `workato_variable/declare_variable` (control)
3. `snowflake/sync_objects_to_snowflake_v2` — pushes the rows into Snowflake. **Mocked.**

## How it's triggered
Scheduled (clock) trigger — in real Workato it fires on a timer; here we fire it by running the command below, which runs the query live.

## Run it
```bash
cd ~/Desktop
python3 test_sandbox/run.py 87092508 --live --trace
```
**Expect:** `status: completed`; a `snowflake::sync_objects_to_snowflake_v2` side-effect tagged as a mocked call. No Salesforce row changes (it only reads SF, then writes to Snowflake).

## To make it write for real
Snowflake would need a live connector (like we built for Jira/Slack) + credentials. Out of scope unless you want Snowflake live.

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **snowflake side-effect seen?:** ☐ &nbsp; **SF rows read (trigger):** &nbsp; **Notes:**
