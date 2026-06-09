"""
context.py - the per-run state container (RunContext).

Holds everything one recipe execution needs and accumulates the three outputs
the sandbox cares about: the trace, the side-effect log, and the final state.

  step_outputs : {alias -> output}     filled as each step runs; what _ref reads
  state        : runtime primitives     variables / lookup_tables / db_tables / lists
  fixtures     : provided injection      trigger / reads / config (overrides; gaps faked)
  clock        : deterministic now/today
  scope        : foreach binding stack   {field, index}
  side_effects : external writes log     the "observable answer"
  trace        : per-step record

Deterministic by construction: a fixed clock, no wall-clock calls. This is what
lets a gold run and a candidate run be compared fairly later.
"""

# fixed, deterministic clock for reproducible runs
DEFAULT_NOW = "2026-06-01T00:00:00+00:00"


def _default_state():
    return {
        "variables": {},
        "lookup_tables": {},
        "db_tables": {},
        "lists": {},
        "smart_lists": {},
    }


class RunContext:
    def __init__(self, fixtures=None, initial_state=None, now=None):
        self.step_outputs = {}
        self.state = {**_default_state(), **(initial_state or {})}
        self.fixtures = fixtures or {}
        self.clock = {"now": now or DEFAULT_NOW}
        self.scope = []
        self.side_effects = []
        self.trace = []
        self.formula_errors = []          # unimplemented/failed formulas (coverage)
        self.current_output_schema = None  # set by interpreter before each dispatch
        self.current_alias = None          # alias of the step being dispatched

    # --- step outputs -----------------------------------------------------
    def set_output(self, alias, value):
        if alias is not None:
            self.step_outputs[alias] = value

    def get_output(self, alias):
        return self.step_outputs.get(alias)

    # --- foreach scope ----------------------------------------------------
    def push_scope(self, field, index):
        self.scope.append({"field": field, "index": index})

    def pop_scope(self):
        self.scope.pop()

    @property
    def current_scope(self):
        return self.scope[-1] if self.scope else {}

    # --- accumulation -----------------------------------------------------
    def log_side_effect(self, provider, operation, **data):
        self.side_effects.append({
            "provider": provider,
            "operation": operation,
            "data": data,
        })

    def record(self, **entry):
        self.trace.append(entry)

    # --- result -----------------------------------------------------------
    def result(self, status):
        return {
            "status": status,
            "trace": self.trace,
            "side_effects": self.side_effects,
            "final_state": self.state,
        }
