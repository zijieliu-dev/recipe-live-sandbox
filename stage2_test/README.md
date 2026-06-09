# Stage 2 — Live Jira & Slack Test Set

Stage 1 proved the sandbox against **live Salesforce**. Stage 2 demonstrates the **two new
live connectors — Jira and Slack** — running real Workato recipes end-to-end. Jira/Slack
calls hit the **real APIs**; Salesforce and everything else behave as in Stage 1.

- **Jira** → `test-sandbox-dev.atlassian.net` (real issues created, real comments added)
- **Slack** → workspace `sandbox-slack-dev`, channel **`#sandbox`** (real messages posted)

Run pattern: `cd ~/Desktop && python3 test_sandbox/run.py <id> --live --input <bundle>`
(Jira/Slack go live automatically because their creds are in `test_sandbox/.env`.)

---

## Results (live runs)

| recipe | connector | what it did | live result |
|--------|-----------|-------------|-------------|
| [127910849](127910849/) | **Jira** | create a Task from a workflow request | **[GL-22](https://test-sandbox-dev.atlassian.net/browse/GL-22)** (Task, High) |
| [129427781](129427781/) | **Jira** | create a Bug + add a comment | **[DM-4](https://test-sandbox-dev.atlassian.net/browse/DM-4)** (Bug) + 1 comment |
| [116780129](116780129/) | **Jira** | find a user by email, then create a Task **assigned** to them | **[AAI-3](https://test-sandbox-dev.atlassian.net/browse/AAI-3)** (assignee: Jesse Liu) |
| [131739423](131739423/) | **Jira** | **read** an issue and return its fields | read **GL-22** live |
| [123804080](123804080/) | **Slack** | post a "response correction" card | `#sandbox` (red "Incorrect Response" attachment) |
| [131610736](131610736/) | **Slack** | post a Block Kit welcome card | `#sandbox` ("Welcome to #ask-security!") |
| [124414716](124414716/) | **Slack** | look up a user by email, then `@`-mention them in a post | `#sandbox` (mentions real id `U0B91BSRGF8`) |

All seven `completed` with the call hitting the **real** Jira/Slack API (not the mock) — covering
Jira **create / comment / find_user / get_issue** and Slack **post / get_user_by_email**.

## How the live routing works (recap)
`live/salesforce.py:make_dispatch` routes by provider: `jira`/`jira_service_desk` → live Jira
REST; `slack`/`slack_bot` → live Slack Web API; everything else → mocked. Two Slack details
worth noting in the writeups: recipe messages are **redirected** to `#sandbox` (recipes carry
foreign channel ids — see `SLACK_CHANNEL_OVERRIDE`), and Workato's block/attachment formats are
**translated** to Slack Block Kit by `live/slack.py`.

## What's in each folder
`<id>/README.md` — what the recipe does, how it's triggered, the exact input supplied, the run
command, and the **verified live result** (issue key/link or Slack timestamp).
