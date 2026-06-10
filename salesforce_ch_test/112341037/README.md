# Recipe `112341037` — set opportunity splits for partner managers (BLOCKED: Setup feature)

**Mode:** WRITE (create/update) &nbsp;|&nbsp; **Trigger:** `salesforce::new_platform_event` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** (none)

> **Status:** ❌ **blocked** — writes to **`OpportunitySplit`** / reads **`OpportunityTeamMember`**,
> which only exist when **Opportunity Splits + Team Selling** are enabled in **Setup**. These are
> standard-feature toggles, **not API-creatable**.

## What it does
On a platform event: find the Opportunity's partner managers and owner; if one is a GSI partner
manager (and not the only one), loop the team and **create/update `OpportunitySplit` records** to
set split percentages (e.g. GSI partner manager → 0%).

## How it's triggered
`new_platform_event`. The event part is fine, but the work targets `OpportunitySplit` /
`OpportunityTeamMember`, which aren't available unless the features are turned on.

## Run it (to confirm the block)
```bash
cd ~/Desktop
python3 test_sandbox/run.py 112341037 --live --trace
```
**Expect:** `status: error` — `sObject type 'OpportunitySplit' is not supported` / not accessible.

## Why it can't write here
`OpportunitySplit` and `OpportunityTeamMember` are gated behind **Setup → Opportunity Splits** and
**Team Selling**. Enabling them is a manual admin action in the Salesforce UI — not something the
Metadata/Tooling API creates. *(If you enabled those features in Setup, this recipe would then be
runnable — no custom schema needed.)*

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **error reason:** &nbsp; **Conclusion:** blocked by Opportunity Splits / Team Selling feature ☐ &nbsp; **Decision (enable in Setup?):** &nbsp; **Notes:**
