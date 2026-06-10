# Recipe `119741820` — process combined attachment (BLOCKED: managed package)

**Mode:** WRITE (update Account) &nbsp;|&nbsp; **Trigger:** `salesforce::new_custom_object_webhook` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** py_eval

> **Status:** ❌ **blocked** — the trigger watches **`LinkSquares__Agreement__c`** (LinkSquares
> managed package), which isn't installed and **can't be created via API**.

## What it does
On a new `LinkSquares__Agreement__c` (webhook): run a SOQL, pull a combined attachment, run a Python
snippet over it (`py_eval`, mocked), build a list, and **update Account** records in a loop.

## How it's triggered
`new_custom_object_webhook` on `LinkSquares__Agreement__c`. That object doesn't exist here, so the
trigger can't realize a real record → the run errors/empties early.

## Run it (to confirm the block)
```bash
cd ~/Desktop
python3 test_sandbox/run.py 119741820 --live --trace
```
**Expect:** `status: error` (or empty trigger) — the `LinkSquares__Agreement__c` object is absent.

## Why it can't write here
`LinkSquares__Agreement__c` is **managed-package** schema (LinkSquares). It requires installing that
package; it can't be created via the Metadata/Tooling API. Out of scope for a vanilla dev org.
*(Note: the `update_sobject` target is the standard `Account`, so if the trigger object existed and
returned data, the Account update itself would be runnable — but the trigger object is the blocker.)*

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **error reason:** &nbsp; **Conclusion:** blocked by `LinkSquares__` package ☐ &nbsp; **Notes:**
