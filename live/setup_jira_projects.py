#!/usr/bin/env python3
"""
setup_jira_projects.py - create the Jira projects the recipes reference.

Parallel to setup_init_db.py (which seeds the Salesforce init tables): this
provisions the live Jira side so recipes run UNCHANGED. It touches Jira only -
no recipe or engine file is modified.

The recipes hard-code project_issuetype values like "RME--Task", "PSM--Enhancement"
(harvested from other workspaces). This script recreates those project KEYS in
your Jira as company-managed (classic) projects, whose default template already
provides the standard issue types: Task, Sub-task, Story, Bug, Epic.

  python3 test_sandbox/live/setup_jira_projects.py            # create the 21 projects + issue types
  python3 test_sandbox/live/setup_jira_projects.py --reset    # delete the projects we created

Idempotent: existing project keys are skipped. --reset never deletes ST (your
manually-created template project) or any key not in this script's list.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.jira_live import JiraClient, JiraError      # noqa: E402

# company-managed (classic) software template -> Task, Sub-task, Story, Bug, Epic
TEMPLATE = "com.pyxis.greenhopper.jira:gh-kanban-template"
PROJECT_TYPE = "software"

# project key -> extra (non-standard) issue type names the recipes use for it.
# Standard types (Task/Bug/Story/Sub-task/Epic) come free with the template.
PROJECTS = {
    "AAI": [], "BSYS": [], "CT": [], "DM": [], "GL": [], "MOPS": [],
    "PLG": [], "RIS": [], "RME": [], "SGO": [], "TS": [], "WEB": [], "WG": [],
    "AIMATRIX": ["Enhancement"],
    "PSM": ["Enhancement", "[PE] Change"],
    "PSP": ["Security Bug"],
    "BTSUP": ["[BT] Security Concerns"],
    "BBA": ["Ask a question"],
    "BBSF": ["Ask a question"],
    "PETFOSUP": ["New Application Request"],
    "PARPFSTFO": ["Cloud Service Request", "New Application Request"],
}
PROTECTED = {"ST"}        # never delete the manual template project


def existing_keys(jc):
    keys = set()
    start = 0
    while True:
        page = jc._req("GET", "/rest/api/3/project/search",
                       params={"startAt": start, "maxResults": 50})
        for p in page.get("values", []):
            keys.add(p.get("key"))
        if page.get("isLast", True):
            break
        start += page.get("maxResults", 50)
    return keys


def create_project(jc, key, lead):
    body = {"key": key, "name": key, "projectTypeKey": PROJECT_TYPE,
            "projectTemplateKey": TEMPLATE, "leadAccountId": lead,
            "assigneeType": "PROJECT_LEAD"}
    return jc._req("POST", "/rest/api/3/project", body=body)


# -- custom issue types (only with --custom-types) -------------------------
def _all_issue_types(jc):
    return {it["name"].lower(): it["id"] for it in jc._req("GET", "/rest/api/3/issuetype")}


def ensure_issue_type(jc, name, cache):
    if name.lower() in cache:
        return cache[name.lower()]
    it = jc._req("POST", "/rest/api/3/issuetype", body={"name": name, "type": "standard"})
    cache[name.lower()] = it["id"]
    return it["id"]


def add_types_to_project(jc, key, type_ids):
    pid = jc._req("GET", "/rest/api/3/project/%s" % key)["id"]
    page = jc._req("GET", "/rest/api/3/issuetypescheme/project",
                   params={"projectId": pid})
    scheme_id = page["values"][0]["issueTypeScheme"]["id"]
    jc._req("PUT", "/rest/api/3/issuetypescheme/%s/issuetype" % scheme_id,
            body={"issueTypeIds": [str(t) for t in type_ids]})


def main():
    ap = argparse.ArgumentParser(description="Provision (or delete) the recipe Jira projects.")
    ap.add_argument("--reset", action="store_true",
                    help="delete the projects this script created (never ST)")
    args = ap.parse_args()

    jc = JiraClient.from_env()
    if jc is None:
        raise SystemExit("no Jira creds in .env")
    me = jc._req("GET", "/rest/api/3/myself")["accountId"]
    have = existing_keys(jc)

    if args.reset:
        for key in PROJECTS:
            if key in PROTECTED or key not in have:
                continue
            try:
                jc._req("DELETE", "/rest/api/3/project/%s" % key)
                print("deleted %s" % key)
            except JiraError as e:
                print("delete %s failed: %s %s" % (key, e.status, str(e.body)[:120]))
        return

    # create each project, then create + attach its non-standard issue types
    type_cache = _all_issue_types(jc)
    for key, extras in PROJECTS.items():
        if key in have:
            print("%-10s exists, skip" % key)
        else:
            try:
                create_project(jc, key, me)
                print("%-10s created" % key)
            except JiraError as e:
                print("%-10s CREATE FAILED: %s %s" % (key, e.status, str(e.body)[:160]))
                continue
        if extras:
            try:
                ids = [ensure_issue_type(jc, n, type_cache) for n in extras]
                add_types_to_project(jc, key, ids)
                print("%-10s   + issue types %s" % ("", extras))
            except JiraError as e:
                print("%-10s   custom-type setup failed: %s %s" % ("", e.status, str(e.body)[:160]))


if __name__ == "__main__":
    main()
