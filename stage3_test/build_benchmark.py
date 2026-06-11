#!/usr/bin/env python3
"""Build the stage3 live benchmark from groundtruth/.

Two splits (per user decision 2026-06-11):
  * main_1k  - SCORED. Clean only: recipes that ran a live action (read OR write)
               with NO failed live effect. = all clean live-WRITES (truly
               succeeded) + clean READ-ONLY-live. Trimmed to 1000 with a
               diversity rule: keep every write + every non-Slack read, then fill
               with Slack reads (Slack otherwise dominates the pool).
  * partials - NOT scored. The 321 partials, labelled by blocker:
                 platform_limited -> blocked by block_kit_modals (needs a real
                                     Slack trigger_id; interaction-only)
                 mock_blank        -> slack/sheets content came from mocked
                                     upstream steps / blank-by-design
Outputs (in stage3_test/benchmark/): main_1k.jsonl, main_1k_ids.txt,
partials_split.jsonl, partials_split_ids.txt, README.md.
"""
import json
import os
import glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GT = os.path.join(HERE, "groundtruth")
OUT = os.path.join(HERE, "benchmark")
TARGET = 1000

LIVE = {"salesforce", "jira", "jira_service_desk", "slack", "slack_bot", "google_sheets"}
APP = {"salesforce": "SF", "slack": "Slack", "slack_bot": "Slack", "jira": "Jira",
       "jira_service_desk": "Jira", "google_sheets": "Sheets"}


def load_all():
    truly = set(open(os.path.join(HERE, "truly_succeeded_ids.txt")).read().split())
    partial = set(open(os.path.join(HERE, "partial_live_ids.txt")).read().split())
    recs = {}
    for p in glob.glob(os.path.join(GT, "*.json")):
        if p.endswith(("index.jsonl", "summary.json")):
            continue
        d = json.load(open(p))
        if "id" not in d or d.get("status") not in ("completed", "stopped"):
            continue
        recs[str(d["id"])] = d
    return truly, partial, recs


def live_actions(d):
    tr = d.get("output", {}).get("trace") or []
    return [s for s in tr if s.get("keyword") == "action" and s.get("provider") in LIVE]


def apps_of(actions):
    return sorted({APP[s["provider"]] for s in actions})


def primary_app(actions):
    return Counter(APP[s["provider"]] for s in actions).most_common(1)[0][0]


def main():
    os.makedirs(OUT, exist_ok=True)
    truly, partial, recs = load_all()

    writes, reads = [], []
    for rid, d in recs.items():
        la = live_actions(d)
        if not la:
            continue
        entry = {"id": rid, "primary_app": primary_app(la), "apps": apps_of(la),
                 "live_action_steps": len(la), "status": d.get("status")}
        if rid in truly:
            ops = [e["operation"] for e in (d.get("live_effects") or []) if e.get("wrote")]
            entry["tier"] = "live_write"
            entry["live_write_ops"] = sorted(set(ops))
            writes.append(entry)
        elif rid in partial:
            continue
        else:
            entry["tier"] = "live_read"
            reads.append(entry)

    # selection: all writes + all non-Slack reads + fill with Slack reads
    writes.sort(key=lambda e: int(e["id"]))
    reads.sort(key=lambda e: int(e["id"]))
    nonslack = [e for e in reads if e["primary_app"] != "Slack"]
    slack = [e for e in reads if e["primary_app"] == "Slack"]
    need = TARGET - len(writes) - len(nonslack)
    chosen_reads = nonslack + slack[:max(0, need)]
    main = writes + chosen_reads
    main.sort(key=lambda e: int(e["id"]))

    # partials split
    parts = []
    for rid in sorted(partial, key=int):
        d = recs.get(rid)
        if not d:
            continue
        le = d.get("live_effects") or []
        failed = [e for e in le if not e.get("wrote")]
        did_write = any(e.get("wrote") for e in le)
        is_modal = any(e["operation"] == "block_kit_modals" for e in failed)
        la = live_actions(d)
        parts.append({
            "id": rid,
            "label": "platform_limited" if is_modal else "mock_blank",
            "blocker": "block_kit_modals" if is_modal
            else sorted({"%s::%s" % (e["provider"], e["operation"]) for e in failed}),
            "did_live_write": did_write,
            "apps": apps_of(la) if la else [],
            "failed_ops": sorted({"%s::%s" % (e["provider"], e["operation"]) for e in failed}),
        })

    def dump(name, rows):
        with open(os.path.join(OUT, name + ".jsonl"), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        with open(os.path.join(OUT, name + "_ids.txt"), "w") as f:
            f.write("\n".join(r["id"] for r in rows) + "\n")

    dump("main_1k", main)
    dump("partials_split", parts)

    # report
    def by(rows, key):
        c = Counter(r[key] for r in rows)
        return dict(c.most_common())
    main_tier = by(main, "tier")
    main_app = by(main, "primary_app")
    part_label = by(parts, "label")
    write_readme(main_tier, main_app, part_label, len(main), len(parts))
    print("main_1k:", len(main), "tier:", main_tier, "primary_app:", main_app)
    print("partials_split:", len(parts), "label:", part_label)


def write_readme(main_tier, main_app, part_label, n_main, n_part):
    txt = """# Stage-3 live benchmark

Built by `build_benchmark.py` from `groundtruth/`. Two splits.

## main_1k  (SCORED, n=%d)
Recipes that executed at least one **live action** (a real Salesforce / Slack /
Jira / Google-Sheets read or write) and had **no failed live effect** — i.e. they
cleanly exercised the real software. Use this as the scored benchmark.

Per-recipe fields: `id`, `tier`, `primary_app`, `apps`, `live_action_steps`,
`status`, and (for writes) `live_write_ops`.

- `tier`: %s
- `primary_app`: %s

"Read-only" recipes (`tier=live_read`) genuinely hit the live API but only read
(no write side-effect) — accepted as success per the benchmark definition.

Selection: all clean live-writes + all non-Slack clean reads + Slack reads to
fill 1000 (Slack is ~46%% of the clean pool; this trims it for connector
diversity). Deterministic by id.

## partials_split  (NOT scored, n=%d)
Recipes that landed some live effect but had a blocked one. Kept as a labelled
platform-limited / stress split — **not counted as success**.

- `label`:
  - `platform_limited` — blocked by `block_kit_modals`, which needs a real,
    single-use Slack `trigger_id` from a live interaction (no API to mint one).
    These genuinely exercise live Slack; the modal-open is a Slack platform limit.
  - `mock_blank` — a Slack/Sheets write whose content came from mocked upstream
    steps returning empty, or was blank-by-design. Not honestly fixable in batch.
- label counts: %s

Per-recipe fields: `id`, `label`, `blocker`, `did_live_write`, `apps`, `failed_ops`.
""" % (n_main, main_tier, main_app, n_part, part_label)
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(txt)


if __name__ == "__main__":
    main()
