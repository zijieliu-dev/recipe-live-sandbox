"""normalize_recipe.py - turn a model-emitted recipe into a runnable one
WITHOUT changing semantics.

Fixes (non-semantic metadata only):
  - accept {"recipe": {...}} or a bare trigger tree; wrap in the doc envelope
  - renumber steps depth-first from 1
  - fill missing uuid / as alias (deterministic), keep model-chosen aliases
  - fill skip / toggleCfg / dynamicPickListSelection / extended_*_schema
  - coerce missing `input` to {} and missing `block` to []

Rejects (semantic errors - never repaired):
  - root is not a trigger / unparseable structure   -> RecipeNormalizationError
  - unknown provider, unknown operation (vs the action catalog)
  - provider outside the task's allowed connectors
  - action without provider/name
  - foreach without an input.source
  - if/elsif without a condition input
  - _ref(...) to an alias no step defines
  (returned as a schema_errors list by validate())
"""
import uuid as uuidlib

from test_sandbox.engine import loader, refs
from test_sandbox.benchmark_v1.common import stable_hash

_CONTROL = {"if", "elsif", "else", "foreach", "repeat", "while_condition",
            "try", "catch", "stop"}
_PRIMITIVES_OK = {"clock", "json_parser", "csv_parser", "yaml_parser", "logger",
                  "lookup_table", "workato_variable", "workato_list",
                  "workato_smart_list", "workato_db_table", "email", "utility",
                  "workato_files", "file_connector", "js_eval", "py_eval",
                  "workato_custom_code", "workato_mapper", "workato_transformations"}


class RecipeNormalizationError(Exception):
    pass


class RecipeNormalizer:
    def __init__(self, catalog=None):
        """catalog: {(provider, name) -> row} from build_catalog.load_catalog()."""
        self.catalog = catalog or {}

    # -- entry ---------------------------------------------------------------
    def normalize(self, raw):
        recipe = self.ensure_envelope(raw)
        self.fill_defaults(recipe)
        self.assign_numbers(recipe)
        self.assign_missing_aliases(recipe)
        self.assign_missing_uuids(recipe)
        return {"id": "candidate", "recipe": recipe}

    # -- structure -----------------------------------------------------------
    def ensure_envelope(self, raw):
        if not isinstance(raw, dict):
            raise RecipeNormalizationError("recipe output must be a JSON object")
        node = raw.get("recipe", raw)
        if isinstance(node, dict) and node.get("keyword") != "trigger" \
                and isinstance(node.get("recipe"), dict):
            node = node["recipe"]                      # double-wrapped
        if not isinstance(node, dict) or node.get("keyword") != "trigger":
            raise RecipeNormalizationError(
                "recipe root must be a step with keyword='trigger'")
        return node

    def _walk(self, node, fn, depth=0):
        if not isinstance(node, dict):
            return
        fn(node, depth)
        for child in (node.get("block") or []):
            self._walk(child, fn, depth + 1)

    def fill_defaults(self, recipe):
        def fix(step, _depth):
            if not isinstance(step.get("input"), (dict, type(None))):
                # tolerate list/scalar inputs only where the grammar uses them
                pass
            if step.get("input") is None:
                step["input"] = {}
            if not isinstance(step.get("block"), list):
                step["block"] = []
            step.setdefault("skip", False)
            step.setdefault("comment", "")
            step.setdefault("toggleCfg", {})
            step.setdefault("dynamicPickListSelection", {})
            step.setdefault("extended_input_schema", [])
            step.setdefault("extended_output_schema", [])
        self._walk(recipe, fix)

    def assign_numbers(self, recipe):
        counter = {"n": 0}

        def fix(step, _depth):
            counter["n"] += 1
            step["number"] = counter["n"]
        self._walk(recipe, fix)

    def assign_missing_aliases(self, recipe):
        seen = set()

        def fix(step, _depth):
            a = step.get("as")
            if not isinstance(a, str) or not a or a in seen:
                base = "s%02d" % step["number"]
                a = base if (not isinstance(a, str) or not a) \
                    else "%s_%s" % (a, step["number"])
                while a in seen:
                    a += "x"
                step["as"] = a
            seen.add(step["as"])
        self._walk(recipe, fix)

    def assign_missing_uuids(self, recipe):
        def fix(step, _depth):
            if not step.get("uuid"):
                step["uuid"] = str(uuidlib.UUID(
                    stable_hash("bench::%s::%s" % (step["number"],
                                                   step.get("as")), 32)))
        self._walk(recipe, fix)

    # -- semantic validation (NO repair) --------------------------------------
    def validate(self, recipe, allowed_connectors=None):
        """Returns (errors, warnings).

        errors   - hallucination signals that fail the candidate outright:
                   unknown keyword/provider/operation, disallowed connector.
        warnings - structural smells the engine tolerates (the ORIGINAL corpus
                   contains them too: dangling refs, vestigial actions, foreach
                   without source). Reported for diagnostics; execution
                   equivalence decides whether they matter."""
        errors, warnings = [], []
        aliases = set()
        known_providers = ({p for p, _ in self.catalog} | _PRIMITIVES_OK)
        allowed = set(allowed_connectors or [])

        def check(step, _depth):
            kw = step.get("keyword")
            if kw not in loader.STEP_KEYWORDS:
                errors.append("unknown keyword %r (step %s)" % (kw, step.get("number")))
                return
            if step.get("as"):
                aliases.add(step["as"])
            if kw in ("trigger", "action"):
                prov, name = step.get("provider"), step.get("name")
                if not prov or not name:
                    warnings.append("step %s: %s missing provider/name"
                                    % (step.get("number"), kw))
                    return
                if self.catalog and (prov, name) not in self.catalog \
                        and prov not in _PRIMITIVES_OK:
                    if prov not in known_providers:
                        errors.append("step %s: unknown provider %r"
                                      % (step.get("number"), prov))
                    else:
                        errors.append("step %s: unknown operation %s::%s"
                                      % (step.get("number"), prov, name))
                if allowed and prov not in allowed and prov not in _PRIMITIVES_OK:
                    errors.append("step %s: provider %r not allowed for this task"
                                  % (step.get("number"), prov))
            elif kw == "foreach":
                src = (step.get("input") or {}).get("source")
                if not src:
                    warnings.append("step %s: foreach without input.source"
                                    % step.get("number"))
                elif isinstance(src, str) and "_ref(" not in src and "#{" not in src:
                    warnings.append("step %s: foreach source is not a reference/"
                                    "formula expression" % step.get("number"))
            elif kw in ("if", "elsif"):
                if not step.get("input"):
                    warnings.append("step %s: %s without a condition input"
                                    % (step.get("number"), kw))
        self._walk(recipe, check)

        # reference targets must exist somewhere in the recipe
        bad = set()

        def scan(node):
            if isinstance(node, str) and "_ref(" in node:
                for r in refs.find_refs(node):
                    line = r["line"]
                    if not isinstance(line, str):
                        continue       # null alias: resolves to MISSING, same for gold
                    if line not in aliases and line not in (
                            "job_context", "workato", "account_property"):
                        bad.add(line)
            elif isinstance(node, list):
                for x in node:
                    scan(x)
            elif isinstance(node, dict):
                for v in node.values():
                    scan(v)
        scan(recipe)
        for b in sorted(bad):
            warnings.append("reference to nonexistent step alias %r" % b)
        return errors, warnings
