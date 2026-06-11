#!/usr/bin/env python3
"""Summarize groundtruth/index.jsonl: success, live-touching, truly-succeeded,
per-app coverage. Writes truly_succeeded_ids.txt and partial_live_ids.txt."""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GT = os.path.join(HERE, "groundtruth", "index.jsonl")
PROV_APP = {"salesforce": "Salesforce", "slack": "Slack", "slack_bot": "Slack",
            "jira": "Jira", "jira_service_desk": "Jira",
            "google_sheets": "Google Sheets", "google_drive": "Google Sheets"}

status = Counter()
success = uses_live = touch_live = truly = partial = 0
touch = Counter(); wrote = Counter()
truly_ids, partial_ids = [], []

for line in open(GT):
    line = line.strip()
    if not line:
        continue
    d = json.loads(line)
    st = d.get("status")
    status[st] += 1
    if st not in ("completed", "stopped"):
        continue
    success += 1
    if d.get("live_used"):
        uses_live += 1
    le = d.get("live_effects") or []
    if not le:
        continue
    touch_live += 1
    apps_t, apps_w = set(), set()
    for e in le:
        a = PROV_APP.get(e.get("provider"), e.get("provider"))
        apps_t.add(a)
        if e.get("wrote"):
            apps_w.add(a)
    for a in apps_t:
        touch[a] += 1
    for a in apps_w:
        wrote[a] += 1
    if all(e.get("wrote") for e in le):
        truly += 1
        truly_ids.append(d["id"])
    else:
        partial += 1
        partial_ids.append(d["id"])

print("status:", dict(status))
print("success (completed/stopped):", success)
print("uses a live provider:", uses_live)
print("live-touching (>=1 live effect):", touch_live)
print("truly succeeded (all effects wrote):", truly)
print("partial (some effect wrote=false):", partial)
print("per-app touched:", dict(touch))
print("per-app wrote:", dict(wrote))

with open(os.path.join(HERE, "truly_succeeded_ids.txt"), "w") as f:
    f.write("\n".join(truly_ids) + ("\n" if truly_ids else ""))
with open(os.path.join(HERE, "partial_live_ids.txt"), "w") as f:
    f.write("\n".join(partial_ids) + ("\n" if partial_ids else ""))
print("wrote truly_succeeded_ids.txt (%d), partial_live_ids.txt (%d)" % (len(truly_ids), len(partial_ids)))
