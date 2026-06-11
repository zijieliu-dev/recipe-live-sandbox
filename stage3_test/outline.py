#!/usr/bin/env python3
"""
outline.py - print a cleaned recipe's step tree with the input fields each action
sends and the trigger datapills that feed them. Used to craft live input bundles.

  python3 stage3_test/outline.py <recipe-id> [--full]
"""
import json, os, sys, re
sys.path.insert(0, "/home/zijie")
from test_sandbox.engine import loader, refs

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(HERE, "recipes_clean")


def short(v, n=70):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


def trig_refs_in(val, trig_alias):
    """Return the list of trigger paths referenced in a string value."""
    out = []
    if isinstance(val, str):
        for r in refs.find_refs(val):
            if r["line"] == trig_alias:
                path = ".".join(str(p) for p in r["path"] if isinstance(p, str))
                out.append(path or "(root)")
    return out


def walk(node, depth, trig_alias, full):
    if not loader.is_step(node):
        return
    kw = node.get("keyword"); num = node.get("number")
    prov = node.get("provider") or ""
    name = node.get("name") or ""
    head = "%s%2s %-8s %s/%s" % ("  " * depth, num, kw, prov, name)
    print(head)
    inp = node.get("input")
    if isinstance(inp, dict):
        for k, v in inp.items():
            tr = trig_refs_in(v, trig_alias) if isinstance(v, str) else []
            if full or tr or k in ("sobject_name", "project_issuetype", "channel",
                                   "summary", "description", "body", "key", "issuekey",
                                   "id", "query", "jql", "email", "text", "message"):
                tag = ("  <= trigger." + ",".join(tr)) if tr else ""
                print("       %-22s = %s%s" % (k, short(v), tag))
    for v in node.values():
        if isinstance(v, list):
            for x in v:
                walk(x, depth + 1, trig_alias, full)


def main():
    rid = sys.argv[1]
    full = "--full" in sys.argv
    doc = json.load(open(os.path.join(CLEAN, "%s.json" % rid)))
    r = doc["recipe"]
    t = loader.get_trigger(r) or {}
    print("# Recipe %s  trigger=%s/%s  alias=%s" % (rid, t.get("provider"), t.get("name"), t.get("as")))
    # trigger's own input (config/filter) is useful context
    walk(r, 0, t.get("as"), full)


if __name__ == "__main__":
    main()
