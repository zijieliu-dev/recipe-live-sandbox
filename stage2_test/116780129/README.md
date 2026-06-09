# Recipe `116780129` — find a Jira user, then create an assigned Task (LIVE Jira)

**Connector:** Jira (live) &nbsp;|&nbsp; **Trigger:** `workato_api_platform::receive_request` &nbsp;|&nbsp; **Ops:** `jira::find_user`, `jira::create_issue`

## What it does
An inbound API request carries an assignee email + issue fields. The recipe **looks up the Jira
user by email** (`find_user`), then **creates an AAI Task assigned to that user** (`create_issue`
with `assignee_id` = the found user's `accountId`).

## Input supplied
```json
{ "trigger": { "request": {
  "assignee_email": "jesseliu@cs.unc.edu",
  "summary": "Stage2: find-user then assigned Task",
  "description": "Created and assigned to the user found via live Jira find_user."
}}}
```

## Run command
```bash
cd ~/Desktop
python3 test_sandbox/run.py 116780129 --live --input /tmp/s2_jfind.json
```

## Live result ✅
- `status: completed`; side-effect `jira::create_issue` → `key: AAI-3`
- `find_user("jesseliu@cs.unc.edu")` matched the real Jira user **Jesse Liu** → used their `accountId`.
- Created **[AAI-3](https://test-sandbox-dev.atlassian.net/browse/AAI-3)** — Task, **assignee = Jesse Liu**.

**Proves:** a real **two-step Jira flow** — live user lookup feeding a live create — with the
created issue actually assigned to the resolved user.
