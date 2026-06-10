# Recipe `62905310` — embedded-account opportunity reorg (✅ WRITES, provisioned + engine-supported)

**Mode:** WRITE (upsert/update) &nbsp;|&nbsp; **Trigger:** `salesforce::new_platform_event` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** (none)

> **Status:** ✅ the **second challenge-folder recipe** made to write end-to-end. It mutates
> **real standard objects** (Account/Opportunity), so run it with `--reset` to auto-restore.

## What it does
On a platform event carrying an Opportunity Id (`Opportunity_ID__c`): load the Opp; if its Account
isn't already an "… - Embedded" account, **upsert** an "`<Account> - Embedded`" Account and **move
the Opportunity** (and its primary contact / CS tasks) onto it. A data-reorganization recipe.

## How it's triggered
`new_platform_event`. Real Workato fires it when a platform event is published; here we supply the
event payload via `--input` (just the `Opportunity_ID__c`).

---

## One-time setup (already done — documents how to reproduce)
`Workato_Task__c` and several custom fields don't exist in a vanilla org. Provisioned via Metadata
deploy + FLS (schema is permanent baseline; data resets per trial):
- **Custom object** `Workato_Task__c` + lookups `Account__c → Account`, `Opportunity__c → Opportunity`
- **Opportunity** fields: `Opportunity_ID__c` (Text), `Subscribed_Plan_Type__c` (Text), `Primary_Contact__c` (Lookup → Contact)
- **User** field: `Sales_Team__c` (Text) — referenced as `Owner.Sales_Team__c`
- **Contact** field: `Primary_Contact__c` (Text)
- FLS for all of the above via the `Sandbox_Recipe_Access` permission set

## Engine/handler fixes this recipe required (all reusable)
- `live/salesforce.py`: `table_list_custom` is a reserved key (not a WHERE filter); `field_list`
  relationship notation (`Account$Label.Name` → `Account.Name`) is parsed; `upsert_sobject` does
  **match-by-field → update-or-create** (handles `query_field={"primary_key":"Name"}`, non-external-id keys).
- `engine/formula.py`: tokenizer skips Ruby `#` line comments (a field formula had a trailing `#…`).
- `engine/refs.py`: `current_item` with no foreach scope falls back to the **first** list element (Workato default).

---

## Steps (per trial)

### Step 1 — build the platform-event payload (a real Opportunity Id)
```bash
cd ~/Desktop
cat > /tmp/pe62.json <<'EOF'
{ "trigger": { "Opportunity_ID__c": "006g5000003ukwDAAQ" } }
EOF
```
*(`006g5000003ukwDAAQ` = the "Edge Emergency Generator" opp on "Edge Communications".)*

### Step 2 — run live with `--reset` (writes are real; restored after)
```bash
python3 test_sandbox/run.py 62905310 --live --reset --input /tmp/pe62.json --trace
```
**Expect:** `status: completed`, `formula_errors: 0`, and SF side-effects:
`upsert_sobject on Account` (matched=False → creates "Edge Communications - Embedded") and
`update_sobject on Opportunity` (moves the opp to it).

{
  "id": "62905310",
  "status": "completed",
  "steps": 10,
  "side_effects": [
    {
      "provider": "salesforce",
      "operation": "upsert_sobject",
      "data": {
        "sobject": "Account",
        "matched": false,
        "data": {
          "Name": "Edge Communications - Embedded",
          "OwnerId": "005g5000006ezEDAAY",
          "ParentId": "001g500000MKbA2AAL",
          "Website": "http://edgecomm.com"
        }
      }
    },
    {
      "provider": "salesforce",
      "operation": "update_sobject",
      "data": {
        "sobject": "Opportunity",
        "id": "006g5000003ukwDAAQ",
        "data": {
          "AccountId": "001g500000QgHK1AAN"
        }
      }
    }
  ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {
    "Opportunity_ID__c": "006g5000003ukwDAAQ"
  },
  "trace": [
    {
      "step": 1,
      "keyword": "trigger",
      "provider": "salesforce",
      "name": "new_platform_event",
      "alias": "e3bacc47"
    },
    {
      "step": 2,
      "keyword": "action",
      "provider": "salesforce",
      "name": "search_sobjects",
      "alias": "85ba156e"
    },
    {
      "step": 3,
      "keyword": "if",
      "taken": false
    },
    {
      "step": 5,
      "keyword": "action",
      "provider": "salesforce",
      "name": "search_sobjects_soql",
      "alias": "3abac461"
    },
    {
      "step": 6,
      "keyword": "if",
      "taken": true
    },
    {
      "step": 7,
      "keyword": "action",
      "provider": "salesforce",
      "name": "upsert_sobject",
      "alias": "a7af64bc"
    },
    {
      "step": 8,
      "keyword": "action",
      "provider": "salesforce",
      "name": "update_sobject",
      "alias": "4cfb3ee6"
    },
    {
      "step": 9,
      "keyword": "if",
      "taken": false
    },
    {
      "step": 11,
      "keyword": "action",
      "provider": "salesforce",
      "name": "search_sobjects",
      "alias": "1774368a"
    },
    {
      "step": 12,
      "keyword": "if",
      "taken": false
    }
  ]
}

### Step 3 — confirm the org was restored
```bash
python3 -c "
import sys; sys.path.insert(0,'/Users/jesseliu/Desktop')
from test_sandbox.salesforce_live import SalesforceClient
c=SalesforceClient.from_cli('my-dev-org')
print('Opp account:', c.query_all(\"SELECT AccountId, Account.Name FROM Opportunity WHERE Id='006g5000003ukwDAAQ'\"))
print('Embedded accts:', c.query_all(\"SELECT Id FROM Account WHERE Name LIKE '%- Embedded'\") or 'none')
"
```
Expect Opp back on `Edge Communications` and **no** leftover Embedded account.

> Want to *see* the writes persist? Run Step 2 **without** `--reset`, inspect the new Embedded
> account + moved opp, then delete the account / restore the opp's AccountId manually.
Opp account: [{'attributes': {'type': 'Opportunity', 'url': '/services/data/v59.0/sobjects/Opportunity/006g5000003ukwDAAQ'}, 'AccountId': '001g500000MKbA2AAL', 'Account': {'attributes': {'type': 'Account', 'url': '/services/data/v59.0/sobjects/Account/001g500000MKbA2AAL'}, 'Name': 'Edge Communications'}}]
Embedded accts: none

---

## Results (fill in after you run it)
- **Date run:** &nbsp; **status / formula_errors:**
- **SF writes seen:** ☐ upsert Account ☐ update Opportunity
- **Embedded account created (name):**
- **Restored cleanly (`--reset`)?** ☐ Opp back on original account ☐ no leftover Embedded account
- **Notes:**
