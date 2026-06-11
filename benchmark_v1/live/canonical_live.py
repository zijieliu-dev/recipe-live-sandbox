"""canonical_live.py - normalize live read-back results into comparable
canonical effects.

Real systems mint different ids on every run, so original and candidate can
only compare after normalization:
  - physical resource ids -> logical names via the namespace resource map
    (bench tab -> logical.sheets.main, bench channel -> logical.slack.bench_channel);
  - dynamic identifiers -> placeholders: <JIRA_ISSUE_KEY>, <TS>, <SF_ID>, <URL_ID>;
  - run markers (B<rid>_<scen>_<side>) -> stripped everywhere;
  - whitespace collapsed; Jira ADF descriptions flattened to plain text.

The REQUESTED target (what the recipe asked for, pre-rebinding) is the
canonical target - both sides request the same thing, the physical namespace
is an environment detail.
"""
import re

from test_sandbox.benchmark_v1.canonicalizers import generic

_TS_RX = re.compile(r"\b1\d{9}\.\d{4,6}\b")                  # slack ts
_SFID_RX = re.compile(r"\b[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?\b")


def _marker_rx(ns):
    rid = re.escape(str(ns["recipe_id"]))
    return re.compile(r"\bB%s_\w+\b" % rid)


def _key_rx(ns):
    return re.compile(r"\b%s-\d+\b" % re.escape(ns["jira_project"] or "ZZNONE"))


def norm_text(s, ns):
    if s is None:
        return ""
    s = str(s)
    s = _marker_rx(ns).sub("", s)
    s = _key_rx(ns).sub("<JIRA_ISSUE_KEY>", s)
    s = _TS_RX.sub("<TS>", s)
    return generic.norm_text(s)


def map_logical(value, resource_map):
    if value is None:
        return None
    return resource_map.get(str(value), str(value))


def adf_to_text(node):
    """Flatten a Jira ADF document (API v3 description) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    parts = []

    def rec(n):
        if isinstance(n, dict):
            if isinstance(n.get("text"), str):
                parts.append(n["text"])
            for c in n.get("content") or []:
                rec(c)
        elif isinstance(n, list):
            for c in n:
                rec(c)
    rec(node)
    return " ".join(parts)


def scrub_value(v, ns):
    """Normalize a scalar cell/field value (used for sheet cells, SF fields)."""
    if isinstance(v, str):
        return norm_text(v, ns)
    return v
