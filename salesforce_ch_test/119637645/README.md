# Recipe `119637645` — create Partner/Customer accounts (PARTIALLY provisionable)

**Mode:** WRITE (update/create Account) &nbsp;|&nbsp; **Trigger:** `salesforce::new_outbound_message` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** corporate_api, slack_bot

> **Status:** ❌ errors today. The **Account writes are provisionable** (custom fields), but it
> also creates **`AccountTeamMember`**, which requires the **Account Teams** feature enabled in
> **Setup** (not API-creatable) — a partial hard blocker. Largest recipe in the set (65 steps).

## What it does
Triggered by an outbound message when `Create_Partner_account__c` or `Create_Customer_account__c`
is set: looks up the Account + user details, dedupes against similar accounts, then **creates a
Partner or Customer Account** (and an `AccountTeamMember`), unchecks the flags, and **notifies Slack**.

## How it's triggered
`new_outbound_message` (a Salesforce Outbound Message / workflow). Here we realize a watched Account record as the trigger (or supply one via `--input`).

## Run it (today → expect error)
```bash
cd ~/Desktop
python3 test_sandbox/run.py 119637645 --live --trace
```
**Expect today:** `status: error` — missing Account custom fields, then `AccountTeamMember`.

## What it needs to actually write
- **Provisionable:** ~44 `Account` custom fields (`Cat_*`, `Billing_Contact_*`, `Create_Partner_Account__c`, …) as Text + FLS — these would let the Account create/update steps run.
- **Hard blocker:** `AccountTeamMember` needs **Setup → Account Teams enabled** (can't be done via API). So the team-member create step can't run here.
- corporate_api + slack_bot stay mocked (slack would post if we routed it).

So this one is **partially** doable: Account writes yes, the team-member step no. Worth it only if you accept that gap.

## Results (fill in)
- **Date run:** &nbsp; **status (pre-provision):** &nbsp; **first blocking error:** &nbsp; **decision (provision Account fields? accept AccountTeamMember gap?):** &nbsp; **Notes:**
