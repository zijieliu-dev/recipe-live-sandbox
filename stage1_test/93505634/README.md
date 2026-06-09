
# Recipe `93505634` — DELETE on Event

**Mode:** WRITE (mutates org) | **SF operation(s):** delete_sobject | **triggered by:** `workato_api_platform::receive_request`

## How each run is reset (isolation)

A **persistent init database** lives in the org as the baseline (seeded once via `setup_init_db.py`): 10 Event rows + 10 Contract rows, alongside the existing Account/Contact/Opportunity data. **Every trial starts from this same init state.**

Each Salesforce write is recorded by a change-tracker; after the trial it is reversed so the init database is put back:

- a **deleted** init row → re-created from its snapshot (same data)
- an **updated** init row → its fields restored
- anything the recipe **created** → deleted

So the init table returns to its full row count and the next trial starts from the identical state.

## Input → Output, per sample (operates on the init table)

### Sample 1 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDztEAE"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDztEAE` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-01-15T10:00:00.000+0000", `ActivityDate`="2026-01-15", `DurationInMinutes`=1, `StartDateTime`="2026-01-15T10:00:00.000+0000", `EndDateTime`="2026-01-15T10:01:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 2 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDTdEAM"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDTdEAM` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-02-10T10:00:00.000+0000", `ActivityDate`="2026-02-10", `DurationInMinutes`=2, `StartDateTime`="2026-02-10T10:00:00.000+0000", `EndDateTime`="2026-02-10T10:02:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 3 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDVFEA2"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDVFEA2` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-03-05T10:00:00.000+0000", `ActivityDate`="2026-03-05", `DurationInMinutes`=3, `StartDateTime`="2026-03-05T10:00:00.000+0000", `EndDateTime`="2026-03-05T10:03:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 4 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dE37EAE"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dE37EAE` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-04-20T10:00:00.000+0000", `ActivityDate`="2026-04-20", `DurationInMinutes`=4, `StartDateTime`="2026-04-20T10:00:00.000+0000", `EndDateTime`="2026-04-20T10:04:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 5 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDYTEA2"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDYTEA2` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-05-12T10:00:00.000+0000", `ActivityDate`="2026-05-12", `DurationInMinutes`=5, `StartDateTime`="2026-05-12T10:00:00.000+0000", `EndDateTime`="2026-05-12T10:05:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 6 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDa5EAE"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDa5EAE` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-06-08T10:00:00.000+0000", `ActivityDate`="2026-06-08", `DurationInMinutes`=6, `StartDateTime`="2026-06-08T10:00:00.000+0000", `EndDateTime`="2026-06-08T10:06:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 7 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDbhEAE"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDbhEAE` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-07-22T10:00:00.000+0000", `ActivityDate`="2026-07-22", `DurationInMinutes`=7, `StartDateTime`="2026-07-22T10:00:00.000+0000", `EndDateTime`="2026-07-22T10:07:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 8 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDdJEAU"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDdJEAU` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-08-30T10:00:00.000+0000", `ActivityDate`="2026-08-30", `DurationInMinutes`=8, `StartDateTime`="2026-08-30T10:00:00.000+0000", `EndDateTime`="2026-08-30T10:08:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 9 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dE1VEAU"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dE1VEAU` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-09-14T10:00:00.000+0000", `ActivityDate`="2026-09-14", `DurationInMinutes`=9, `StartDateTime`="2026-09-14T10:00:00.000+0000", `EndDateTime`="2026-09-14T10:09:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

### Sample 10 — `completed`
- **Input (trigger):** `{"request": {"Id": "00Ug5000000dDevEAE"}}`
- **Init table:** `Event` has **10 rows** (baseline)
- **Targeted row `00Ug5000000dDevEAE` BEFORE:** `IsAllDayEvent`=false, `ActivityDateTime`="2026-10-03T10:00:00.000+0000", `ActivityDate`="2026-10-03", `DurationInMinutes`=10, `StartDateTime`="2026-10-03T10:00:00.000+0000", `EndDateTime`="2026-10-03T10:10:00.000+0000", …
- **AFTER recipe:** row **DELETED via live API** ✅ → table now **9 rows**
- **Reset:** 1 write(s) reversed → init table restored to **10 rows**

