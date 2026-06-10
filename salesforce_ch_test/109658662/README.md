# Recipe `109658662` — share project + create tasks on new assignment (BLOCKED: managed package)

**Mode:** WRITE (create) &nbsp;|&nbsp; **Trigger:** `salesforce::new_custom_object` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** slack_bot

> **Status:** ❌ **blocked** — depends on the **`pse__` (Certinia / FinancialForce PSA) managed
> package** objects (`pse__Assignment__c`, `pse__Proj__Share`, `pse__Project_Task__Share`) that
> aren't installed here and **can't be created via API**. Can't write in a vanilla org.

## What it does
"Run for every new assignment where an external resource is being assigned": check existing
`ProjectShare`s, create one if missing (share the project), look at tasks, create task records,
and notify Slack. (On a no-share branch it stops early.)

## How it's triggered
`new_custom_object` on a `pse__` object. Since that object isn't installed, the trigger realizes empty and the recipe stops early (or the create steps error).

## Run it (to confirm the block)
```bash
cd ~/Desktop
python3 test_sandbox/run.py 109658662 --live --trace
```
**Expect:** `status: stopped` or `error` — it can't create the `pse__Project_Task__Share` / `pse__Proj__Share` records.

## Why it can't write here
`pse__*` objects belong to the **FinancialForce/Certinia PSA managed package**. Managed-package
schema only exists if you **install the package** — it cannot be scripted/created via the Metadata
or Tooling API. So this recipe is out of scope for a vanilla dev org.

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **error/stop reason:** &nbsp; **Conclusion:** blocked by `pse__` package ☐ confirmed &nbsp; **Notes:**
