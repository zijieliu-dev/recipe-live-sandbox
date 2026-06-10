"""
refs.py - parse and resolve the canonical datapill reference.

clean.py normalized both Workato dialects into one form:
    _ref("<provider>", "<line>", [<path segments>])

This module finds those tokens in a string, parses them, and resolves them
against a run's step-output store (a {alias -> output} dict), digging the path.

Resolution rules for the path:
  - dict segment            -> value[seg]
  - list + "first"/"last"   -> first/last element
  - list + integer string   -> index
  - list + field name       -> project that field across the list (Workato pill
                               semantics: a path through a list maps over it)
Anything that runs off the end of real data returns MISSING (lazy fabrication
in Phase 5 will fill these; Phase 1 just reports them).
"""
import json
import re

_REF_START = re.compile(r"_ref\(")


class _Missing:
    """Sentinel for an unresolved reference."""
    __slots__ = ()

    def __repr__(self):
        return "<MISSING>"

    def __bool__(self):
        return False


MISSING = _Missing()


def _scan_paren(s, open_idx):
    """Given the index of '(', return the index of its matching ')'.
    Respects quoted strings and nested brackets/parens."""
    depth = 0
    in_str = False
    esc = False
    quote = ""
    k = open_idx
    n = len(s)
    while k < n:
        c = s[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                in_str = False
        else:
            if c == '"' or c == "'":
                in_str = True
                quote = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return k
        k += 1
    raise ValueError("unbalanced _ref(")


def find_refs(s):
    """Yield dicts {span, provider, line, path} for every _ref(...) in s."""
    out = []
    for m in _REF_START.finditer(s):
        open_idx = m.end() - 1                 # the '(' in "_ref("
        try:
            close = _scan_paren(s, open_idx)
        except ValueError:
            continue
        argstr = s[open_idx + 1:close]         # provider","line",[path]
        try:
            provider, line, path = json.loads("[" + argstr + "]")
        except Exception:
            continue
        out.append({
            "span": (m.start(), close + 1),
            "provider": provider,
            "line": line,
            "path": path,
        })
    return out


def _is_int(seg):
    return isinstance(seg, int) or (isinstance(seg, str) and seg.lstrip("-").isdigit())


def _special_segment(seg, value, ctx):
    """Resolve a Workato non-scalar path element. Returns (handled, new_value)."""
    pet = seg.get("path_element_type") if isinstance(seg, dict) else None
    if pet == "size":
        return True, (len(value) if isinstance(value, (list, dict, str)) else MISSING)
    if pet == "current_item":
        # the item bound by the enclosing foreach...
        scoped = ctx.current_scope.get("field", MISSING) if ctx else MISSING
        if scoped is not MISSING:
            return True, scoped
        # ...or, with no foreach scope, Workato treats it as the first list element
        if isinstance(value, list):
            return True, (value[0] if value else MISSING)
        return True, value
    if pet == "current_index":
        return True, (ctx.current_scope.get("index", MISSING) if ctx else MISSING)
    if pet == "join":
        # implicit external read; fabrication will supply it (Level-B follow-up)
        return True, MISSING
    return False, MISSING


def dig(value, path, ctx=None):
    """Walk `path` into `value`, applying the list/dict/accessor rules above.

    `ctx` (optional) lets special segments resolve against the run scope
    (current_item / current_index) and compute size.
    """
    for seg in path:
        if value is MISSING or value is None:
            return MISSING
        if isinstance(seg, (dict, list)):
            handled, nv = _special_segment(seg, value, ctx)
            if handled:
                value = nv
                continue
            return MISSING
        if isinstance(value, list):
            if seg == "first":
                value = value[0] if value else MISSING
            elif seg == "last":
                value = value[-1] if value else MISSING
            elif _is_int(seg):
                idx = int(seg)
                value = value[idx] if -len(value) <= idx < len(value) else MISSING
            else:
                # project the field across the list
                value = [v.get(seg) if isinstance(v, dict) else None for v in value]
        elif isinstance(value, dict):
            value = value.get(seg, MISSING)
        else:
            return MISSING
    return value


def resolve(provider, line, path, ctx):
    """Resolve one reference against the run context's step-output store.

    `line` is the step alias. Non-step sources (e.g. workato/job_context) are
    not in step_outputs yet; they return MISSING here and will be supplied by
    fabrication/env in a later phase.
    """
    base = ctx.step_outputs.get(line, MISSING)
    if base is MISSING:
        return MISSING
    return dig(base, path, ctx)
