#!/usr/bin/env python3
"""
score_predictions_live.py - Stage 9: compare candidate live runs vs live gold.

Verdict per scenario (live_strict_pass requires ALL of):
  1-3. parse / structure / schema gates already passed (from the runner)
  4.   no live connector error and status matches gold
  5.   read-back succeeded
  6.   canonical live diff == gold canonical live diff (1:1 set match)
  7.   no extra live writes (unmatched read-back effects OR blocked/violating
       write calls)
  8.   no missing live writes
  9.   read-only gold (no live effects) -> candidate made zero real writes
 10.   every scenario of the task passes

Headline metric: pass@1_live_write_verified_strict. cleanup_success and
flake_retry_rate are reported separately (never silently ignored).

Usage:
  python3 score_predictions_live.py --name run1
  (reads results/<name>.live_candidate_effects.jsonl + gold/live_groundtruth_effects.jsonl)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from test_sandbox.benchmark_v1 import common  # noqa: E402
from test_sandbox.benchmark_v1.compare_effects import _match_sets, _canon_str  # noqa: E402


def compare_live_scenario(gold_s, cand_s):
    v = {"scenario_id": gold_s["scenario_id"]}
    if cand_s is None:
        v.update(fail_stage="live_run_error", live_strict_pass=False,
                 detail="scenario not executed")
        return v
    v["status_match"] = gold_s["status"] == cand_s.get("status")
    if cand_s.get("live_run_error"):
        v.update(fail_stage="live_run_error", live_strict_pass=False,
                 detail=cand_s["live_run_error"])
        return v
    if gold_s.get("readback_error") or gold_s.get("live_effects_canonical") is None:
        v.update(fail_stage="gold_readback_error", live_strict_pass=False)
        return v
    if cand_s.get("readback_error") or cand_s.get("live_effects_canonical") is None:
        v.update(fail_stage="live_readback_error", live_strict_pass=False,
                 detail=cand_s.get("readback_error"))
        return v
    exp = gold_s["live_effects_canonical"]
    obs = cand_s["live_effects_canonical"]
    missing, extra = _match_sets(exp, obs,
                                 lambda a, b: _canon_str(a) == _canon_str(b))
    violations = cand_s.get("policy_violations") or []
    # "read-only" means the gold neither produced effects NOR attempted real
    # writes (a gold write that landed nothing must not flag the candidate's
    # identical no-op write as extra).
    read_only = not exp and not (gold_s.get("n_real_writes") or 0)
    extra_real_writes = (cand_s.get("n_real_writes") or 0) if read_only else 0
    v.update(
        missing_effects=missing, extra_effects=extra,
        n_policy_violations=len(violations),
        flake_retries=len(cand_s.get("flake_retries") or []),
        cleanup_ok=bool(cand_s.get("cleanup_ok", True)),
        live_write_acked=all(w.get("acked") for w in
                             (cand_s.get("write_log") or []) if not w.get("blocked")),
    )
    if violations:
        v.update(fail_stage="live_policy_violation", live_strict_pass=False)
    elif read_only and extra_real_writes:
        v.update(fail_stage="live_extra_write", live_strict_pass=False,
                 detail="read-only gold but candidate wrote %d times" % extra_real_writes)
    elif missing and extra:
        v.update(fail_stage="live_effect_mismatch", live_strict_pass=False)
    elif extra:
        v.update(fail_stage="live_extra_write", live_strict_pass=False)
    elif missing:
        v.update(fail_stage="live_missing_write", live_strict_pass=False)
    elif not v["status_match"]:
        v.update(fail_stage="status_mismatch", live_strict_pass=False)
    else:
        v.update(fail_stage="pass", live_strict_pass=True)
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    args = ap.parse_args()

    gold = {g["task_id"]: g for g in common.read_jsonl(
        os.path.join(common.GOLD_DIR, "live_groundtruth_effects.jsonl"))}
    cand_rows = common.read_jsonl(os.path.join(
        common.RESULTS_DIR, "%s.live_candidate_effects.jsonl" % args.name))
    sandbox_results = {r["task_id"]: r for r in common.read_jsonl(
        os.path.join(common.RESULTS_DIR, "%s.results.jsonl" % args.name))}

    verdicts = []
    for row in cand_rows:
        tid = row["task_id"]
        g = gold.get(tid)
        if row.get("fail_stage"):
            verdicts.append({"task_id": tid, "live_strict_pass": False,
                             "fail_stage": row["fail_stage"],
                             "detail": row.get("detail")})
            continue
        cand_by_scen = {s["scenario_id"]: s for s in row.get("scenarios") or []}
        scen_v = [compare_live_scenario(s, cand_by_scen.get(s["scenario_id"]))
                  for s in g["scenarios"]]
        passed = all(s["live_strict_pass"] for s in scen_v)
        stage = "pass" if passed else next(
            (s["fail_stage"] for s in scen_v if not s["live_strict_pass"]), "fail")
        verdicts.append({
            "task_id": tid, "live_strict_pass": passed, "fail_stage": stage,
            "cleanup_ok": all(s.get("cleanup_ok", True) for s in scen_v),
            "flake_retries": sum(s.get("flake_retries", 0) for s in scen_v),
            "scenarios": scen_v,
        })

    n = len(verdicts)
    stages = {}
    for v in verdicts:
        stages[v["fail_stage"]] = stages.get(v["fail_stage"], 0) + 1
    scen_all = [s for v in verdicts for s in v.get("scenarios", [])]

    def rate(k):
        vals = [v for v in verdicts if k in v]
        return round(sum(1 for v in vals if v[k]) / len(vals), 4) if vals else None

    sandbox_vs_live = {"sandbox_pass_live_fail": 0, "live_pass_sandbox_fail": 0}
    for v in verdicts:
        sb = sandbox_results.get(v["task_id"])
        if sb:
            if sb.get("strict_pass") and not v["live_strict_pass"]:
                sandbox_vs_live["sandbox_pass_live_fail"] += 1
            if v["live_strict_pass"] and not sb.get("strict_pass"):
                sandbox_vs_live["live_pass_sandbox_fail"] += 1

    metrics = {
        "n_tasks_scored": n,
        "pass@1_live_write_verified_strict": rate("live_strict_pass"),
        "fail_stage_counts": dict(sorted(stages.items(), key=lambda kv: -kv[1])),
        "live_write_ack_rate": round(
            sum(1 for s in scen_all if s.get("live_write_acked"))
            / len(scen_all), 4) if scen_all else None,
        "live_extra_write_rate": round(
            sum(1 for s in scen_all if s.get("extra_effects")) / len(scen_all), 4)
        if scen_all else None,
        "live_missing_write_rate": round(
            sum(1 for s in scen_all if s.get("missing_effects")) / len(scen_all), 4)
        if scen_all else None,
        "live_policy_violation_rate": round(
            sum(1 for s in scen_all if s.get("n_policy_violations")) / len(scen_all), 4)
        if scen_all else None,
        "cleanup_success_rate": rate("cleanup_ok"),
        "flake_retry_rate": round(
            sum(1 for s in scen_all if s.get("flake_retries")) / len(scen_all), 4)
        if scen_all else None,
        "sandbox_vs_live": sandbox_vs_live if sandbox_results else None,
    }

    vpath = os.path.join(common.RESULTS_DIR, "%s.live.verdicts.jsonl" % args.name)
    mpath = os.path.join(common.RESULTS_DIR, "%s.live.metrics.json" % args.name)
    common.write_jsonl(vpath, verdicts)
    with open(mpath, "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))
    print("\nverdicts -> %s\nmetrics -> %s" % (vpath, mpath))


if __name__ == "__main__":
    main()
