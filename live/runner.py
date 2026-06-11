"""
runner.py - the single live-run code path.

Extracted from run.py so both the CLI (`run.py --live`) and the batch
ground-truth recorder share ONE implementation. The expensive part of a live
run is authenticating the Salesforce CLI token; `build_live_clients()` does it
once and the resulting clients are reused across many `run_one_live()` calls.

  clients = build_live_clients(org="my-dev-org")     # mints SF token once
  out = run_one_live(doc, bundle, clients)           # run a recipe, get result dict

`run_one_live` returns the same dict run.py prints, plus always carries the
trace / final_state so a caller can record full ground truth (the CLI trims
them by flag).
"""
from test_sandbox.engine import interpreter, loader
from test_sandbox.engine.context import RunContext
from test_sandbox.live import salesforce as live
from test_sandbox.live.realize import realize_trigger, realize_sf_trigger, realize_jira_trigger
from test_sandbox.live.tracker import TrackedClient
from test_sandbox.salesforce_live import SalesforceClient, SalesforceError
from test_sandbox.jira_live import JiraClient
from test_sandbox.slack_live import SlackClient
from test_sandbox.google_sheets_live import SheetsClient

# the providers we drive against real APIs; everything else is mocked
LIVE_PROVIDERS = {"salesforce", "jira", "jira_service_desk",
                  "slack", "slack_bot", "google_sheets"}

WRITE_OPS = {"delete_sobject", "update_sobject", "composite_update_sobject",
             "updated_custom_object", "upsert_sobject"}

# Salesforce ops that only READ — they get logged as side-effects so the trace is
# complete, but they are not writes and must not count toward "truly succeeded".
SF_READ_OPS = {"get_sobject_schema", "search_sobjects", "get_sobject_by_id",
               "get_sobject", "describe"}

# trigger providers that can be fired (per Stage 3 analysis); informational only,
# completion is decided by actually running, not by this flag.
FIREABLE_PREFIXES = ("salesforce", "slack_bot", "clock", "workato_genie",
                     "work_genie", "workato_api_platform", "workato_recipe_function",
                     "byin_workato_recipe_ops", "workato_webhooks")


def classify(recipe):
    """Static facts about a recipe: providers used, which are live vs mocked,
    whether it touches SF custom schema, and trigger fire-ability."""
    provs, live_used, mocked_used = set(), set(), set()
    sf_custom = False
    for s in loader.iter_steps(recipe):
        p = s.get("provider")
        if p:
            provs.add(p)
            (live_used if p in LIVE_PROVIDERS else mocked_used).add(p)
        if p == "salesforce":
            inp = s.get("input") or {}
            sob = inp.get("sobject_name") or ""
            if str(sob).endswith("__c") or any(
                    str(k).endswith("__c") or str(v).find("__c") >= 0
                    for k, v in inp.items() if isinstance(v, str)):
                sf_custom = True
    trig = loader.get_trigger(recipe) or {}
    tprov = trig.get("provider") or ""
    fireable = tprov.startswith(FIREABLE_PREFIXES)
    return {
        "trigger_provider": tprov,
        "fireable": fireable,
        "providers": sorted(provs),
        "live_used": sorted(live_used),
        "mocked_used": sorted(mocked_used),
        "sf_custom_schema": sf_custom,
    }


def live_effects(side_effects):
    """Per live WRITE side-effect, did it produce a real write? (jira key /
    slack ok / sheets rows / sf write success). Read-only ops (schema describe,
    search, GET adhoc) are not writes and are skipped, so they never drag a
    successful recipe into "partial"."""
    out = []
    for se in side_effects:
        pr = se.get("provider")
        if pr not in LIVE_PROVIDERS:
            continue
        data = se.get("data") if isinstance(se.get("data"), dict) else {}
        op = se.get("operation", "")
        if pr in ("jira", "jira_service_desk"):
            wrote = bool(data.get("key")) and not data.get("__jira_error__") and data.get("success") is not False
        elif pr in ("slack", "slack_bot"):
            wrote = data.get("ok") is True
        elif pr == "google_sheets":
            wrote = (data.get("appended") or 0) > 0
        elif pr == "salesforce":
            if op in SF_READ_OPS:
                continue                       # a read, not a write effect
            if op == "__adhoc_http_action":
                if (data.get("verb") or "GET").upper() in ("GET", "HEAD"):
                    continue                   # raw read, not a write
                # a write verb: prefer the logged result, else fall back to
                # "attempted and the run didn't surface an http error".
                res = data.get("result") if isinstance(data.get("result"), dict) else {}
                wrote = (res.get("id") is not None or res.get("success") is True) \
                    if res else not data.get("__http_error__")
            else:
                # create/upsert log the API result nested under "result"; updates
                # log a top-level id; the upsert-create branch logs matched=False.
                res = data.get("result") if isinstance(data.get("result"), dict) else {}
                wrote = bool(data.get("id") or data.get("success")
                             or (data.get("records") is not None)
                             or res.get("id") or res.get("success")
                             or (data.get("matched") is False))
        else:
            wrote = False
        detail = data.get("error") or data.get("note") or data.get("key") or data.get("ts") or ""
        out.append({"provider": pr, "operation": op, "wrote": bool(wrote), "detail": str(detail)[:80]})
    return out


def build_live_clients(org="my-dev-org"):
    """Authenticate every live connector once. SF is required (CLI token);
    Jira/Slack/Sheets go live only if their creds are present, else stay None
    (-> those providers mock). Returns a dict reused across runs."""
    return {
        "sf": SalesforceClient.from_cli(org),
        "jira": JiraClient.from_env(),
        "slack": SlackClient.from_env(),
        "sheets": SheetsClient.from_env(),
    }


def live_provider_status(clients):
    """Which of the live providers are actually wired (for reporting)."""
    return {
        "salesforce": clients.get("sf") is not None,
        "jira": clients.get("jira") is not None,
        "slack": clients.get("slack") is not None,
        "google_sheets": clients.get("sheets") is not None,
    }


def _build_write_pool(recipe, sf):
    """Pre-fetch ids of records the recipe may update/delete, by sobject.
    Objects the org lacks (INVALID_TYPE) resolve to an empty pool, never a crash."""
    pool = {}
    for s in loader.iter_steps(recipe):
        if s.get("provider") == "salesforce" and s.get("name") in WRITE_OPS:
            sob = (s.get("input") or {}).get("sobject_name")
            if sob and sob not in pool:
                try:
                    pool[sob] = [r["Id"] for r in
                                 sf.query_all("SELECT Id FROM %s LIMIT 200" % sob)]
                except SalesforceError:
                    pool[sob] = []
    return pool


def run_one_live(doc, bundle, clients, sample=0, reset=True, want_diff=False):
    """Fire one recipe live and return its result dict.

    doc     : a loaded cleaned-recipe doc ({"id":..., "recipe":...})
    bundle  : input bundle (trigger/config/reads); {} -> trigger auto-realized
    clients : from build_live_clients() (reused)
    reset   : revert SF writes after the run (wrap SF in the change tracker)
    """
    recipe = doc["recipe"]
    sf = clients["sf"]
    # fresh tracker per recipe so each run's diff/teardown is isolated, but the
    # underlying authenticated SF client (and its token) is reused.
    sfrunner = TrackedClient(sf) if (reset or want_diff) else sf

    alias = (loader.get_trigger(recipe) or {}).get("as")
    pool = _build_write_pool(recipe, sf)

    trig = bundle.get("trigger")
    if trig is None:
        trig_step = loader.get_trigger(recipe) or {}
        if trig_step.get("provider") == "salesforce":
            trig = realize_sf_trigger(sfrunner, recipe)
        else:
            trig, _ = realize_trigger(recipe, sfrunner, alias, sample, target_pool=pool)
        # feed a real seeded issue key into trigger pills that drive Jira ops,
        # so key-based calls hit a live issue instead of 404ing on a fake key.
        if clients.get("jira"):
            realize_jira_trigger(recipe, clients["jira"], alias, trig, sample)

    ctx = RunContext(fixtures={"trigger": trig,
                               "config": bundle.get("config", {}),
                               "reads": bundle.get("reads", {})})
    res = interpreter.run(recipe, ctx, dispatch=live.make_dispatch(
        sfrunner, jira_client=clients.get("jira"),
        slack_client=clients.get("slack"), sheets_client=clients.get("sheets")))

    db_diff = sfrunner.diff() if want_diff else None
    if reset:
        sfrunner.teardown()

    out = {
        "id": doc.get("id"),
        "status": res["status"],
        "steps": len(res["trace"]),
        "side_effects": res["side_effects"],
        "formula_errors": ctx.formula_errors,
        "sample": sample,
        "trigger_fired": trig,
        "trace": res["trace"],
        "final_state": res["final_state"],
    }
    if want_diff:
        out["db_diff"] = db_diff
    return out
