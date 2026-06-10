# Recipe `64106452` — composite UPDATE on a custom object (provisioned + engine-supported)

**Mode:** WRITE (bulk update) &nbsp;|&nbsp; **Trigger:** `salesforce::scheduled_sobject_soql_query` &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** (none)

> This is a **real challenge-folder recipe** made to write end-to-end. Unlike the
> earlier ones, it needed both **schema provisioning** (a custom object your org
> lacked) **and** new **sandbox-engine support** (batch trigger + composite update).

## What it does
1. **Trigger** — scheduled SOQL on `Workato_User__c` for rows whose
   `Lead__r.ConvertedContactId != null` (i.e. linked to a converted Lead).
2. **`composite_update_sobject`** — for each matching row, set
   `Account__c` = the Lead's `ConvertedAccountId` and `Contact__c` = its `ConvertedContactId`.

---

## One-time setup (already done — documents how to reproduce)

`Workato_User__c` doesn't exist in a vanilla org, so we provisioned it. **Schema is a
permanent baseline (created once); only the *rows* reset per trial.**

1. **Create the custom object + lookups** via Metadata API (Tooling API can't create objects):
   ```bash
   # /tmp/sfdeploy/force-app/.../objects/Workato_User__c/  (object + Lead__c/Account__c/Contact__c lookups)
   sf project deploy start --source-dir force-app --target-org my-dev-org
   ```
2. **Grant access** (the deploy doesn't auto-grant FLS to your user) via the
   `Sandbox_Recipe_Access` permission set: `ObjectPermissions` on `Workato_User__c` +
   `FieldPermissions` on the 3 lookups (inserted via the REST API).
3. **Seed data**: convert a Lead (Apex `Database.convertLead` via `executeAnonymous`), then
   create one `Workato_User__c` row with `Lead__c` → that converted Lead, `Account__c`/`Contact__c` empty.

## Engine support added (so the recipe could run)
- `live/realize.py` — `scheduled_sobject_soql_query` triggers now **run the real query** with
  the relationship `field_list` (`Lead__r$Lead.Field` → `Lead__r.Field`) and return `{sobject: [rows]}`.
- `engine/interpreter.py` — `resolve_input` expands the `____source` + `current_item`
  **list-map** (composite ops) into one record per source row.
- `live/salesforce.py` — `composite_create/update_sobject` are handled as **per-record bulk writes**.

---

## Steps (per trial)

### Step 1 — BEFORE: the seeded row (Account__c / Contact__c empty)
```bash
cd ~/Desktop
python3 -c "
import sys; sys.path.insert(0,'/Users/jesseliu/Desktop')
from test_sandbox.salesforce_live import SalesforceClient
c=SalesforceClient.from_cli('my-dev-org')
print(c.query_all('SELECT Id, Account__c, Contact__c FROM Workato_User__c'))
"
```
Baseline: `Account__c=None, Contact__c=None`.

jesseliu@mac Desktop % cd ~/Desktop
python3 -c "
import sys; sys.path.insert(0,'/Users/jesseliu/Desktop')
from test_sandbox.salesforce_live import SalesforceClient
c=SalesforceClient.from_cli('my-dev-org')
print(c.query_all('SELECT Id, Account__c, Contact__c FROM Workato_User__c'))
"
[{'attributes': {'type': 'Workato_User__c', 'url': '/services/data/v59.0/sobjects/Workato_User__c/a07g500000SZLO7AAP'}, 'Id': 'a07g500000SZLO7AAP', 'Account__c': None, 'Contact__c': None}]


### Step 2 — run the recipe live (trigger realizes the batch from the real query)
```bash
python3 test_sandbox/run.py 64106452 --live --trace
```

Expect `status: completed` and a `salesforce::composite_update_sobject` side-effect with `count=1`.
{
  "id": "64106452",
  "status": "completed",
  "steps": 2,
  "side_effects": [
    {
      "provider": "salesforce",
      "operation": "composite_update_sobject",
      "data": {
        "sobject": "Workato_User__c",
        "count": 1,
        "records": [
          {
            "id": "a07g500000SZLO7AAP",
            "success": true
          }
        ]
      }
    }
  ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {
    "Workato_User__c": [
      {
        "Id": "a07g500000SZLO7AAP",
        "Lead__r": {
          "attributes": {
            "type": "Lead",
            "url": "/services/data/v59.0/sobjects/Lead/00Qg5000003yWg2EAE"
          },
          "ConvertedContactId": "003g500000KplMpAAJ",
          "ConvertedAccountId": "001g500000QeVjNAAV"
        }
      }
    ],
    "records": [
      {
        "Id": "a07g500000SZLO7AAP",
        "Lead__r": {
          "attributes": {
            "type": "Lead",
            "url": "/services/data/v59.0/sobjects/Lead/00Qg5000003yWg2EAE"
          },
          "ConvertedContactId": "003g500000KplMpAAJ",
          "ConvertedAccountId": "001g500000QeVjNAAV"
        }
      }
    ],
    "count": 1
  },
  "trace": [
    {
      "step": 1,
      "keyword": "trigger",
      "provider": "salesforce",
      "name": "scheduled_sobject_soql_query",
      "alias": "353a3b26"
    },
    {
      "step": 2,
      "keyword": "action",
      "provider": "salesforce",
      "name": "composite_update_sobject",
      "alias": "331ac97f"
    }
  ]
}

### Step 3 — AFTER: the row now points at the converted Lead's Account/Contact
```bash
python3 -c "
import sys; sys.path.insert(0,'/Users/jesseliu/Desktop')
from test_sandbox.salesforce_live import SalesforceClient
c=SalesforceClient.from_cli('my-dev-org')
print(c.query_all('SELECT Id, Account__c, Contact__c FROM Workato_User__c'))
"
```
Expect `Account__c` and `Contact__c` now populated (the converted Lead's `ConvertedAccountId` / `ConvertedContactId`). 

jesseliu@mac Desktop % python3 -c "
import sys; sys.path.insert(0,'/Users/jesseliu/Desktop')
from test_sandbox.salesforce_live import SalesforceClient
c=SalesforceClient.from_cli('my-dev-org')
print(c.query_all('SELECT Id, Account__c, Contact__c FROM Workato_User__c'))
"
[{'attributes': {'type': 'Workato_User__c', 'url': '/services/data/v59.0/sobjects/Workato_User__c/a07g500000SZLO7AAP'}, 'Id': 'a07g500000SZLO7AAP', 'Account__c': '001g500000QeVjNAAV', 'Contact__c': '003g500000KplMpAAJ'}]


### Step 4 — reset the row for the next trial (schema stays, data resets)
```bash
python3 -c "
import sys; sys.path.insert(0,'/Users/jesseliu/Desktop')
from test_sandbox.salesforce_live import SalesforceClient
c=SalesforceClient.from_cli('my-dev-org')
c.update('Workato_User__c','a07g500000SZLO7AAP',{'Account__c':None,'Contact__c':None})
print('reset ->', c.query_all('SELECT Id, Account__c, Contact__c FROM Workato_User__c'))
"
```
reset -> [{'attributes': {'type': 'Workato_User__c', 'url': '/services/data/v59.0/sobjects/Workato_User__c/a07g500000SZLO7AAP'}, 'Id': 'a07g500000SZLO7AAP', 'Account__c': None, 'Contact__c': None}]

---

## Results (fill in after you run it)

- **Date run:**
- **BEFORE** — Account__c / Contact__c:
- **run status:**
- **composite_update side-effect** (count / record id):
- **AFTER** — Account__c / Contact__c:
- **Match the converted Lead's ids?** ☐ yes ☐ no
- **Reset for next trial?** ☐ yes
- **Notes:**
