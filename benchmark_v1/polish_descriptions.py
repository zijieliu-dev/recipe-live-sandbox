#!/usr/bin/env python3
"""
polish_descriptions.py - intent-level natural-language task descriptions.

Rewrites the deterministic template descriptions in tasks/main_1k.jsonl into
goal-oriented natural language via the Claude Batches API, with a scripted
faithfulness verifier. The "Expected observable behavior" contract section is
NEVER given to the model to rewrite - it is split off and re-attached
verbatim. A task whose rewrite drops a required behavioral fact falls back to
the template and lands in the repair queue.

Pipeline (each stage writes its artifact under nl_descriptions/):
  python3 polish_descriptions.py extract              # requirements per task
  python3 polish_descriptions.py submit [--limit N] [--ids FILE]
  python3 polish_descriptions.py collect              # poll + validate
  python3 polish_descriptions.py repair               # re-submit failures with explicit must-include list
  python3 polish_descriptions.py merge                # add description_natural to tasks/main_1k.jsonl

Requires ANTHROPIC_API_KEY (env or ../.env). Run under a python with the
`anthropic` package (e.g. /tmp/nlenv/bin/python) for submit/collect/repair;
extract/merge are stdlib-only.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks", "main_1k.jsonl")
RECIPES_DIR = os.path.join(HERE, "..", "recipes_clean")
GOLD = os.path.join(HERE, "gold", "groundtruth_effects.jsonl")
OUT_DIR = os.path.join(HERE, "nl_descriptions")
REQS = os.path.join(OUT_DIR, "requirements.jsonl")
BATCH_STATE = os.path.join(OUT_DIR, "batch_state.json")
RESULTS = os.path.join(OUT_DIR, "descriptions_natural.jsonl")
FAILURES = os.path.join(OUT_DIR, "coverage_failures.jsonl")

MODEL = "claude-opus-4-8"
CONTRACT_MARK = "Expected observable behavior"

SYSTEM = """You rewrite mechanical, auto-generated automation task descriptions into natural, intent-level task descriptions, as a knowledgeable operations engineer would write them for a colleague who must BUILD the automation from scratch.

Rules:
1. Describe the GOAL and the REQUIRED BEHAVIOR: what triggers the automation, what conditions/branches it must honor, what it writes where and with what content. Do NOT prescribe the step-by-step operation sequence, step numbers, or internal variable plumbing - the builder chooses the implementation.
2. PRESERVE EVERY BEHAVIORAL FACT: every literal value the automation embeds (channel names, project/issue types, message wording, field values, condition thresholds, URLs, sheet/tab names, label values) must appear in your rewrite, verbatim where it is content the automation writes. Which data fields flow from the trigger or from read data into each write must remain unambiguous.
3. Do not invent behavior, data, or context that is not in the source description.
4. Write 1-3 paragraphs of flowing prose (bullet lists allowed only for genuinely parallel write contents). No headers. Do not mention "the original recipe", "the template", or these instructions.
5. Connector/provider names you may mention naturally (e.g. "post a Slack message", "create a Jira issue"), since the builder knows which connectors are allowed."""

USER_TMPL = """Rewrite the following auto-generated automation task description into an intent-level description per your rules. Output only via the required JSON schema.

<auto_generated_description>
{narrative}
</auto_generated_description>

The runtime inputs provided separately to the builder (do not re-enumerate them, but you may reference them): {runtime_inputs}
{must_include}"""

SCHEMA = {
    "type": "object",
    "properties": {"description": {"type": "string"}},
    "required": ["description"],
    "additionalProperties": False,
}

_ANON_RX = re.compile(r"</?anon>")
_REF_RX = re.compile(r"#\{_ref\([^}]*\)\}|=\s*_ref\(")


def norm(s):
    return re.sub(r"\s+", " ", _ANON_RX.sub("", str(s))).strip().lower()


def split_desc(desc):
    i = desc.find(CONTRACT_MARK)
    if i < 0:
        return desc, ""
    return desc[:i].rstrip(), desc[i:]


def load_env_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    envp = os.path.join(HERE, "..", ".env")
    if os.path.exists(envp):
        for line in open(envp):
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1]
                return


def read_jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p) if l.strip()]


def write_jsonl(p, rows):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- extract --
def recipe_literals(rid):
    """All literal strings embedded in the recipe's step inputs (no refs)."""
    p = os.path.join(RECIPES_DIR, "%s.json" % rid)
    doc = json.load(open(p))
    out = set()

    def walk(v):
        if isinstance(v, str):
            if not _REF_RX.search(v) and len(v.strip()) >= 3:
                out.add(norm(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    rec = doc.get("recipe") or doc

    def steps(s):
        walk(s.get("input"))
        for c in s.get("block") or []:
            steps(c)

    steps(rec)
    return out


def effect_strings(scenarios):
    """String leaves of canonical effects (content the run actually wrote)."""
    out = set()

    def walk(v):
        if isinstance(v, str) and len(v.strip()) >= 3:
            out.add(norm(v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    for s in scenarios:
        walk(s.get("effects_canonical"))
    return out


_GENERIC = {"true", "false", "none", "null", "task", "medium", "logical.jira.project",
            "logical.sheets.main", "logical.sheets.spreadsheet",
            "logical.slack.bench_channel", "<jira_issue_key>", "<thread>"}


def required_tokens(task, gold_row):
    """Recipe-embedded literals that surface in gold effects: these are
    behavioral content the description must carry (refs/fixture data flow at
    runtime and need not be spelled out; runtime inputs are given separately)."""
    lits = recipe_literals(task["source_recipe_id"])
    effs = effect_strings(gold_row["scenarios"])
    ri = norm(json.dumps(task.get("runtime_inputs") or {}))
    req = set()
    for e in effs:
        if e in _GENERIC or e in ri:
            continue
        for lit in lits:
            if e == lit or (len(e) >= 8 and e in lit):
                req.add(e)
                break
    # cap pathological cases (huge value matrices); keep the longest = most specific
    return sorted(req, key=len, reverse=True)[:40]


def cmd_extract(args):
    by_rid = {g["recipe_id"]: g for g in read_jsonl(GOLD)}
    rows = []
    for t in read_jsonl(TASKS):
        g = by_rid.get(t["source_recipe_id"])
        narrative, contract = split_desc(t["description"])
        req = required_tokens(t, g) if g else []
        rows.append({"task_id": t["task_id"], "narrative": narrative,
                     "contract": contract, "required_tokens": req,
                     "runtime_inputs": t.get("runtime_inputs") or {}})
    write_jsonl(REQS, rows)
    n_req = sum(len(r["required_tokens"]) for r in rows)
    print("wrote %d requirement rows (%d required tokens total) -> %s"
          % (len(rows), n_req, REQS))


# ----------------------------------------------------------------- submit --
def build_request(r, must_include=None):
    mi = ""
    if must_include:
        mi = ("\nYour rewrite MUST contain each of these literal values "
              "verbatim (they are behavioral content):\n" +
              "\n".join("- %s" % t for t in must_include))
    return {
        "custom_id": r["task_id"],
        "params": {
            "model": MODEL,
            "max_tokens": 16000,
            "thinking": {"type": "adaptive"},
            "system": [{"type": "text", "text": SYSTEM,
                        "cache_control": {"type": "ephemeral"}}],
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": USER_TMPL.format(
                narrative=r["narrative"],
                runtime_inputs=json.dumps(r["runtime_inputs"], ensure_ascii=False),
                must_include=mi)}],
        },
    }


def cmd_submit(args):
    import anthropic
    load_env_key()
    client = anthropic.Anthropic()
    reqs = read_jsonl(REQS)
    if args.ids:
        ids = {l.strip() for l in open(args.ids) if l.strip()}
        reqs = [r for r in reqs if r["task_id"] in ids]
    if args.limit:
        reqs = reqs[: args.limit]
    # always pass the full required literals: the template narrative
    # truncates long values, so this is the only complete source
    batch = client.messages.batches.create(
        requests=[build_request(r, must_include=r["required_tokens"] or None)
                  for r in reqs])
    json.dump({"batch_id": batch.id, "n": len(reqs), "mode": "initial"},
              open(BATCH_STATE, "w"))
    print("submitted batch %s with %d requests" % (batch.id, len(reqs)))


# ---------------------------------------------------------------- collect --
def validate(task_id, text, reqs_by_id):
    r = reqs_by_id[task_id]
    nd = norm(text)
    missing = [t for t in r["required_tokens"] if t not in nd]
    return missing


def cmd_collect(args):
    import anthropic
    import time
    load_env_key()
    client = anthropic.Anthropic()
    state = json.load(open(BATCH_STATE))
    bid = state["batch_id"]
    while True:
        b = client.messages.batches.retrieve(bid)
        if b.processing_status == "ended":
            break
        print("status=%s processing=%d" % (b.processing_status,
                                           b.request_counts.processing),
              file=sys.stderr)
        time.sleep(30)
    reqs_by_id = {r["task_id"]: r for r in read_jsonl(REQS)}
    ok = {r["task_id"]: r for r in read_jsonl(RESULTS)}
    failures, n_err = [], 0
    for result in client.messages.batches.results(bid):
        tid = result.custom_id
        if result.result.type != "succeeded":
            n_err += 1
            failures.append({"task_id": tid, "reason": result.result.type})
            continue
        msg = result.result.message
        if msg.stop_reason == "refusal":
            n_err += 1
            failures.append({"task_id": tid, "reason": "refusal"})
            continue
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            desc = json.loads(text)["description"]
        except Exception:
            failures.append({"task_id": tid, "reason": "bad_json"})
            continue
        missing = validate(tid, desc, reqs_by_id)
        if missing:
            failures.append({"task_id": tid, "reason": "missing_tokens",
                             "missing": missing})
            continue
        ok[tid] = {"task_id": tid, "description_natural":
                   desc.rstrip() + "\n\n" + reqs_by_id[tid]["contract"]}
    write_jsonl(RESULTS, list(ok.values()))
    write_jsonl(FAILURES, failures)
    print("collected: %d ok, %d failed (%d api errors) -> %s / %s"
          % (len(ok), len(failures), n_err, RESULTS, FAILURES))


# ----------------------------------------------------------------- repair --
def cmd_repair(args):
    import anthropic
    load_env_key()
    client = anthropic.Anthropic()
    reqs_by_id = {r["task_id"]: r for r in read_jsonl(REQS)}
    fails = read_jsonl(FAILURES)
    if not fails:
        print("no failures to repair")
        return
    requests = []
    for f in fails:
        r = reqs_by_id[f["task_id"]]
        requests.append(build_request(r, must_include=f.get("missing")
                                      or r["required_tokens"]))
    batch = client.messages.batches.create(requests=requests)
    json.dump({"batch_id": batch.id, "n": len(requests), "mode": "repair"},
              open(BATCH_STATE, "w"))
    print("submitted repair batch %s with %d requests" % (batch.id, len(requests)))


# ------------------------------------------------------------------ merge --
def cmd_merge(args):
    nat = {r["task_id"]: r["description_natural"] for r in read_jsonl(RESULTS)}
    tasks = read_jsonl(TASKS)
    n = 0
    for t in tasks:
        if t["task_id"] in nat:
            t["description_natural"] = nat[t["task_id"]]
            n += 1
    write_jsonl(TASKS, tasks)
    print("merged description_natural into %d/%d tasks (template kept in "
          "'description'; tasks without a verified rewrite have no "
          "description_natural field)" % (n, len(tasks)))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("extract")
    sp = sub.add_parser("submit")
    sp.add_argument("--limit", type=int, default=0)
    sp.add_argument("--ids")
    sub.add_parser("collect")
    sub.add_parser("repair")
    sub.add_parser("merge")
    args = ap.parse_args()
    {"extract": cmd_extract, "submit": cmd_submit, "collect": cmd_collect,
     "repair": cmd_repair, "merge": cmd_merge}[args.cmd](args)


if __name__ == "__main__":
    main()
