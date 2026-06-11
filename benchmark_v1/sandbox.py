"""sandbox.py - the benchmark execution sandbox.

Wraps the deterministic engine (engine/interpreter.py) with a FIXTURE-BACKED
dispatch so a gold run and a candidate run see exactly the same world:

  primitive providers (clock, json_parser, lookup_table, logger, ...)
      -> the real comps implementation (already deterministic)
  external connector READ
      -> served from the fixture's recorded provider state, keyed by
         provider::operation[::object]  (never from the step's
         extended_output_schema - candidate recipes don't have one)
  external connector WRITE
      -> logged as an EFFECT (the scored answer) and answered with the
         fixture's recorded write output (or a deterministic stub)

Two dispatch modes share the routing:
  RecordingDispatch  fixture BUILD: fabricate read outputs from the original
                     step's schema (seeded provider::operation - recipe-
                     independent) and record them into the fixture.
  FixtureDispatch    gold + candidate runs: serve recorded state only.

run() returns a RunRecord dict: status, calls, effects, reads, control trace,
state diff, formula errors.
"""
import copy
import json

from test_sandbox import comps
from test_sandbox.comps._default import default_handle
from test_sandbox.engine import interpreter, fabricate, loader
from test_sandbox.engine.context import RunContext
from test_sandbox.benchmark_v1 import ops
from test_sandbox.benchmark_v1.common import stable_hash, DEFAULT_NOW

_STATE_KEYS = ("lookup_tables", "db_tables", "lists", "smart_lists")


def is_external(provider):
    """True iff the provider has no bespoke comp (mock-stub external connector)."""
    if not provider:
        return False
    try:
        return comps._get(provider) is default_handle
    except Exception:
        return True


# Primitives whose comps fall back to schema-shaped fabrication when their
# in-run state is empty (lookup_table always; smart_list/db_table on empty
# state). Candidate recipes carry no schemas, so that fallback MUST be served
# from the fixture or gold and candidate would see different worlds.
_LOOKUP_READ_OPS = {"search_entries", "get_entries", "lookup_entry", "get_entry"}
_DBT_READ_OPS = {"get_records", "new_records_realtime", "updated_records_realtime",
                 "new_records_polling"}


def _prim_read_key(provider, operation, inp):
    """Fixture key for a schema-fallback-capable primitive read; None for
    everything else (real stateful comp behavior)."""
    if provider == "lookup_table" and operation in _LOOKUP_READ_OPS:
        return ops.fixture_key(provider, operation, ops.object_of(inp))
    if provider == "workato_smart_list" and operation == "query_list":
        return ops.fixture_key(provider, operation)
    if provider == "workato_db_table" and operation in _DBT_READ_OPS:
        tid = str(inp.get("table_id") or inp.get("id") or "default")
        return ops.fixture_key(provider, operation, tid)
    return None


def _prim_has_state(provider, inp, ctx):
    """True when the primitive's in-run state is non-empty - the comp then
    serves real accumulated data and the schema fallback is NOT in play."""
    if provider == "workato_smart_list":
        return bool(ctx.state.get("smart_lists", {}).get("_smart_list"))
    if provider == "workato_db_table":
        tid = str(inp.get("table_id") or inp.get("id") or "default")
        return bool(ctx.state.get("db_tables", {}).get(tid))
    return False                       # lookup_table reads are stateless


def write_stub(provider, operation):
    """Deterministic write-result a connector returns when the fixture has no
    recorded output for this op. Superset of the id-ish fields recipes dig."""
    h = stable_hash("%s::%s" % (provider, operation))
    n = int(h, 16) % 100000
    return {"id": "BW_%s" % h, "key": "BW-%d" % (n % 1000), "ok": True,
            "success": True, "ts": "1750000000.%06d" % n, "status": "success",
            "url": "https://example.com/bw/%d" % n}


class _Recorder:
    """TraceRecorder: every external call, classified, with resolved input."""

    def __init__(self):
        self.calls = []
        self.effects = []      # write calls (the scored answer, pre-canonical)
        self.reads = []        # read calls (diagnostic)
        self.fixture_misses = []

    def record(self, provider, operation, inp, output, w, obj, served):
        rec = {"seq": len(self.calls), "provider": provider,
               "operation": operation, "object": obj, "is_write": w,
               "input": inp, "served": served}
        self.calls.append(rec)
        if w:
            self.effects.append({"provider": provider, "operation": operation,
                                 "object": obj, "input": inp})
        else:
            self.reads.append({"provider": provider, "operation": operation,
                               "object": obj})
            if served == "fallback":
                self.fixture_misses.append("%s::%s" % (provider, operation))


class RecordingDispatch:
    """Fixture-build mode: fabricate external reads from the ORIGINAL step's
    output schema (seed = provider::operation, recipe-independent), recording
    everything into a fixture dict."""

    def __init__(self, seed_reads=None, seed_writes=None, alias_keys=None):
        self.recorder = _Recorder()
        self.reads_state = seed_reads if seed_reads is not None else {}
        self.writes_out = seed_writes if seed_writes is not None else {}
        self.alias_keys = alias_keys if alias_keys is not None else {}
        # seeded entries (e.g. branch-fixed reads) win over fresh fabrication:
        # setdefault below only fills keys not yet present.

    def _record_prim_fallback(self, provider, operation, inp, ctx, pkey):
        """Record what this primitive read returns on EMPTY state (the schema
        fallback), even when state is currently non-empty - a scenario may skip
        the write that filled it and gold/candidate must then agree."""
        if pkey in self.reads_state:
            return
        saved = None
        if provider == "workato_smart_list":
            saved = ("smart_lists", ctx.state.get("smart_lists"))
            ctx.state["smart_lists"] = {}
        elif provider == "workato_db_table":
            saved = ("db_tables", ctx.state.get("db_tables"))
            ctx.state["db_tables"] = {}
        try:
            out = comps.dispatch(provider, operation, inp, ctx)
        finally:
            if saved:
                ctx.state[saved[0]] = saved[1]
        self.reads_state[pkey] = copy.deepcopy(out)

    def __call__(self, provider, operation, inp, ctx):
        if not is_external(provider):
            pkey = _prim_read_key(provider, operation, inp)
            if pkey is None:
                return comps.dispatch(provider, operation, inp, ctx)
            self._record_prim_fallback(provider, operation, inp, ctx, pkey)
            alias = getattr(ctx, "current_alias", None)
            if alias:
                self.alias_keys[alias] = pkey
            if _prim_has_state(provider, inp, ctx):
                return comps.dispatch(provider, operation, inp, ctx)
            return copy.deepcopy(self.reads_state[pkey])
        obj = ops.object_of(inp)
        key = ops.fixture_key(provider, operation, obj)
        w = ops.is_write(provider, operation)
        ctx.log_side_effect(provider, operation, input=inp)
        schema = getattr(ctx, "current_output_schema", None)
        fab = fabricate.fabricate(schema, "%s::%s" % (provider, operation)) if schema else {}
        if w:
            out = {**write_stub(provider, operation), **fab}
            self.writes_out.setdefault(key, out)
            out = self.writes_out[key]
        else:
            self.reads_state.setdefault(key, fab)
            out = self.reads_state[key]
        alias = getattr(ctx, "current_alias", None)
        if alias:
            self.alias_keys[alias] = key
        self.recorder.record(provider, operation, inp, out, w, obj, "recorded")
        return copy.deepcopy(out)


class FixtureDispatch:
    """Gold/candidate mode: serve external reads from the fixture, log writes."""

    def __init__(self, fixture):
        self.fixture = fixture
        self.recorder = _Recorder()

    def _serve_read(self, provider, operation, obj):
        reads = self.fixture.get("reads") or {}
        for k in (ops.fixture_key(provider, operation, obj),
                  ops.fixture_key(provider, operation)):
            if k in reads:
                return reads[k], "exact"
        # same provider+object through a different operation (equivalent read)
        if obj:
            suffix = "::%s" % obj
            for k in sorted(reads):
                if k.startswith(provider + "::") and k.endswith(suffix):
                    return reads[k], "object"
        # same provider+operation regardless of object
        prefix = "%s::%s::" % (provider, operation)
        for k in sorted(reads):
            if k.startswith(prefix):
                return reads[k], "operation"
        return {}, "fallback"

    def __call__(self, provider, operation, inp, ctx):
        if not is_external(provider):
            pkey = _prim_read_key(provider, operation, inp)
            if pkey is not None and not _prim_has_state(provider, inp, ctx) \
                    and pkey in (self.fixture.get("reads") or {}):
                return copy.deepcopy(self.fixture["reads"][pkey])
            return comps.dispatch(provider, operation, inp, ctx)
        obj = ops.object_of(inp)
        w = ops.is_write(provider, operation)
        ctx.log_side_effect(provider, operation, input=inp)
        if w:
            wouts = self.fixture.get("writes_out") or {}
            out = (wouts.get(ops.fixture_key(provider, operation, obj))
                   or wouts.get(ops.fixture_key(provider, operation))
                   or write_stub(provider, operation))
            served = "recorded" if wouts else "stub"
        else:
            out, served = self._serve_read(provider, operation, obj)
        self.recorder.record(provider, operation, inp, out, w, obj, served)
        return copy.deepcopy(out)


# --------------------------------------------------------------------------- #
# run wrappers                                                                #
# --------------------------------------------------------------------------- #
def control_trace(trace):
    """Summarize the engine trace into the diagnostic control-flow record."""
    out = []
    foreach_iter = {}
    for e in trace:
        kw = e.get("keyword")
        if kw in ("if", "elsif"):
            out.append({"step": e.get("step"), "keyword": kw,
                        "taken": bool(e.get("taken"))})
        elif kw == "foreach":
            foreach_iter[e.get("step")] = foreach_iter.get(e.get("step"), 0) + 1
        elif kw in ("stop", "catch", "repeat", "try"):
            out.append({"step": e.get("step"), "keyword": kw})
    for num, n in sorted(foreach_iter.items(), key=lambda kv: (kv[0] is None, kv[0])):
        out.append({"step": num, "keyword": "foreach", "entries": n})
    return out


def state_diff(initial, final):
    """Internal-state writes (lookup/db tables, lists) the run produced."""
    diff = {}
    for k in _STATE_KEYS:
        a = (initial or {}).get(k) or {}
        b = (final or {}).get(k) or {}
        if json.dumps(a, sort_keys=True, default=str) != json.dumps(b, sort_keys=True, default=str):
            diff[k] = b
    return diff


def apply_overrides(fixture, overrides):
    """Scenario overrides: set fixture values at (target, path)."""
    fx = copy.deepcopy(fixture)
    for ov in overrides or []:
        target, path, value = ov["target"], ov["path"], ov.get("value")
        if target == "trigger":
            base = fx.get("trigger_event")
        elif target.startswith("reads:"):
            base = (fx.get("reads") or {}).get(target[6:])
        else:
            continue
        set_path(base, path, value)
    return fx


def set_path(base, path, value):
    """Set `value` at `path` inside base. A string segment over a list applies
    to every dict element (Workato pill projection semantics)."""
    if base is None or not path:
        return False
    cur = base
    for i, seg in enumerate(path):
        last = i == len(path) - 1
        if isinstance(cur, list):
            if isinstance(seg, int) or (isinstance(seg, str) and seg.lstrip("-").isdigit()):
                idx = int(seg)
                if not (-len(cur) <= idx < len(cur)):
                    return False
                if last:
                    cur[idx] = value
                    return True
                cur = cur[idx]
            elif seg in ("first", "last"):
                if not cur:
                    return False
                idx = 0 if seg == "first" else -1
                if last:
                    cur[idx] = value
                    return True
                cur = cur[idx]
            else:
                ok = False
                for el in cur:
                    if isinstance(el, dict):
                        if last:
                            el[seg] = value
                            ok = True
                        else:
                            ok = set_path(el, path[i:], value) or ok
                return ok
        elif isinstance(cur, dict):
            if last:
                cur[seg] = value
                return True
            if seg not in cur or not isinstance(cur[seg], (dict, list)):
                cur[seg] = {}
            cur = cur[seg]
        else:
            return False
    return False


def run_recipe(recipe, dispatch, trigger_event=None, config=None,
               initial_state=None, now=None):
    """Execute one recipe through the engine with the given dispatch.
    Returns (RunRecord, ctx)."""
    init = copy.deepcopy(initial_state) if initial_state else None
    ctx = RunContext(
        fixtures={"trigger": copy.deepcopy(trigger_event),
                  "config": copy.deepcopy(config or {}), "reads": {}},
        initial_state=copy.deepcopy(init) if init else None,
        now=now or DEFAULT_NOW,
    )
    res = interpreter.run(recipe, ctx, dispatch=dispatch)
    rec = dispatch.recorder if hasattr(dispatch, "recorder") else _Recorder()
    record = {
        "status": res["status"],
        "effects": rec.effects,
        "reads": rec.reads,
        "calls": rec.calls,
        "fixture_misses": sorted(set(rec.fixture_misses)),
        "control_trace": control_trace(res["trace"]),
        "trace": res["trace"],
        "state_diff": state_diff(init or {}, res["final_state"]),
        "formula_errors": ctx.formula_errors,
    }
    return record, ctx


def run_on_fixture(recipe, fixture, overrides=None):
    """Run a recipe (gold or candidate) against a fixture (+scenario overrides)."""
    fx = apply_overrides(fixture, overrides) if overrides else fixture
    dispatch = FixtureDispatch(fx)
    return run_recipe(
        recipe, dispatch,
        trigger_event=fx.get("trigger_event"),
        config=fx.get("config"),
        initial_state=fx.get("state"),
        now=(fx.get("clock") or {}).get("now"),
    )


def trigger_alias(recipe):
    trig = loader.get_trigger(recipe)
    return trig.get("as") if trig else None
