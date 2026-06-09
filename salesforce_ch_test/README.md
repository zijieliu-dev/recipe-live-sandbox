# Salesforce Challenge — Live Test Set (manual, one-by-one)

Recipes from `salesforce_recipes_challenge/`, run **one at a time** against the real
org (`my-dev-org`). **Salesforce calls hit the live API**; every other connector
(lookup_table, google_sheets, snowflake, variables, …) is **mocked**.

Unlike `stage1_test/` (fully automated), here **you run each recipe yourself**,
observe the real effect, and fill in that recipe's `README.md` results section.

---

## Runnable recipes (in suggested order)

Only recipes that **run without error in this org** are included. Each links to its
own folder with step-by-step guidance.

| # | recipe | what you'll observe | live SF effect |
|---|--------|---------------------|----------------|
| 1 | **120326127** | a real **Chatter post** on an Account feed | ✅ write (Chatter) |
| 2 | 109658662 | reads ProjectShares, branch, stops | read-only |
| 3 | 118326803 | CDC loop + variable updates, stops | read-only |
| 4 | 131400470 | google_sheets bulk add (mocked) | none (mocked) |
| 5 | 87092508 | snowflake sync (mocked) | none (mocked) |

**Start with #1** — it's the only one with a clearly observable real write.

## Excluded (cannot run in a vanilla dev org)

These error because they need schema this org doesn't have and **can't be created
via API** (managed packages / standard features), so they're left out for now:

| recipe | needs |
|--------|-------|
| 112341037 | `OpportunitySplit` / Team-Selling feature (Setup toggle) |
| 119741820 | `skilljar__` managed package |
| 64106452  | `Workato_User__c` custom object (creatable later) |
| 62905310  | missing Account/Opportunity custom fields (creatable later) |
| 119637645 | Account custom fields + a missing record (partially creatable) |

*(The last three could be unblocked by a future `setup_sf_schema.py` provisioner;
they're excluded here because they don't run today.)*

---

## Workflow for each recipe

```bash
cd ~/Desktop
python3 test_sandbox/run.py <recipe-id> --live --trace
```
1. Read `status` and `side_effects` in the JSON output.
2. Check the real effect where it lands (Salesforce record/Chatter, etc.).
3. Open `salesforce_ch_test/<recipe-id>/README.md` and fill in the **Results** section.

Auth uses the Salesforce CLI (`sf`), target org `my-dev-org`.
