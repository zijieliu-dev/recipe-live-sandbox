"""
loader.py - load a cleaned recipe and index its steps.

A cleaned recipe doc (from clean.py) looks like:
  { "id":..., "flow_id":..., ..., "recipe": <step tree>, "_clean": {...} }

The step tree is rooted at the trigger (keyword="trigger", number=1) and nests
child steps under "block".

Tightened step definition (per Phase 0 finding): a *real* step is a dict that
has a "keyword" AND a "number" (and usually "as"). A bare input field that
happens to be named "keyword" is therefore NOT mistaken for a step.
"""
import json

# the only keywords that denote real recipe steps
STEP_KEYWORDS = {
    "trigger", "action", "if", "elsif", "else",
    "foreach", "repeat", "while_condition", "try", "catch", "stop",
}


def is_step(node):
    """True iff node is a genuine recipe step (not an input field named 'keyword')."""
    return (
        isinstance(node, dict)
        and node.get("keyword") in STEP_KEYWORDS
        and "number" in node
    )


def load(path):
    """Load a cleaned recipe doc from disk."""
    with open(path) as f:
        return json.load(f)


def iter_steps(node):
    """Yield every genuine step in the tree, depth-first (pre-order)."""
    if is_step(node):
        yield node
    if isinstance(node, dict):
        for v in node.values():
            yield from iter_steps(v)
    elif isinstance(node, list):
        for x in node:
            yield from iter_steps(x)


def index_by_alias(recipe):
    """Map each step's `as` alias -> the step dict. Aliases are the datapill
    `line` values, so this is what the ref resolver looks steps up by."""
    index = {}
    for step in iter_steps(recipe):
        alias = step.get("as")
        if alias is not None:
            index[alias] = step
    return index


def get_trigger(recipe):
    """Return the root trigger step (the tree root, normally)."""
    if is_step(recipe) and recipe.get("keyword") == "trigger":
        return recipe
    for step in iter_steps(recipe):
        if step.get("keyword") == "trigger":
            return step
    return None
