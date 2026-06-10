"""
interpreter.py - Phase 2 tree-walker.

Executes a cleaned recipe and produces a trace + side-effect log + final state.

Control-flow structure (discovered from the corpus): if/elsif/else, try/catch,
and repeat/while_condition all use a TRAILING-CONTINUATION layout - the
alternative branch (elsif/else), the handler (catch), or the loop condition
(while_condition) is the LAST child inside the construct's `block`:

    if.block      = [then-steps..., (elsif|else)?]
    elsif.block   = [then-steps..., (elsif|else)?]   (chains)
    else.block    = [steps...]
    try.block     = [protected..., catch?]
    catch.block   = [handler...]
    repeat.block  = [body..., while_condition]       (do-while)
    foreach.block = [body...]                         (run per item)

Phase-2 deferrals (made explicit, replaced in later phases):
  - formulas with logic / scope tokens  -> None      (Phase 3: real evaluator)
  - if/elsif conditions                 -> then-branch (Phase 3)
  - foreach                             -> 1 stub iteration (Phase 5: real lists)
  - repeat/while                        -> MAX_REPEAT iterations (Phase 3 cond)
  - comp behavior                       -> generic stub (Phase 4: real comps)
"""
from . import loader, refs, formula, fabricate

MAX_REPEAT = 1          # cap for do-while loops (condition is stubbed past 1)
MAX_FOREACH = 3         # cap iterations per foreach (keeps traces bounded)


class StopRecipe(Exception):
    """Raised by a `stop` step to terminate the recipe."""


class StepError(Exception):
    """A step failed to execute; caught by an enclosing try/catch or the runner."""
    def __init__(self, step, reason):
        self.step = step
        self.reason = reason
        super().__init__("step #%s %s::%s: %s" % (
            step.get("number"), step.get("provider"), step.get("name"), reason))


# --------------------------------------------------------------------------- #
# input resolution (delegates to the Phase-3 formula engine)                  #
# --------------------------------------------------------------------------- #
def resolve_input(node, ctx):
    """Recursively resolve a step's input structure, evaluating #{...}."""
    if isinstance(node, str):
        return formula.interpolate(node, ctx, ctx.formula_errors)
    if isinstance(node, list):
        return [resolve_input(x, ctx) for x in node]
    if isinstance(node, dict):
        if "____source" in node:          # Workato list-mapping (composite ops)
            return _resolve_list_map(node, ctx)
        return {k: resolve_input(v, ctx) for k, v in node.items()}
    return node


def _resolve_list_map(node, ctx):
    """Expand a `{____source: <list>, <field>: <template-with-current_item>}` block
    into one resolved dict per item of the source list (composite create/update).
    Each item is bound as the foreach `current_item` scope while its template resolves."""
    src = resolve_input(node["____source"], ctx)
    if src is refs.MISSING or src is None:
        src = []
    elif not isinstance(src, list):
        src = [src]
    template = {k: v for k, v in node.items() if k not in ("____source", "attributes")}
    out = []
    for i, item in enumerate(src):
        ctx.push_scope(field=item, index=i)
        out.append({k: resolve_input(v, ctx) for k, v in template.items()})
        ctx.pop_scope()
    return out


# --------------------------------------------------------------------------- #
# generic comp dispatch (Phase 2 stub; Phase 4 injects real comps)            #
# --------------------------------------------------------------------------- #
def _generic_dispatch(provider, operation, resolved_input, ctx):
    ctx.log_side_effect(provider, operation, input=resolved_input)
    return {}


# --------------------------------------------------------------------------- #
# control flow                                                                #
# --------------------------------------------------------------------------- #
def _split_trailing(block, kws):
    """Split a block into (body, trailing-continuation-or-None)."""
    block = block or []
    if block and isinstance(block[-1], dict) and block[-1].get("keyword") in kws:
        return block[:-1], block[-1]
    return list(block), None


def _eval_condition(step, ctx):
    """Evaluate the if/elsif condition tree (Phase 3)."""
    return formula.eval_condition_tree(step.get("input"), ctx, ctx.formula_errors)


class Interpreter:
    def __init__(self, dispatch=None):
        self.dispatch = dispatch or _generic_dispatch

    # -- per-construct ------------------------------------------------------
    def exec_block(self, block, ctx):
        for step in (block or []):
            self.exec_step(step, ctx)

    def exec_step(self, step, ctx):
        kw = step.get("keyword")
        if kw == "action":
            self.exec_action(step, ctx)
        elif kw in ("if", "elsif"):
            self.exec_if(step, ctx)
        elif kw == "else":
            self.exec_block(step.get("block"), ctx)
        elif kw == "foreach":
            self.exec_foreach(step, ctx)
        elif kw == "try":
            self.exec_try(step, ctx)
        elif kw == "repeat":
            self.exec_repeat(step, ctx)
        elif kw == "while_condition":
            pass                              # only meaningful as repeat's trailer
        elif kw == "stop":
            ctx.record(step=step.get("number"), keyword="stop")
            raise StopRecipe()
        elif kw == "catch":
            self.exec_block(step.get("block"), ctx)
        # trigger handled in run(); unknown keywords are skipped

    def exec_action(self, step, ctx):
        inp = resolve_input(step.get("input", {}), ctx)
        ctx.current_output_schema = step.get("extended_output_schema")
        ctx.current_alias = step.get("as")
        try:
            out = self.dispatch(step.get("provider"), step.get("name"), inp, ctx)
        except (StopRecipe, StepError):
            raise
        except Exception as e:
            raise StepError(step, "dispatch raised %r" % e)
        ctx.set_output(step.get("as"), out)
        ctx.record(step=step.get("number"), keyword="action",
                   provider=step.get("provider"), name=step.get("name"),
                   alias=step.get("as"))

    def exec_if(self, step, ctx):
        body, cont = _split_trailing(step.get("block"), ("elsif", "else"))
        taken = _eval_condition(step, ctx)
        ctx.record(step=step.get("number"), keyword=step.get("keyword"), taken=taken)
        if taken:
            self.exec_block(body, ctx)
        elif cont is not None:
            self.exec_step(cont, ctx)

    def exec_foreach(self, step, ctx):
        ctx.record(step=step.get("number"), keyword="foreach")
        src = resolve_input(step.get("input", {}), ctx).get("source")
        if not isinstance(src, list) or not src:
            src = [{}, {}]                       # fabricated fallback so body runs
        for i, item in enumerate(src[:MAX_FOREACH]):
            ctx.push_scope(field=item, index=i)
            self.exec_block(step.get("block"), ctx)
            ctx.pop_scope()

    def exec_try(self, step, ctx):
        body, catch = _split_trailing(step.get("block"), ("catch",))
        ctx.record(step=step.get("number"), keyword="try")
        try:
            self.exec_block(body, ctx)
        except StopRecipe:
            raise
        except StepError as e:
            ctx.record(step=step.get("number"), keyword="catch", caught=str(e))
            if catch is not None:
                self.exec_block(catch.get("block"), ctx)

    def exec_repeat(self, step, ctx):
        body, _cond = _split_trailing(step.get("block"), ("while_condition",))
        ctx.record(step=step.get("number"), keyword="repeat")
        for _ in range(MAX_REPEAT):
            self.exec_block(body, ctx)

    # -- entry point --------------------------------------------------------
    def run(self, recipe, ctx):
        trigger = loader.get_trigger(recipe) or recipe
        event = ctx.fixtures.get("trigger")
        if event is None:                                # fabricate from schema
            event = fabricate.fabricate(
                trigger.get("extended_output_schema") or [],
                "trigger::%s" % trigger.get("as"))
        ctx.set_output(trigger.get("as"), event)
        ctx.record(step=trigger.get("number"), keyword="trigger",
                   provider=trigger.get("provider"), name=trigger.get("name"),
                   alias=trigger.get("as"))
        try:
            self.exec_block(trigger.get("block"), ctx)
            status = "completed"
        except StopRecipe:
            status = "stopped"
        except StepError as e:
            status = "error"
            ctx.record(error=str(e))
        return ctx.result(status)


def run(recipe, ctx, dispatch=None):
    """Convenience: execute a recipe with a fresh interpreter."""
    return Interpreter(dispatch=dispatch).run(recipe, ctx)
