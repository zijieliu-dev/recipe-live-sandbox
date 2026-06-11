"""runner_lib.py - run ONE recipe live across a task's fixture scenarios.

Shared by run_original_live (gold), run_candidate_live (predictions) and
selfcheck_live. One scenario = materialize namespace -> run with the
LiveWriteDispatch -> read-back -> canonicalize -> cleanup (unless --keep).
"""
import json
import os
import sys
import time

from test_sandbox.benchmark_v1 import common, ops, sandbox
from test_sandbox.benchmark_v1.live import (config as live_config, dispatch as
                                            live_dispatch, namespace, readback,
                                            rebind)


def load_fixture(recipe_id):
    with open(os.path.join(common.FIXTURES_DIR, "%s.json" % recipe_id)) as f:
        return json.load(f)


def run_task_live(task, recipe, side, clients, cfg, targets, keep=False,
                  scenario_ids=None, groups=None, live_overrides=None,
                  needs=None):
    """-> list of per-scenario live result rows. `groups` pins which provider
    groups go live; `live_overrides` are the gold's update-target patch
    templates and `needs` the bench targets to materialize (candidates must
    reuse BOTH from the gold run)."""
    rid = task["source_recipe_id"]
    fixture = load_fixture(rid)
    rows = []
    for scen in fixture.get("scenarios") or [{"scenario_id": "positive", "overrides": []}]:
        if scenario_ids and scen["scenario_id"] not in scenario_ids:
            continue
        fx = sandbox.apply_overrides(fixture, scen["overrides"]) \
            if scen["overrides"] else fixture
        ns = namespace.materialize(rid, scen["scenario_id"], side, cfg,
                                   clients, targets, needs=needs)
        live_ovs = rebind.instantiate(live_overrides, ns)
        if live_ovs:
            fx = sandbox.apply_overrides(fx, live_ovs)
        run_started = time.time()
        row = {"task_id": task["task_id"], "recipe_id": rid,
               "scenario_id": scen["scenario_id"], "side": side,
               "run_started": run_started}
        dsp = live_dispatch.LiveWriteDispatch(fx, ns, clients, cfg, groups=groups)
        row["live_groups"] = sorted(dsp.handlers)
        try:
            record, _ = sandbox.run_recipe(
                recipe, dsp,
                trigger_event=fx.get("trigger_event"), config=fx.get("config"),
                initial_state=fx.get("state"),
                now=(fx.get("clock") or {}).get("now"))
            row["status"] = record["status"]
            row["control_trace"] = record["control_trace"]
        except Exception as e:
            row["status"] = "error"
            row["live_run_error"] = repr(e)[:300]
        row["write_log"] = [
            {k: w.get(k) for k in ("provider", "operation", "requested",
                                   "blocked", "acked")}
            for w in dsp.write_log]
        row["policy_violations"] = dsp.violations
        row["live_errors"] = dsp.live_errors
        row["n_real_writes"] = sum(1 for w in dsp.write_log if not w["blocked"])
        try:
            effects, raw, flakes = readback.read_back(ns, dsp, clients, cfg)
            row["live_effects_canonical"] = effects
            row["readback_raw"] = raw
            row["flake_retries"] = flakes
        except Exception as e:
            row["live_effects_canonical"] = None
            row["readback_error"] = repr(e)[:300]
            row["flake_retries"] = []
        if keep:
            row["cleanup_results"] = [{"skipped": True}]
        else:
            row["cleanup_results"] = namespace.cleanup(ns, clients)
        row["cleanup_ok"] = all(c.get("ok") or c.get("skipped")
                                for c in row["cleanup_results"]) \
            if row["cleanup_results"] else True
        row["materialize_errors"] = ns.get("materialize_errors") or []
        row["namespace_path"] = namespace.save(ns)
        rows.append(row)
    return rows


_APP_GROUP = {"Sheets": "google_sheets", "Jira": "jira", "Slack": "slack",
              "SF": "salesforce"}


def recipe_write_groups(recipe_id):
    """Which live provider groups a recipe actually WRITES to (static scan)."""
    doc = common.load_recipe_doc(recipe_id)
    groups = set()
    for s in common.iter_steps(doc["recipe"]):
        if s.get("keyword") != "action":
            continue
        g = live_config.provider_group(s.get("provider"))
        if g and ops.is_write(s.get("provider"), s.get("name")):
            groups.add(g)
    return groups


def select_tasks(args_ids=None, apps=None, tiers=None, limit=0,
                 require_writes=True, write_apps=None):
    """Pick live-track tasks. `write_apps` selects by which app the recipe
    actually WRITES to (a 'Jira' primary_app task may only write Slack);
    `apps` filters by primary_app."""
    tasks = common.read_jsonl(common.MAIN_TASKS)
    want_groups = {_APP_GROUP[a] for a in write_apps} if write_apps else None
    out = []
    ids = None
    if args_ids:
        ids = {l.strip() for l in open(args_ids) if l.strip()}
    for t in tasks:
        if ids is not None and t["source_recipe_id"] not in ids \
                and t["task_id"] not in ids:
            continue
        if apps and t.get("primary_app") not in apps:
            continue
        if tiers and t.get("tier") not in tiers:
            continue
        if require_writes and t.get("tier") != "live_write":
            continue
        if want_groups is not None \
                and not (recipe_write_groups(t["source_recipe_id"]) & want_groups):
            continue
        out.append(t)
        if limit and len(out) >= limit:
            break
    return out


def progress(i, n):
    if (i + 1) % 5 == 0 or i + 1 == n:
        print("  %d/%d live runs" % (i + 1, n), file=sys.stderr)
