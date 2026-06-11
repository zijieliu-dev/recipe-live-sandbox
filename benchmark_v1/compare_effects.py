"""compare_effects.py - execution-equivalence comparison of one scenario run.

Per scenario:
  strict_pass   status matches AND every expected canonical effect is matched
                1:1 by an observed effect AND there are NO extra writes AND the
                internal state diff matches. For read-only ground truth the
                expected reads signature must also be covered (status alone is
                too weak an answer for a read task).
  lenient_pass  status matches AND every expected effect has an observed effect
                with the same (provider-family, target) whose text carries the
                expected required tokens AND no extra writes.

Matching never compares volatile fields (canonicalizers already dropped them)
and never requires same step order/aliases/UUIDs - only same behavior.
"""
import json


def _canon_str(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


def _target_of(e):
    return (e.get("channel") or e.get("project") or e.get("spreadsheet")
            or e.get("sheet") or e.get("sobject") or e.get("object") or None)


def _text_of(e):
    parts = []
    for k in ("text", "summary", "description", "body", "values", "record",
              "button_titles", "modal_title", "comment"):
        v = e.get(k)
        if v:
            parts.append(_canon_str(v) if not isinstance(v, str) else v)
    return " ".join(parts)


def _strict_equal(expected, observed):
    return _canon_str(expected) == _canon_str(observed)


def _lenient_match(expected, observed, required_tokens):
    if expected.get("family") != observed.get("family"):
        return False
    et, ot = _target_of(expected), _target_of(observed)
    if et and et != ot:
        return False
    text = _text_of(observed)
    blob = _canon_str(observed)
    for tok in required_tokens:
        # a token is only demanded from effects that carried it in gold
        if tok in _canon_str(expected) and tok not in blob and tok not in text:
            return False
    return True


def _match_sets(expected_list, observed_list, matcher):
    """Greedy 1:1 matching. Returns (missing_expected, unmatched_observed)."""
    remaining = list(range(len(observed_list)))
    missing = []
    for exp in expected_list:
        hit = None
        for j in remaining:
            if matcher(exp, observed_list[j]):
                hit = j
                break
        if hit is None:
            missing.append(exp)
        else:
            remaining.remove(hit)
    return missing, [observed_list[j] for j in remaining]


def _reads_covered(expected_reads, observed_reads):
    """Every expected (provider, family) read must be performed; the object
    refinement is honored when the observed read names one."""
    missing = []
    obs = [(r.get("provider"), r.get("family"), r.get("object"))
           for r in observed_reads]
    for r in expected_reads:
        want = (r.get("provider"), r.get("family"), r.get("object"))
        ok = any(o[0] == want[0] and o[1] == want[1]
                 and (want[2] is None or o[2] is None or o[2] == want[2])
                 for o in obs)
        if not ok:
            missing.append(r)
    return missing


def compare_scenario(expected, observed):
    """expected: a gold scenario row; observed: canonicalize_run() of the
    candidate. Returns the per-scenario verdict dict."""
    status_match = expected["status"] == observed["status"]
    exp_eff = expected["effects_canonical"]
    obs_eff = observed["effects_canonical"]
    tokens = expected.get("required_tokens") or []

    s_missing, s_extra = _match_sets(exp_eff, obs_eff, _strict_equal)
    l_missing, l_extra = _match_sets(
        exp_eff, obs_eff, lambda e, o: _lenient_match(e, o, tokens))

    state_match = _canon_str(expected.get("state_diff") or {}) == \
        _canon_str(observed.get("state_diff") or {})

    read_task = not exp_eff and not (expected.get("state_diff") or {})
    missing_reads = _reads_covered(expected.get("reads_canonical") or [],
                                   observed.get("reads_canonical") or []) \
        if read_task else []

    strict = (status_match and not s_missing and not s_extra and state_match
              and not missing_reads)
    lenient = (status_match and not l_missing and not l_extra
               and not missing_reads)
    return {
        "status_match": status_match,
        "expected_status": expected["status"],
        "observed_status": observed["status"],
        "is_read_task": read_task,
        "strict_pass": strict,
        "lenient_pass": lenient or strict,
        "missing_effects_strict": s_missing,
        "extra_writes_strict": s_extra,
        "missing_effects_lenient": l_missing,
        "extra_writes_lenient": l_extra,
        "state_diff_match": state_match,
        "missing_reads": missing_reads,
    }


def aggregate_scenarios(per_scenario):
    """A task passes only if EVERY scenario passes (control-flow stress rule)."""
    return {
        "strict_pass": all(s["strict_pass"] for s in per_scenario),
        "lenient_pass": all(s["lenient_pass"] for s in per_scenario),
        "status_match": all(s["status_match"] for s in per_scenario),
        "effect_match": all(not s["missing_effects_strict"] for s in per_scenario),
        "extra_write_count": sum(len(s["extra_writes_strict"]) for s in per_scenario),
        "missing_effect_count": sum(len(s["missing_effects_strict"]) for s in per_scenario),
        "n_scenarios": len(per_scenario),
        "n_scenarios_passed_strict": sum(1 for s in per_scenario if s["strict_pass"]),
    }
