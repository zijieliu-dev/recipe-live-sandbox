# Salesforce Challenge — Live Test Set (manual, one-by-one)

Recipes from `salesforce_recipes_challenge/`, run **one at a time** against the real org
(`my-dev-org`). **Salesforce calls hit the live API**; other connectors (Sheets, Snowflake,
py_eval, corporate_api, variables…) are **mocked**. You run each recipe yourself (per its README)
and fill in the **Results** section.

Run pattern: `cd ~/Desktop && python3 test_sandbox/run.py <id> --live --trace`

---

## Status map (all 10 challenge recipes)

| recipe | what it does | status |
|--------|--------------|--------|
| **[64106452](64106452/)** | sync converted-Lead Account/Contact onto `Workato_User__c` | ✅ **writes for real** (provisioned object + engine support) |
| [87092508](87092508/) | scheduled SF query → Snowflake sync | ⚪ runs; write is **mocked** (Snowflake) — no SF effect |
| [131400470](131400470/) | batch trigger → Google Sheets bulk add | ⚪ runs; trigger object missing + write **mocked** (Sheets) |
| [120326127](120326127/) | Chatter post on lost-deal unassignment | 🔴 runs, **no observable effect** (gated on a missing field) |
| **[62905310](62905310/)** | embedded-account opp reorganization | ✅ **writes for real** (provisioned `Workato_Task__c` + fields; upserts Embedded account, moves opp) |
| [119637645](119637645/) | create Partner/Customer accounts + notify | 🟡 partially provisionable (Account fields) but `AccountTeamMember` needs a Setup feature |
| [109658662](109658662/) | share project + create tasks on new assignment | ⛔ blocked — `pse__` (Certinia PSA) managed package |
| [118326803](118326803/) | cancel Resource Requests on Opp change | ⛔ blocked — `pse__` managed package |
| [119741820](119741820/) | process combined attachment | ⛔ blocked — `LinkSquares__` managed package |
| [112341037](112341037/) | set opportunity splits | ⛔ blocked — Opportunity Splits / Team Selling Setup feature |

**Legend:** ✅ writes live · ⚪ runs but write goes to a mocked connector · 🔴 runs, nothing observable · 🟡 can be made to write with provisioning · ⛔ can't run here (managed package / Setup feature, not API-creatable).

### Bottom line
- **2 of 10 write for real today** (`64106452`, `62905310`) — after provisioning their custom
  schema + the engine support (batch triggers, composite ops, relationship field_list,
  match-or-create upsert, Ruby-comment formulas, no-scope `current_item`).
- **2 run but only touch mocked connectors** (Snowflake / Sheets); **1 has no observable effect**.
- **5 are blocked** by managed packages (`pse__`, `LinkSquares__`, `skilljar__`) or Setup features
  (Opportunity Splits / Team Selling, Account Teams) — none of which can be created via API.

---

## Not in the challenge folder (stage1/selected substitutes used to demo the mechanics)
| recipe | op | note |
|--------|----|----|
| [123607383](123607383/) | UPDATE Contract | clean before/after write demo |
| [93505634](93505634/) | DELETE Event | clean before/after delete demo (init DB) |

---

## How a recipe folder is laid out
Each `<id>/README.md` has: what the recipe does, how it's triggered, the run command + expected
outcome, why it's blocked / what it'd take (if applicable), and a **Results** section to fill in
after you run it.
