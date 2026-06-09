#!/usr/bin/env python3
"""
run_stage1.py - run the stage-1 recipes against the LIVE org, one sample at a
time, each wrapped in tracked teardown so the org returns to its prior state.

Per recipe x sample:
  TrackedClient(live) -> run recipe (Salesforce live, others mocked) -> teardown

Writes stage1_test/<id>/results.md and prints a summary. Salesforce reads hit
the real org; writes are tracked and undone by teardown.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.engine import interpreter, loader            # noqa: E402
from test_sandbox.engine.context import RunContext             # noqa: E402
from test_sandbox.salesforce_live import SalesforceClient, SalesforceError  # noqa: E402
from test_sandbox.live import salesforce as live               # noqa: E402
from test_sandbox.live.tracker import TrackedClient            # noqa: E402
from test_sandbox.live.realize import realize_trigger, realize_sf_trigger  # noqa: E402

N_SAMPLES = 10                                                  # realized live samples/recipe

WRITE_OPS = {"delete_sobject", "update_sobject", "composite_update_sobject",
             "updated_custom_object", "upsert_sobject"}


def write_targets(recipe):
    """Salesforce objects a write recipe operates on (for the init table)."""
    out = []
    for s in loader.iter_steps(recipe):
        if s.get("provider") == "salesforce" and s.get("name") in WRITE_OPS:
            sob = (s.get("input") or {}).get("sobject_name")
            if sob and sob not in out:
                out.append(sob)
    return out

_SYS = {"attributes", "Id", "IsDeleted", "CreatedDate", "CreatedById",
        "LastModifiedDate", "LastModifiedById", "SystemModstamp",
        "LastViewedDate", "LastReferencedDate"}


def _snapshot(client, sobject, rid):
    """Current non-null field values of a record (None if it doesn't exist)."""
    try:
        rec = client.get(sobject, rid)
    except SalesforceError:
        return None
    return {k: v for k, v in rec.items() if v not in (None, "") and k not in _SYS}


def _read_examples(ctx):
    """For each live SF read step: row count + one example row."""
    out = []
    for o in ctx.step_outputs.values():
        if isinstance(o, dict) and "count" in o:
            recs = o.get("records") or []
            ex = {k: v for k, v in (recs[0] if recs else {}).items() if k != "attributes"}
            out.append({"count": o["count"], "example": ex})
    return out

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.dirname(HERE)
STAGE1 = os.path.join(os.path.dirname(SANDBOX), "stage1_test")

_JSON = re.compile(r"```json\n(.*?)\n```", re.S)


def parse_samples(md_path):
    out = []
    if not os.path.exists(md_path):
        return out
    for block in _JSON.findall(open(md_path).read()):
        try:
            out.append(json.loads(block))
        except Exception:
            pass
    return out


def sf_activity(ctx):
    """Summarize live SF read outputs captured in step outputs."""
    reads = []
    for out in ctx.step_outputs.values():
        if isinstance(out, dict) and "count" in out:
            reads.append(out["count"])
    return reads


def run():
    client = SalesforceClient.from_cli("my-dev-org")
    selected = json.load(open(os.path.join(HERE, "selected.json")))
    summary = []

    for meta in selected:
        rid = meta["id"]
        recipe = loader.load(os.path.join(SANDBOX, "recipes_clean", "%s.json" % rid))["recipe"]
        trig = loader.get_trigger(recipe)
        alias = trig.get("as") if trig else None
        write_sobs = write_targets(recipe)               # [] for read recipes
        rows = []
        for i in range(N_SAMPLES):
            tracked = TrackedClient(client)
            dispatch = live.make_dispatch(tracked)

            # init table = current rows of the persistent write-target object(s)
            table_ids = {sob: [r["Id"] for r in client.query_all("SELECT Id FROM %s LIMIT 200" % sob)]
                         for sob in write_sobs}
            init_count = {sob: len(ids) for sob, ids in table_ids.items()}
            # the specific row this sample targets (for before/after detail)
            target = None
            for sob in write_sobs:
                if table_ids[sob]:
                    target = (sob, table_ids[sob][i % len(table_ids[sob])])
                    break
            target_before = _snapshot(client, *target) if target else None

            trig_step = loader.get_trigger(recipe) or {}
            try:
                if trig_step.get("provider") == "salesforce":      # SF-triggered: real watched record
                    realized = realize_sf_trigger(tracked, recipe, i)
                    notes = ["SF-triggered: real %s record" %
                             ((trig_step.get("input") or {}).get("sobject_name"))]
                else:
                    realized, notes = realize_trigger(recipe, tracked, alias, i, target_pool=table_ids)
            except Exception as e:
                realized, notes = {}, ["realize failed: %s" % str(e)[:60]]
            ctx = RunContext(fixtures={"trigger": realized, "reads": {}, "config": {}})
            try:
                res = interpreter.run(recipe, ctx, dispatch=dispatch)
                status = res["status"]
            except Exception as e:
                status = "EXC:" + str(e)[:40]

            # state DURING the trial (after recipe, before teardown)
            target_after = _snapshot(client, *target) if target else None
            after_count = {sob: client.query("SELECT COUNT() FROM %s" % sob)["totalSize"] for sob in write_sobs}
            reads = _read_examples(ctx)
            mutations = len(tracked.changes)
            td = tracked.teardown()
            restored = {sob: client.query("SELECT COUNT() FROM %s" % sob)["totalSize"] for sob in write_sobs}

            rows.append({"sample": i + 1, "status": status, "trigger": realized, "notes": notes,
                         "sf_reads": sf_activity(ctx), "reads": reads,
                         "target": target, "target_before": target_before, "target_after": target_after,
                         "init_count": init_count, "after_count": after_count, "restored": restored,
                         "mutations": mutations, "teardown": len(td),
                         "formula_errors": len(ctx.formula_errors)})
        write_samples(meta, rows)
        write_results(meta, rows)
        # NOTE: per-recipe README.md is hand-curated — do NOT overwrite it here.
        ok = sum(1 for r in rows if r["status"] == "completed")
        rowsum = sum(sum(r["sf_reads"]) for r in rows if r["sf_reads"])
        summary.append((rid, meta["readonly"], len(rows), ok,
                        sum(r["mutations"] for r in rows), rowsum))

    print("recipe       mode   samples  completed  real-rows-read  writes(undone)")
    for rid, ro, n, ok, mut, rows_read in summary:
        print("  %-10s %-5s  %5d   %6d   %10d   %8d"
              % (rid, "READ" if ro else "WRITE", n, ok, rows_read, mut))
    print("\nwrote results.md into each stage1_test/<id>/")


def _kv(d, limit=6):
    """Render a dict as a compact `k=v` list (truncated)."""
    if d is None:
        return "_(record does not exist)_"
    items = list(d.items())[:limit]
    s = ", ".join("`%s`=%s" % (k, json.dumps(v, default=str)) for k, v in items)
    if len(d) > limit:
        s += ", …"
    return s or "_(empty)_"


def write_readme(meta, rows):
    write = not meta["readonly"]
    L = ["# Recipe `%s` — %s on %s" % (meta["id"], ", ".join(meta["cats"]),
                                       ", ".join(meta["objects"])), "",
         "**Mode:** %s | **SF operation(s):** %s | **triggered by:** `%s`"
         % ("WRITE (mutates org)" if write else "READ-only",
            ", ".join(meta["ops"]), meta["trigger"]), ""]

    # how reset works
    is_delete = "DELETE" in meta["cats"]
    L += ["## How each run is reset (isolation)", "",
          "A **persistent init database** lives in the org as the baseline "
          "(seeded once via `setup_init_db.py`): 10 Event rows + 10 Contract rows, "
          "alongside the existing Account/Contact/Opportunity data. **Every trial "
          "starts from this same init state.**", "",
          "Each Salesforce write is recorded by a change-tracker; after the trial "
          "it is reversed so the init database is put back:", "",
          "- a **deleted** init row → re-created from its snapshot (same data)",
          "- an **updated** init row → its fields restored",
          "- anything the recipe **created** → deleted", "",
          "So the init table returns to its full row count and the next trial starts "
          "from the identical state.", ""]

    L += ["## Input → Output, per sample (operates on the init table)", ""]
    for r in rows:
        L.append("### Sample %d — `%s`" % (r["sample"], r["status"]))
        trig = json.dumps(r["trigger"], default=str)
        L.append("- **Input (trigger):** `%s`" % (trig if len(trig) < 200 else trig[:200] + "…`"))
        if write and r["target"]:
            sob, tid = r["target"]
            ic = r["init_count"].get(sob, 0)
            ac = r["after_count"].get(sob, 0)
            rc = r["restored"].get(sob, 0)
            L.append("- **Init table:** `%s` has **%d rows** (baseline)" % (sob, ic))
            L.append("- **Targeted row `%s` BEFORE:** %s" % (tid, _kv(r["target_before"])))
            if r["target_after"] is None:
                L.append("- **AFTER recipe:** row **DELETED via live API** ✅ → table now **%d rows**" % ac)
            else:
                b, a = r["target_before"] or {}, r["target_after"]
                changed = {k: a.get(k) for k in a if b.get(k) != a.get(k)}
                L.append("- **AFTER recipe:** row **UPDATED** → %s (table still %d rows)" % (_kv(changed), ac))
            L.append("- **Reset:** %d write(s) reversed → init table restored to **%d rows**" % (r["mutations"], rc))
        elif r["reads"]:
            for rd in r["reads"]:
                L.append("- **Live query on init data:** %d row(s); example: %s"
                         % (rd["count"], _kv(rd["example"])))
            L.append("- **State change:** none (read-only)")
        else:
            L.append("- **State change:** none")
        L.append("")
    open(os.path.join(STAGE1, meta["id"], "README.md"), "w").write("\n".join(L) + "\n")


def write_samples(meta, rows):
    """Overwrite test_samples.md with the REAL inputs used in the live run."""
    L = ["# Test samples — recipe `%s` (realized against live `my-dev-org`)" % meta["id"], "",
         "%d samples. Each trigger payload below is the **actual input fed to the "
         "recipe**, populated with real org data: real filter values fetched from "
         "the org, and real target ids from seeded records." % len(rows), ""]
    for r in rows:
        L.append("## Sample %d" % r["sample"])
        if r["notes"]:
            L.append("Realized from org:")
            for n in r["notes"]:
                L.append("- %s" % n)
        L.append("```json")
        L.append(json.dumps({"trigger": r["trigger"]}, indent=2))
        L.append("```")
        L.append("")
    open(os.path.join(STAGE1, meta["id"], "test_samples.md"), "w").write("\n".join(L) + "\n")


def write_results(meta, rows):
    L = ["# Live run results — recipe `%s`" % meta["id"], "",
         "Mode: **%s** | object(s): %s | SF op(s): %s"
         % ("READ-only" if meta["readonly"] else "WRITE", ", ".join(meta["objects"]),
            ", ".join(meta["ops"])),
         "", "Each sample was **realized against the live `my-dev-org`** (real "
         "filter values fetched / target records seeded), run, then torn down "
         "(all writes undone, org restored).", "",
         "| sample | status | live SF rows read | writes (undone) | formula errs |",
         "|---|---|---|---|---|"]
    for r in rows:
        L.append("| %d | %s | %s | %d | %d |"
                 % (r["sample"], r["status"], r["sf_reads"] or "-",
                    r["mutations"], r["formula_errors"]))
    L.append("")
    L.append("## Realized inputs per sample (real org data)")
    for r in rows:
        L.append("- **Sample %d** (%s):" % (r["sample"], r["status"]))
        for n in r["notes"] or ["(no trigger->SF data dependency)"]:
            L.append("  - %s" % n)
    open(os.path.join(STAGE1, meta["id"], "results.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    run()
