#!/usr/bin/env python3
"""
build_prompts.py - assemble the model-facing prompt for every task.

Each prompt contains: the task description, runtime inputs, the action schemas
for the ALLOWED connectors (the model's tool manual - atomic schemas only,
never recipe fragments), the control-flow schemas, reference syntax, and the
output contract. It never contains the source recipe.

Outputs: prompts/<task_id>.txt and tasks/prompts.jsonl

Usage:  python3 build_prompts.py [--catalog-mode allowed|used]
  allowed (default)  include every catalog op of every allowed connector
  used               include only the ops the original used (easier split)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common  # noqa: E402

_HEADER = """You are generating a recipe JSON for a local workflow-automation sandbox
(Workato-style recipes). Build ONE recipe that implements the task below.

## Task
%(description)s

## Runtime parameters (available to formulas as `input`)
%(runtime_inputs)s

## Allowed connectors
%(allowed)s

## Available action/trigger schemas (your tool manual)
Each entry: keyword, provider, name, required/optional input fields, and the
output fields you can reference from later steps.
%(actions)s

## Control-flow blocks
%(controls)s

## Recipe grammar
- The recipe is a tree rooted at the trigger:
  {"recipe": {"keyword": "trigger", "provider": ..., "name": ..., "as": "t1",
              "input": {...}, "block": [ <steps...> ]}}
- Every step: {"keyword": "action"|"if"|"elsif"|"else"|"foreach"|"stop"|"try"|"catch",
               "provider": ..., "name": ... (actions only), "as": "<unique alias>",
               "input": {...}, "block": [ <nested steps> ]}
- `elsif`/`else` must be the LAST child inside the `block` of the `if` they follow.
  A `catch` must be the LAST child of its `try` block.
- Reference a previous step's output inside any string input:
    #{_ref("<provider>","<as-alias>",["field","nested_field"])}
- Reference the current foreach item:
    #{_ref("<provider>","<foreach-step-alias>",[{"path_element_type":"current_item"},"field"])}
- A foreach step's input is {"source": "#{_ref(...)}"} and must resolve to a list.
- An if/elsif input is a condition tree:
    {"lhs": "#{_ref(...)}", "operand": "equals_to", "rhs": "value"}
  or {"type": "compound", "operand": "and"|"or", "conditions": [<leaves>]}
  Operands: equals_to, not_equals_to, present, blank, contains, not_contains,
  starts_with, ends_with, greater_than, less_than, is_true, is_not_true.
- Formula expressions inside #{...} use Ruby-flavored Workato syntax.
- Do NOT invent providers or operations outside the schemas above.
- Metadata (number, uuid, toggleCfg, extended_*_schema, ...) is filled by the
  harness - omit it.

## Output
Return ONLY the recipe JSON object ({"recipe": {...}}). No markdown, no prose.
"""


def _action_lines(catalog, ids, mode, allowed):
    rows = []
    if mode == "used":
        keys = [tuple(i.split("::", 1)) for i in ids if "::" in i]
    else:
        keys = [k for k in catalog if k[0] in set(allowed)]
    for k in sorted(set(keys)):
        r = catalog.get(k)
        if not r:
            continue
        rows.append({
            "keyword": r["keyword"], "provider": r["provider"], "name": r["name"],
            "required_input_fields": r["required_input_fields"],
            "optional_input_fields": r["optional_input_fields"][:25],
            "output_fields": [f["name"] for f in r.get("output_schema") or []][:30],
        })
    return json.dumps(rows, indent=1, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog-mode", choices=("allowed", "used"), default="allowed")
    args = ap.parse_args()

    common.ensure_dirs()
    from test_sandbox.benchmark_v1.build_catalog import load_catalog
    catalog = load_catalog()
    with open(os.path.join(common.SCHEMAS_DIR, "control_flow.json")) as f:
        controls = json.load(f)
    controls_txt = json.dumps(
        [{k: c[k] for k in ("keyword", "required_input_fields", "description")}
         for c in controls], indent=1)

    tasks = common.read_jsonl(common.MAIN_TASKS)
    rows = []
    for t in tasks:
        prompt = _HEADER % {
            "description": t["description"],
            "runtime_inputs": json.dumps(t["runtime_inputs"], indent=1),
            "allowed": ", ".join(t["allowed_connectors"]),
            "actions": _action_lines(catalog, t["action_catalog_ids"],
                                     args.catalog_mode, t["allowed_connectors"]),
            "controls": controls_txt,
        }
        with open(os.path.join(common.PROMPTS_DIR, "%s.txt" % t["task_id"]), "w") as f:
            f.write(prompt)
        rows.append({"task_id": t["task_id"], "prompt": prompt})
    common.write_jsonl(os.path.join(common.TASKS_DIR, "prompts.jsonl"), rows)
    print("prompts: %d (-%s catalog) -> %s"
          % (len(rows), args.catalog_mode, common.PROMPTS_DIR))


if __name__ == "__main__":
    main()
