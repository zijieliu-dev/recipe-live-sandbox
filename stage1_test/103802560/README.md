# Recipe #3 — `103802560` · Describe Account Schema (READ-only)

**Trigger event:** a **Slack slash-command** (`slack_bot::bot_command_v2`). When a user runs the command, the recipe fetches the **Account object's field schema** from Salesforce and (mocked) posts/cleans up a Slack message.

**Salesforce function:** `get_sobject_schema` on **Account** → a *metadata read* (`GET /sobjects/Account/describe`). **No rows are created, updated, or deleted.**

---

## Logic Flow (steps)

| # | step | meaning |
|---|------|---------|
| 1 | `trigger slack_bot::bot_command_v2` | a Slack command fires the recipe |
| 2 | `action salesforce::get_sobject_schema` (`sobject_name: Account`) | **describe Account** → returns its field list |
| 3 | `action byin_…recipe_ops…::connection_required_acknowledge_process_event` | recipe-ops internal ack (mocked) |
| 4 | `action slack_bot::delete_message` | clean up the Slack message (mocked) |

Only step 2 touches Salesforce, and it only **reads metadata**.

---

## Initialize Database Snapshot
**Not required.** This recipe reads Account *metadata* (field definitions), not rows — nothing to seed or restore. The init DB (`Event`/`Contract`) is irrelevant here.

## Verify Pre-Execution State (optional)
The "state" this recipe reads is the Account schema, which always exists:
```bash
sf sobject describe --target-org my-dev-org --sobject Account | python3 -c "import sys,json;print('Account fields:',len(json.load(sys.stdin)['fields']))"
```
Expectation: **70 fields** (e.g. `Id, Name, Type, ParentId, …`).

## Execute Logic Flow
Fire the recipe live (Salesforce real, other connectors mocked):
```bash
python3 test_sandbox/run.py 103802560 --live --sample 0
```

**Execution Result Snapshot:**
```json
{
  "id": "103802560",
  "status": "completed",
  "steps": 4,
  "side_effects": [
    { "provider": "salesforce", "operation": "get_sobject_schema",
      "data": { "sobject": "Account", "field_count": 70 } },
    { "provider": "byin_workato_recipe_ops_connector_3165546_1699532902",
      "operation": "connection_required_acknowledge_process_event" },
    { "provider": "slack_bot", "operation": "delete_message" }
  ],
  "formula_errors": [],
  "sample": 0,
  "trigger_fired": {}
}
```
The **first** side-effect is the live describe (step 2): `get_sobject_schema → Account, field_count: 70` — direct proof step 2 executed against the org and pulled the real Account schema (70 fields). The other two are the mocked recipe-ops + Slack steps. `status: completed` confirms the run succeeded.

**Cross-check that 70 is your org's real schema:**
```bash
sf sobject describe --target-org my-dev-org --sobject Account | python3 -c "import sys,json;print(len(json.load(sys.stdin)['fields']),'fields')"
```
→ `70 fields` (add a custom field to Account and both numbers become 71 — confirming it's live, not cached).

## Confirm Resulting State (optional)
**No state change** — this is a read. Row counts are identical before and after:
```bash
sf data query --target-org my-dev-org --query "SELECT COUNT() FROM Account"   # unchanged (16)
```

## Environment Recovery
**Not needed.** Nothing was written, so there is nothing to undo. `--reset` is a no-op here, and `recover_init_db.py` is unnecessary.

---

### Notes
- `trigger_fired` is `{}` because the recipe does not read any field off the Slack command for the describe — it always describes `Account`.
- This recipe verifies the **read path** end-to-end against the live org (real `describe`), with zero side effects on data.
- **vs. recipe #1/#2:** those mutate (delete/update) and need recovery; recipes #3–#10 are reads and do not.


- Step 3 — …recipe_ops…::connection_required_acknowledge_process_event: an internal Workato recipe-ops housekeeping/acknowledgement call (bookkeeping the recipe-ops platform does).
- Step 4 — slack_bot::delete_message: deletes the Slack message (UI cleanup after the command).

How "mocked" works: in our sandbox, only salesforce goes to the real API; every other connector is mocked. The dispatcher routes them to a generic handler
(comps/_default.py) that doesn't actually call Slack or recipe-ops — it just records the call and returns fake output:
def default_handle(provider, operation, inp, ctx):
    ctx.log_side_effect(provider, operation, input=inp)   # 1) record "this WOULD have been called"
    schema = ctx.current_output_schema
    return fabricate.fabricate(schema, ...) if schema else {}   # 2) return fabricated output
So for step 4, no real Slack message is deleted — the sandbox logs {provider: slack_bot, operation: delete_message, input: …} and hands back a fake result so the
recipe can continue. Same for step 3.

That's exactly what you see in the result snapshot: those two entries under side_effects are the records of the mocked calls (provider + operation), not real
actions:
"side_effects": [
{ "provider": "byin_…recipe_ops…", "operation": "connection_required_acknowledge_process_event" },
{ "provider": "slack_bot", "operation": "delete_message" }
]

So: Salesforce step 2 = real (live describe); steps 3 & 4 = mocked (logged + fake output, no real Slack/recipe-ops call). The side_effects list is the sandbox's
record of every connector the recipe tried to call.