# Recipe `124414716` — look up a Slack user by email, then mention them in a post (LIVE Slack)

**Connector:** Slack (live) &nbsp;|&nbsp; **Trigger:** `workato_genie::start_workflow` &nbsp;|&nbsp; **Ops:** `slack_bot::get_user_by_email`, `slack_bot::post_bot_message`

## What it does
A Genie workflow supplies a user email + a query. The recipe **resolves the Slack user by email**
(`get_user_by_email`), then **posts a message** that `@`-mentions that user with their unanswered query.

## Input supplied
```json
{ "trigger": {
  "context": { "user_email": "jesseliu@cs.unc.edu" },
  "parameters": { "channel_id": "C0B95EM1PC1", "user_query": "How do I reset my SSO?" }
}}
```

## Run command
```bash
cd ~/Desktop
python3 test_sandbox/run.py 124414716 --live --input /tmp/s2_slook.json
```

## Live result ✅
- `status: completed`; `slack_bot::post_bot_message` → `ok: true`, `ts: 1781047423.095119`
- `get_user_by_email("jesseliu@cs.unc.edu")` resolved to the real Slack id **`U0B91BSRGF8`**
  (needs the `users:read.email` scope — which is set).
- Posted to **`#sandbox`**: *"`<@U0B91BSRGF8>` have an unanswered query: How do I reset my SSO?"*

**Proves:** the live Slack connector chains a **real user lookup → real post**, with the `@`-mention
resolving to an actual workspace member (not a placeholder).

> Note: `get_user_by_email` only resolves emails that belong to **real members** of
> `sandbox-slack-dev`. `jesseliu@cs.unc.edu` is the one member; other emails return `users_not_found`.
