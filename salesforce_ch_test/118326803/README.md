# Recipe `118326803` — cancel Resource Requests on Opportunity change (BLOCKED: managed package)

**Mode:** WRITE (update) &nbsp;|&nbsp; **Trigger:** `salesforce::change_data_capture` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** (none)

> **Status:** ❌ **blocked** — operates on **`pse__Resource_Request__c`** (Certinia/FinancialForce
> PSA managed package), which isn't installed and **can't be created via API**.

## What it does
On a changed Opportunity (CDC): retrieve all `pse__Resource_Request__c` for the Opp; if none, stop;
otherwise loop them, adjust start dates that fall on a weekend (via variables), and **update each
Resource Request's Status to "Cancelled."**

## How it's triggered
`change_data_capture` on Opportunity. The Opportunity part is fine (standard object), but the records
it acts on (`pse__Resource_Request__c`) don't exist here, so `get_related` returns nothing → it stops.

## Run it (to confirm the block)
```bash
cd ~/Desktop
python3 test_sandbox/run.py 118326803 --live --trace
```
**Expect:** `status: stopped` — no Resource Requests found (the managed object is absent), so the "nothing to do → stop" branch runs.

## Why it can't write here
`pse__Resource_Request__c` is **managed-package** schema (FinancialForce/Certinia PSA). It only
exists if the package is installed; it can't be scripted via the API. Out of scope for a vanilla org.

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **resource requests found:** (expect 0) &nbsp; **Conclusion:** blocked by `pse__` package ☐ &nbsp; **Notes:**
