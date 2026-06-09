"""
verifier.py - Phase 7. Compare a candidate recipe against a gold reference.

The sandbox is deterministic and fabrication is keyed by provider::operation
(recipe-independent), so two recipes that call the same connector op see the
same data. The only recipe-specific input is the trigger event, so we:

  1. run the gold recipe (fabricating inputs),
  2. capture the trigger event it used,
  3. run the candidate forced to use that same trigger event,
  4. diff the observable side-effects (the "answer").

Verdict levels:
  exact_match     - identical side-effect log (strict)
  signature_match - same multiset of (provider, operation) calls (lenient)
Plus the missing/extra calls so a failure is actionable.
"""
import json
from collections import Counter

from . import interpreter, loader
from .context import RunContext


def _trigger_event(ctx, recipe):
    trig = loader.get_trigger(recipe)
    return ctx.step_outputs.get(trig.get("as")) if trig else None


def _run(recipe, fixtures, dispatch):
    ctx = RunContext(fixtures=fixtures or {})
    res = interpreter.run(recipe, ctx, dispatch=dispatch)
    return ctx, res


def _sig(se):
    return (se.get("provider"), se.get("operation"))


def _canon(side_effects):
    return json.dumps(side_effects, sort_keys=True, default=str)


def verify(gold_recipe, candidate_recipe, bundle=None, dispatch=None):
    if dispatch is None:
        from .. import comps
        dispatch = comps.dispatch

    gctx, gres = _run(gold_recipe, bundle, dispatch)

    shared = dict(bundle or {})
    shared["trigger"] = _trigger_event(gctx, gold_recipe)   # force same entry input
    cctx, cres = _run(candidate_recipe, shared, dispatch)

    g_se, c_se = gres["side_effects"], cres["side_effects"]
    gsig, csig = Counter(map(_sig, g_se)), Counter(map(_sig, c_se))

    exact = _canon(g_se) == _canon(c_se)
    signature_match = gsig == csig

    return {
        "match": exact,
        "exact_match": exact,
        "signature_match": signature_match,
        "gold_status": gres["status"],
        "candidate_status": cres["status"],
        "gold_side_effects": len(g_se),
        "candidate_side_effects": len(c_se),
        "missing_calls": [list(x) for x in (gsig - csig).elements()],
        "extra_calls": [list(x) for x in (csig - gsig).elements()],
    }
