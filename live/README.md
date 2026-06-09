- setup_init_db.py = the orchestrator — decides what objects & how many (Event:10, Contract:10), checks the current count, and loops.
- seed_record = the worker — creates one valid row of a given object (reads its schema, fills required fields, retries).

## Phrase 0 - Tables Initialization

### BEFORE (empty)
sf data query --target-org my-dev-org --query "SELECT COUNT() FROM Event"

jesseliu@Jesses-MacBook-Pro ~ % sf data query --target-org my-dev-org --query "SELECT COUNT() FROM Event"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.

Total number of records retrieved: 0.
Querying Data... done

### seed the init table (10 Events)
python3 test_sandbox/live/setup_init_db.py

! python3 test_sandbox/live/setup_init_db.py                                                                                                                        
  ⎿  Event      have=0  target=10  seeding=10
                -> Event now has 10 rows (persistent init table)
     Contract   have=0  target=10  seeding=10
                -> Contract now has 10 rows (persistent init table)

jesseliu@Jesses-MacBook-Pro ~ % sf data query --target-org my-dev-org --query "SELECT COUNT() FROM Event"
 ›   Warning: @salesforce/cli update available from 2.134.6 to 2.136.8.

Total number of records retrieved: 10.
Querying Data... done


## Phrase 1 - Building sample

python3 - <<'EOF'
import sys; sys.path.insert(0, '.')
from test_sandbox.engine import loader
from test_sandbox.salesforce_live import SalesforceClient
from test_sandbox.live.realize import realize_trigger

c = SalesforceClient.from_cli("my-dev-org")
r = loader.load("test_sandbox/recipes_clean/93505634.json")["recipe"]
alias = loader.get_trigger(r)["as"]

pool = {
    "Event": [x["Id"] for x in c.query_all("SELECT Id FROM Event LIMIT 200")]
}

trig, notes = realize_trigger(r, c, alias, 0, target_pool=pool)

print("TRIGGER:", trig)
print("NOTES  :", notes)
EOF

Output:
TRIGGER: {'request': {'Id': '00Ug5000000fDe1EAE'}}
NOTES  : ['target row from init table: Event.request.Id = 00Ug5000000fDe1EAE (1 of 10 rows)']

#### What's the difference here?
- Live Workato: the recipe is a deployed endpoint → you fire it with an HTTP request (curl -X POST <url> -d '{"Id":"…"}').
- Local (our sandbox): no server to call

## Phrase 2 - Fire (the CLI orchestration)
Prepare everything needed so Phase 3 can run against Salesforce live
å
    test_sandbox/run.py (--live branch) — what python3 test_sandbox/run.py 93505634 --live does.
    client = SalesforceClient.from_cli(args.org)                       # auth
    runner = TrackedClient(client) if args.reset else client           # wrap for teardown
    pool = { sob: [ids of init rows] for each write-target object }    # query the init table
    trig, _ = realize_trigger(recipe, runner, alias, 0, target_pool=pool)  # Phase 1
    ctx = RunContext(fixtures={"trigger": trig, ...})
    res = interpreter.run(recipe, ctx, dispatch=live.make_dispatch(runner))  # Phase 3
    if args.reset: runner.teardown()                                   # Phase 5
    Meaning: auth → build the sample trigger → run the recipe with the live dispatcher → optionally restore.

python3 test_sandbox/run.py 93505634 --live
Load recipe 93505634, connect to Salesforce, create or choose a realistic trigger event, then run the interpreter using live Salesforce actions.

## Phrase 3 - The engine executes the recipe
1. loader.py: Here is the starting point. Here are the steps we need to walk through.
2. interpreter.py — the walker:
    - Interpreter.run → sets step_outputs[trigger.as] = {"request":{"Id":"00Ug…"}}, then exec_block(trigger.block).
    - exec_block → loops the 2 child steps (delete, return_response) → exec_step.
    - exec_step → keyword=="action" → exec_action.
    - exec_action → resolve_input then dispatch:
    inp = resolve_input(step["input"], ctx)             # {"id":"#{_ref(...)}","sobject_name":"Event"}
    out = self.dispatch("salesforce","delete_sobject", inp, ctx)
    ctx.set_output(step["as"], out); ctx.record(...)

    resolve_input → formula.interpolate → refs — turns the datapill into a value.
    # resolve_input: for the string "#{_ref(\"...\",\"d1232a54\",[\"request\",\"Id\"])}"
    formula.interpolate(s, ctx, ...)        # finds #{...}, evaluates the _ref inside
    # refs.resolve("workato_api_platform","d1232a54",["request","Id"], ctx):
    base = ctx.step_outputs["d1232a54"]     # the trigger event you set
    return dig(base, ["request","Id"])       # -> "00Ug…"
    Meaning: the id field #{_ref(...)} becomes the literal Event id from the trigger. So inp = {"id":"00Ug…","sobject_name":"Event"}.


### PHASE 4 — The connector performs the real delete
test_sandbox/live/salesforce.py · make_dispatch + handler
def dispatch(provider, operation, inp, ctx):
    if provider == "salesforce": return sf(provider, operation, inp, ctx)  # LIVE
    return comps.dispatch(...)                                             # else mocked
# handler:
if operation == "delete_sobject":
    res = client.delete(sobject, inp.get("id"))     # real REST
    ctx.log_side_effect(provider, operation, sobject=sobject, id=inp.get("id"))
    return {"id": inp.get("id"), "success": True}
Meaning: because provider is salesforce, the real handler runs; it calls the live client's delete and logs the side-effect.

test_sandbox/salesforce_live/client.py — the actual HTTPS call.
def delete(self, sobject, rid):
    self._req("DELETE", "/services/data/v59.0/sobjects/Event/00Ug…")
# _req adds the bearer token + retries; _raw does urllib.urlopen
Meaning: this is the network call that removes the Event from your org. (from_cli got the token from sf org display; _raw retries on transient connection resets.)

### PHASE 5 — Isolation / reset (only with --reset)

test_sandbox/live/tracker.py · TrackedClient
def delete(self, sobject, rid):
    snap = self._c.get(sobject, rid)        # snapshot the row BEFORE deleting
    self.changes.append(("delete", sobject, rid, snap))
    return self._c.delete(sobject, rid)     # real delete
    
def teardown(self):
    for ch in reversed(self.changes):
        if ch[0] == "delete":
            clean = {createable, non-null fields from snap}
            self._c.create(o, clean)        # RE-CREATE the deleted row (new id, same data)
Meaning: if the runner is a TrackedClient, every delete is recorded with a snapshot; teardown re-creates the deleted Event so the init table goes back to 10.

