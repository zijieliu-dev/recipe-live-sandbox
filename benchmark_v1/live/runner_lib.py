"""runner_lib.py - run ONE recipe live across a task's fixture scenarios.

Shared by run_original_live (gold), run_candidate_live (predictions) and
selfcheck_live. One scenario = materialize namespace -> run with the
LiveWriteDispatch -> read-back -> canonicalize -> cleanup (unless --keep).
"""
import json
import os
import sys
import time

from test_sandbox.benchmark_v1 import common, sandbox
from test_sandbox.benchmark_v1.live import (config as live_config, dispatch as
                                            live_dispatch, namespace, readback)


def load_fixture(recipe_id):
    with open(os.path.join(common.FIXTURES_DIR, "%s.json" % recipe_id)) as f:
        return json.load(f)


def run_task_live(task, recipe, side, clients, cfg, targets, keep=False,
                  scenario_ids=None, groups=None):
    """-> list of per-scenario live result rows. `groups` pins which provider
    groups go live (candidates must reuse the gold run's set)."""
    rid = task["source_recipe_id"]
    fixture = load_fixture(rid)
    rows = []
    for scen in fixture.get("scenarios") or [{"scenario_id": "positive", "overrides": []}]:
        if scenario_ids and scen["scenario_id"] not in scenario_ids:
            continue
        fx = sandbox.apply_overrides(fixture, scen["overrides"]) \
            if scen["overrides"] else fixture
        ns = namespace.materialize(rid, scen["scenario_id"], side, cfg,
                                   clients, targets)
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
        row["namespace_path"] = namespace.save(ns)
        rows.append(row)
    return rows


def select_tasks(args_ids=None, apps=None, tiers=None, limit=0, require_writes=True):
    """Pick live-track tasks from the sandbox task list. Default: write tasks
    (read-only tasks have nothing to verify live)."""
    tasks = common.read_jsonl(common.MAIN_TASKS)
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
        out.append(t)
        if limit and len(out) >= limit:
            break
    return out


def progress(i, n):
    if (i + 1) % 5 == 0 or i + 1 == n:
        print("  %d/%d live runs" % (i + 1, n), file=sys.stderr)
