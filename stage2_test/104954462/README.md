# Recipe `104954462` — untick Credit Hold (LIVE Salesforce **+** Slack, one recipe)

**Connectors:** Salesforce **and** Slack (both live, in a single recipe) &nbsp;|&nbsp; **Trigger:** `slack_bot::bot_command_v2` (`/financebot untick_credit_hold`)

> The one recipe that exercises **two live connectors at once**: a Slack bot command drives a
> Salesforce write, then posts a Slack confirmation.

## What it does
1. **Trigger** — a Slack bot command (`untick_credit_hold`) carrying an `accountid`.
2. **`salesforce::search_sobjects`** — find the Account where `Credit_Hold__c = true AND Id = <accountid>`. (live SF read)
3. **`salesforce::update_sobject`** — set `Credit_Hold__c = false` on that Account. (live SF write)
4. **`slack_bot::post_bot_message`** — post a confirmation to the command's channel. (live Slack)

## One-time setup (org schema; sandbox code unchanged)
`Credit_Hold__c` doesn't exist in a vanilla org, so it was provisioned (Metadata deploy + FLS):
- **`Account.Credit_Hold__c`** (Checkbox) + FLS via `Sandbox_Recipe_Access`
- Seeded `Edge Communications` (`001g500000MKbA2AAL`) with `Credit_Hold__c = true`

One general handler fix was also needed (committed): `live/salesforce.py:_lit` now emits a SOQL
**boolean** for `"true"/"false"` filter values (`Credit_Hold__c = true`, not `= 'true'`) — any
checkbox filter needs this.

## Input supplied
```json
{ "trigger": { "parameters": { "accountid": "001g500000MKbA2AAL" }, "context": { "channel": "C0B95EM1PC1" } } }
```

## Run command
```bash
cd ~/Desktop
python3 test_sandbox/run.py 104954462 --live --diff --input /tmp/s2_ch.json
```

## Live result ✅
- `status: completed`. Two live calls **in one recipe**:
  - `salesforce::update_sobject` → `Credit_Hold__c: True → false` (shown by `--diff`)
  - `slack_bot::post_bot_message` → `ok: true`, `ts: 1781052243.809779` (to `#sandbox`)
- Verified: Edge Communications `Credit_Hold__c` is now `false` (the recipe unticked it).

**Proves:** the sandbox runs a recipe that spans **Salesforce + Slack live together** — a real SF
update *and* a real Slack post, from a single bot-command trigger.

## Results (fill in)
- **Date run:** &nbsp; **status:** &nbsp; **SF write (Credit_Hold__c → ):** &nbsp; **Slack ok / ts:** &nbsp; **Notes:**
