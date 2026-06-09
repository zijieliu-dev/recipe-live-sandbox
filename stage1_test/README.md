# Stage 1 — Live Salesforce Test Set

This folder holds **10 Workato recipes** chosen from the corpus, each run **against
a real Salesforce org** (`my-dev-org`). Salesforce calls hit the **live API**;
every other connector (Slack, Snowflake, variables, …) is **simulated**.

Each recipe is tested with **10 input samples** that use **real org data**
(real field values for queries, real seeded record ids for writes). After every
sample, all writes are **undone** so the org is left exactly as it started.

---

## What's in each recipe folder — `stage1_test/<recipe-id>/`

| File | What it contains |
|------|------------------|
| `recipe.md` | The recipe spec: how it's triggered, which Salesforce operation it does, on which object, its branch conditions, and the full step-by-step workflow. |
| `test_samples.md` | The **10 input samples** actually fed to the recipe — each with the real org values / seeded ids used, plus a note saying where each value came from. |
| `results.md` | The **outcome of each sample** run live: completed/error, how many real Salesforce rows were read, how many writes were made (and undone), and any formula errors. |

---

## How to read `results.md` (example)

```
| sample | status    | live SF rows read | writes (undone) | formula errs |
|   1    | completed |        [1]        |        0        |      0       |
```
- **status** — did the recipe run to the end (`completed`) or fail.
- **live SF rows read** — rows the recipe actually pulled from the live org.
- **writes (undone)** — real create/update/delete calls made, all reversed by teardown.

---

## How to reproduce

From `~/Desktop`:

```bash
# 1. confirm Salesforce connectivity + see the org schema
python3 test_sandbox/sf_check.py

# 2. (re)generate recipe.md specs for the 10 selected recipes
python3 test_sandbox/live/gen_stage1.py

# 3. run all 10 recipes x 10 live samples; writes test_samples.md + results.md
python3 test_sandbox/live/run_stage1.py
```

Authentication uses the Salesforce CLI (`sf`); the target org is `my-dev-org`.

---

## How it works (the pipeline, in plain steps)

For each recipe, and each of its 10 samples:

1. **Authenticate** to Salesforce using the CLI session (`sf org display`).
2. **Wrap** the Salesforce client in a *change tracker* that records every write.
3. **Realize the input with real data:**
   - if the recipe **writes** to a record (update/delete), **create a real target
     record** first and use its real id;
   - if the recipe **queries**, fetch a **real value** from the org to filter on
     (e.g. an Account named “Edge…” → filter `"Edg"`);
   - if there's no real value to copy, use a **business-realistic** value
     (real-looking names, emails, addresses, dates, amounts).
4. **Run the recipe.** Salesforce steps make **real REST calls**
   (query / create / update / delete / describe); all other connectors are simulated.
5. **Teardown** — reverse every write: delete created records, restore updated
   fields. The org returns to its starting state.
6. **Record** the realized inputs into `test_samples.md` and the outcome into
   `results.md`.

A residue check (`COUNT()` on each object) after the run confirms the org is
back to baseline — so every sample starts from the same state.

---

## What is real vs. synthetic

- **Real:** authentication, all reads (real rows from your org), the deletes
  (a real record is created then really deleted), the updates (a real record is
  really PATCHed), and the teardown/restore.
- **Synthetic-but-valid:** the *values* written into create/update fields when the
  org has no real value to copy (e.g. a brand-new record's fields) — these are
  realistic and type-valid, not real business data.

---

## The 10 recipes

| recipe id | Salesforce function | object | triggered by |
|-----------|--------------------|--------|--------------|
| 93505634  | DELETE              | Event       | API request |
| 123607383 | UPDATE              | Contract    | Genie workflow |
| 103802560 | SCHEMA (describe)   | Account     | Slack command |
| 107245910 | TRIGGER (new record)| OpportunityFieldHistory | Salesforce |
| 123586145 | adhoc HTTP          | (SOQL)      | scheduled |
| 107245434 | QUERY               | Account     | Slack menu |
| 117979300 | QUERY               | Opportunity | Slack menu |
| 110408597 | QUERY               | User        | recipe function |
| 110430106 | QUERY               | Period      | scheduled SF query |
| 112244779 | QUERY (SOQL v2)     | (SOQL)      | recipe-ops action |
