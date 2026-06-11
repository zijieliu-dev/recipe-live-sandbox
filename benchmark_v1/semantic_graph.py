"""semantic_graph.py - Stage 2: normalize a recipe into a semantic execution graph.

The graph is NOT the benchmark answer; it drives fixture generation (which
reads feed which branches), task-description generation (what the recipe
actually does, from structure rather than comments), and diagnostics.

Node = one step: trigger / action / control. We extract per node:
  - provider/operation, alias
  - literal inputs (static scalars - the business constants: channel, project,
    sobject_name, timezone, ...)
  - dataflow edges: every _ref(provider, alias, path) found in its inputs
  - parsed condition leaves for if/elsif (lhs ref, operand, rhs literal)
  - foreach source ref

Dataflow is taken from the actual input strings (executed dataflow), never
from step comments.
"""
import json

from test_sandbox.engine import loader, refs
from test_sandbox.benchmark_v1 import ops


def _walk_strings(node, cb):
    if isinstance(node, str):
        cb(node)
    elif isinstance(node, list):
        for x in node:
            _walk_strings(x, cb)
    elif isinstance(node, dict):
        for v in node.values():
            _walk_strings(v, cb)


def refs_in(value):
    """All _ref tokens anywhere inside a step-input structure."""
    found = []

    def cb(s):
        if "_ref(" in s:
            for r in refs.find_refs(s):
                found.append({
                    "source_provider": r["provider"],
                    "source_alias": r["line"],
                    "path": [p for p in r["path"]
                             if isinstance(p, (str, int))],
                    "special": [p.get("path_element_type") for p in r["path"]
                                if isinstance(p, dict) and p.get("path_element_type")],
                })
    _walk_strings(value, cb)
    return found


def literal_inputs(inp, cap=120):
    """Static scalar inputs (no #{...} interpolation) - the business constants."""
    out = {}
    if not isinstance(inp, dict):
        return out
    for k, v in inp.items():
        if isinstance(v, (int, float, bool)):
            out[k] = v
        elif isinstance(v, str) and v.strip() and "#{" not in v and "_ref(" not in v:
            s = v.strip()
            out[k] = s if len(s) <= cap else s[:cap] + "..."
    return out


def condition_leaves(node):
    """Flatten an if/elsif condition tree into leaf dicts."""
    leaves = []

    def rec(n):
        if not isinstance(n, dict):
            return
        if n.get("type") == "compound":
            for c in n.get("conditions", []):
                rec(c)
            return
        if "operand" in n or "lhs" in n:
            lhs = n.get("lhs")
            leaf = {
                "operand": n.get("operand"),
                "lhs": lhs if isinstance(lhs, str) else json.dumps(lhs, default=str),
                "rhs": n.get("rhs"),
                "lhs_refs": refs_in(lhs) if isinstance(lhs, str) else [],
            }
            leaves.append(leaf)
    rec(node)
    return leaves


def _node_of(step, depth, parent):
    kw = step.get("keyword")
    node = {
        "number": step.get("number"),
        "keyword": kw,
        "depth": depth,
        "parent": parent,
        "alias": step.get("as"),
        "comment": step.get("comment") or None,
    }
    if kw in ("trigger", "action"):
        node["provider"] = step.get("provider")
        node["name"] = step.get("name")
        node["object"] = ops.object_of(step.get("input") or {})
        node["is_write"] = (kw == "action"
                            and ops.is_write(step.get("provider"), step.get("name")))
        node["literal_inputs"] = literal_inputs(step.get("input") or {})
        node["refs"] = refs_in(step.get("input"))
    elif kw in ("if", "elsif"):
        node["conditions"] = condition_leaves(step.get("input"))
        inp = step.get("input")
        node["condition_combine"] = (inp.get("operand") or "and") \
            if isinstance(inp, dict) and inp.get("type") == "compound" else "and"
    elif kw == "foreach":
        src = (step.get("input") or {}).get("source")
        node["source"] = src if isinstance(src, str) else json.dumps(src, default=str)
        node["source_refs"] = refs_in(src)
    elif kw == "stop":
        node["literal_inputs"] = literal_inputs(step.get("input") or {})
    return node


def build(recipe):
    """Recipe step-tree -> {nodes, alias_index, condition_field_paths, providers}."""
    nodes = []

    def rec(step, depth, parent):
        if not loader.is_step(step):
            return
        node = _node_of(step, depth, parent)
        nodes.append(node)
        for child in (step.get("block") or []):
            rec(child, depth + 1, step.get("number"))

    trig = loader.get_trigger(recipe) or recipe
    rec(trig, 0, None)

    # (alias, dotted-path) pairs that feed conditions; fixture marker injection
    # must never mutate these fields.
    cond_paths = set()
    for n in nodes:
        for leaf in n.get("conditions", []) or []:
            for r in leaf["lhs_refs"]:
                cond_paths.add((r["source_alias"],
                                ".".join(str(p) for p in r["path"])))

    providers = sorted({n.get("provider") for n in nodes if n.get("provider")})
    return {
        "nodes": nodes,
        "providers": providers,
        "condition_field_paths": sorted(["%s:%s" % cp for cp in cond_paths]),
        "n_steps": len(nodes),
    }
