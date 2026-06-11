#!/usr/bin/env python3
"""
build_catalog.py - Stage 1: the model's "tool manual".

From manifest_schemas.json (provider::operation -> first-seen input/output
schema, built by ../manifest.py) and the recipes' usage counts, emit:

  schemas/action_catalog.jsonl     one atomic action schema per provider::op
  schemas/provider_catalog.jsonl   one row per provider (ops + usage)
  schemas/control_flow.json        the control-flow block schemas
  schemas/recipe_minimal_schema.json   the model OUTPUT contract (JSON Schema)

Only atomic action/control-flow schemas are stored - never recipe fragments -
so the benchmark tests generation, not retrieval.

Usage:  python3 build_catalog.py
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.benchmark_v1 import common  # noqa: E402

_MAX_SCHEMA_DEPTH = 3
_MAX_FIELDS = 40


def trim_schema(schema, depth=0):
    """Keep only {name, type, optional, properties} from a Workato field list,
    recursing a bounded depth so catalog rows stay prompt-sized."""
    if not isinstance(schema, list):
        return []
    out = []
    for f in schema[:_MAX_FIELDS]:
        if not isinstance(f, dict) or not f.get("name"):
            continue
        row = {"name": f["name"], "type": f.get("type") or "string"}
        if f.get("optional") is False:
            row["optional"] = False
        props = f.get("properties")
        if props and depth < _MAX_SCHEMA_DEPTH and row["type"] in ("object", "array"):
            row["properties"] = trim_schema(props, depth + 1)
        out.append(row)
    return out


def required_fields(input_schema):
    return [f["name"] for f in (input_schema or [])
            if isinstance(f, dict) and f.get("name") and f.get("optional") is False]


def optional_fields(input_schema):
    return [f["name"] for f in (input_schema or [])
            if isinstance(f, dict) and f.get("name") and f.get("optional") is not False]


def humanize(provider, name, keyword):
    words = str(name or "").replace("_", " ").strip()
    if keyword == "trigger":
        return "Trigger: fires on '%s' events from %s." % (words, provider)
    return "%s: %s." % (provider, words or "operation")


CONTROL_FLOW = [
    {"catalog_id": "control.foreach", "keyword": "foreach",
     "required_input_fields": ["source"], "optional_input_fields": [],
     "description": "Iterate over an array and run the nested `block` steps once per item. "
                    "`input.source` must be a #{_ref(...)} expression resolving to a list. "
                    "Inside the loop, reference the current item with a path element "
                    "{\"path_element_type\": \"current_item\"} against the foreach step's alias."},
    {"catalog_id": "control.if", "keyword": "if",
     "required_input_fields": ["conditions"], "optional_input_fields": ["operand"],
     "description": "Run the nested `block` steps when the condition tree is true. "
                    "`input` is a condition tree: either a leaf "
                    "{\"lhs\": \"#{...}\", \"operand\": \"equals_to|not_equals_to|present|blank|"
                    "contains|greater_than|less_than\", \"rhs\": <value>} or a compound "
                    "{\"type\": \"compound\", \"operand\": \"and|or\", \"conditions\": [...]}. "
                    "An `elsif`/`else` step, when used, is the LAST child inside this step's `block`."},
    {"catalog_id": "control.elsif", "keyword": "elsif",
     "required_input_fields": ["conditions"], "optional_input_fields": [],
     "description": "Alternative conditional branch; appears only as the last child of an "
                    "`if`/`elsif` block. Same condition-tree input as `if`."},
    {"catalog_id": "control.else", "keyword": "else",
     "required_input_fields": [], "optional_input_fields": [],
     "description": "Fallback branch; appears only as the last child of an `if`/`elsif` block."},
    {"catalog_id": "control.stop", "keyword": "stop",
     "required_input_fields": [], "optional_input_fields": ["reason", "error"],
     "description": "Stop the recipe run immediately (terminal status 'stopped')."},
    {"catalog_id": "control.try", "keyword": "try",
     "required_input_fields": [], "optional_input_fields": [],
     "description": "Run nested steps; on a step error, run the trailing `catch` step's "
                    "block instead of failing the recipe. A `catch` step, when used, is the "
                    "LAST child inside this step's `block`."},
    {"catalog_id": "control.catch", "keyword": "catch",
     "required_input_fields": [], "optional_input_fields": [],
     "description": "Error handler; appears only as the last child of a `try` block."},
    {"catalog_id": "control.repeat", "keyword": "repeat",
     "required_input_fields": [], "optional_input_fields": [],
     "description": "Do-while loop; the trailing `while_condition` child holds the condition."},
]

RECIPE_MINIMAL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "benchmark_v1 model output contract",
    "type": "object",
    "required": ["recipe"],
    "properties": {
        "recipe": {"$ref": "#/definitions/trigger_step"},
    },
    "definitions": {
        "trigger_step": {
            "type": "object",
            "required": ["keyword", "provider", "name", "block"],
            "properties": {
                "keyword": {"const": "trigger"},
                "provider": {"type": "string"},
                "name": {"type": "string"},
                "as": {"type": "string", "description": "alias other steps reference; optional (harness fills)"},
                "input": {"type": "object"},
                "block": {"type": "array", "items": {"$ref": "#/definitions/step"}},
            },
        },
        "step": {
            "type": "object",
            "required": ["keyword"],
            "properties": {
                "keyword": {"enum": ["action", "if", "elsif", "else", "foreach",
                                     "repeat", "while_condition", "try", "catch", "stop"]},
                "provider": {"type": "string", "description": "required when keyword=action"},
                "name": {"type": "string", "description": "required when keyword=action"},
                "as": {"type": "string"},
                "input": {"type": ["object", "null"]},
                "block": {"type": "array", "items": {"$ref": "#/definitions/step"}},
            },
        },
    },
    "notes": [
        "Metadata fields (number, uuid, toggleCfg, dynamicPickListSelection, "
        "extended_input_schema, extended_output_schema, skip, comment, flow_id, ...) "
        "are OPTIONAL: the harness normalizer fills them. Do not rely on them.",
        "Reference a previous step's output with "
        "#{_ref(\"<provider>\",\"<as-alias>\",[\"field\",...])} inside string inputs.",
        "Reference the current foreach item with "
        "#{_ref(\"<provider>\",\"<foreach-alias>\",[{\"path_element_type\":\"current_item\"},\"field\"])}.",
        "Formula expressions inside #{...} use Workato's Ruby-flavored syntax.",
    ],
}


def main():
    common.ensure_dirs()
    with open(common.MANIFEST_SCHEMAS) as f:
        schemas = json.load(f)

    # usage counts + keyword (trigger vs action) per provider::op from the corpus
    usage = Counter()
    kw_of = {}
    ids = sorted(f[:-5] for f in os.listdir(common.RECIPES_DIR) if f.endswith(".json"))
    for rid in ids:
        try:
            doc = common.load_recipe_doc(rid)
        except Exception:
            continue
        for s in common.iter_steps(doc.get("recipe") or {}):
            prov, name, kw = s.get("provider"), s.get("name"), s.get("keyword")
            if prov and name and kw in ("trigger", "action"):
                key = "%s::%s" % (prov, name)
                usage[key] += 1
                # a name used as both keeps 'trigger' (rare); first-seen otherwise
                if key not in kw_of or kw == "trigger":
                    kw_of[key] = kw

    actions = []
    for key, sch in schemas.items():
        prov, name = key.split("::", 1)
        ins = sch.get("input_schema") or []
        actions.append({
            "catalog_id": key,
            "keyword": kw_of.get(key, "action"),
            "provider": prov,
            "name": name,
            "required_input_fields": required_fields(ins),
            "optional_input_fields": optional_fields(ins),
            "input_schema": trim_schema(ins),
            "output_schema": trim_schema(sch.get("output_schema") or []),
            "description": humanize(prov, name, kw_of.get(key, "action")),
            "usage_count": usage.get(key, 0),
        })
    actions.sort(key=lambda a: (-a["usage_count"], a["catalog_id"]))

    providers = Counter()
    ops_by_prov = {}
    for a in actions:
        providers[a["provider"]] += a["usage_count"]
        ops_by_prov.setdefault(a["provider"], []).append(a["name"])
    prov_rows = [{"provider": p, "usage_count": c,
                  "n_operations": len(ops_by_prov[p]),
                  "operations": sorted(ops_by_prov[p])}
                 for p, c in providers.most_common()]

    common.write_jsonl(common.ACTION_CATALOG, actions)
    common.write_jsonl(common.PROVIDER_CATALOG, prov_rows)
    with open(os.path.join(common.SCHEMAS_DIR, "control_flow.json"), "w") as f:
        json.dump(CONTROL_FLOW, f, indent=2)
    with open(os.path.join(common.SCHEMAS_DIR, "recipe_minimal_schema.json"), "w") as f:
        json.dump(RECIPE_MINIMAL_SCHEMA, f, indent=2)

    print("action_catalog: %d ops, %d providers -> %s"
          % (len(actions), len(prov_rows), common.SCHEMAS_DIR))


def load_catalog():
    """{(provider, name) -> catalog row} for validation / prompt building."""
    rows = common.read_jsonl(common.ACTION_CATALOG)
    return {(r["provider"], r["name"]): r for r in rows}


if __name__ == "__main__":
    main()
