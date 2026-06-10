# Recipe `131400470` — batch trigger → Google Sheets bulk add (RUNS; write is MOCKED)

**Mode:** read SF batch + sync out &nbsp;|&nbsp; **Trigger:** `salesforce::sobject_batch_created_or_updated` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** Google Sheets

> **Status:** ✅ runs to completion, but (a) its trigger watches a **managed-package object
> `skilljar__Course_Progress__c` that doesn't exist here**, so the trigger batch comes back
> **empty**, and (b) its only write goes to **Google Sheets (mocked)**. So there's **no
> observable Salesforce effect**.

## What it does
1. **Trigger** — batch of created/updated `skilljar__Course_Progress__c` rows. (object missing here → empty)
2. `try` → `google_sheets/add_row_v4_bulk` — append the rows to a sheet. **Mocked.**
3. `catch` → `stop`.

## How it's triggered
Batch trigger on a Salesforce object; here we fire it via the command below. Because the watched object is a Skilljar managed-package object that isn't installed, the realized batch is empty.

## Run it
```bash
cd ~/Desktop
python3 test_sandbox/run.py 131400470 --live --trace
```
**Expect:** `status: completed`; a `google_sheets::add_row_v4_bulk` side-effect (mocked). No SF changes.

## To make it write for real
Would need the **Skilljar managed package** installed (for the trigger object) **and** a live Google Sheets connector. Both out of scope (managed package can't be created via API).

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **trigger batch size:** (expect 0) &nbsp; **sheets side-effect seen?:** ☐ &nbsp; **Notes:**
