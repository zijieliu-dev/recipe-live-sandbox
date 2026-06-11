# Recipe Sandbox — Live Connectors (Salesforce · Jira · Slack · Google Sheets)

This sandbox runs Workato recipes locally. By default every connector is **mocked**
(the call is recorded as a side-effect and a fabricated output is returned). In
**live mode** (`run.py --live`), four connectors hit the **real** software and
everything else stays mocked:

| Connector | Live? | Auth | Target |
|-----------|-------|------|--------|
| **Salesforce**   | ✅ | `sf` CLI (`my-dev-org`) | your dev org |
| **Jira**         | ✅ | email + API token in `.env` | `test-sandbox-dev.atlassian.net` |
| **Slack**        | ✅ | bot token in `.env` | workspace `sandbox-slack-dev`, channel `#sandbox` |
| **Google Sheets**| ✅ | `gcloud` CLI access token | spreadsheet/tab in `.env` (`SHEETS_SPREADSHEET_ID`) |

A connector goes live **only if its client can be built** (creds present); otherwise
it stays mocked. So nothing breaks if a credential is missing.

---

## 1. How it works (the one idea)

`live/salesforce.py: make_dispatch(sf, jira_client, slack_client, sheets_client)`
returns the function the interpreter calls for every recipe step. It routes by
provider:

```
salesforce                  -> real Salesforce REST
jira / jira_service_desk     -> real Jira REST      (only if jira_client given)
slack / slack_bot            -> real Slack Web API   (only if slack_client given)
google_sheets                -> real Sheets v4 API   (only if sheets_client given)
everything else              -> mocked comps.dispatch
```

### Files and their roles
```
salesforce_live/client.py   real Salesforce REST client (pre-existing)
jira_live/client.py         real Jira Cloud REST client
slack_live/client.py        real Slack Web API client
google_sheets_live/client.py real Google Sheets v4 client (token via gcloud CLI)
live/salesforce.py          make_dispatch (provider routing) + the SF handler
live/jira.py                maps Workato jira ops -> Jira REST  (soft-fail on 4xx)
live/slack.py               maps Workato slack ops -> Slack API + Workato->BlockKit translation
live/google_sheets.py       maps Workato sheet ops -> Sheets append (header + values matrix)
live/setup_jira_projects.py one-off: creates the Jira projects the recipes reference
live/slack_bridge.py        webhook server for live Slack interactions (modals)
run.py                      run ONE recipe (mocked, or --live)
```

---

## 2. Setup (one time)

Credentials live in `test_sandbox/.env` (gitignored; template in `.env.example`).

```
# Jira  — token: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_BASE_URL=https://test-sandbox-dev.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=...

# Slack — bot token; scopes: chat:write, users:read, users:read.email, files:write, commands
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_OVERRIDE=C0B95EM1PC1     # send all recipe posts to #sandbox (see §5)
SLACK_SIGNING_SECRET=...               # only needed for the interaction bridge (§6)

# Google Sheets — no token here; auth via the gcloud CLI (see below).
SHEETS_SPREADSHEET_ID=...              # all recipe appends redirect here (recipes carry foreign ids)
SHEETS_TAB=Sheet1                      # default tab
```
Salesforce uses the `sf` CLI — no secret in `.env`. Check it with
`sf org display --target-org my-dev-org`.

Google Sheets uses the `gcloud` CLI (same pattern as Salesforce — the access
token is minted on demand, nothing stored in `.env`). One-time setup:
```
gcloud auth login --enable-gdrive-access   # Drive scope covers the Sheets API
gcloud services enable sheets.googleapis.com
```
Omit `SHEETS_SPREADSHEET_ID` → Google Sheets stays mocked.

**Jira projects** are already provisioned. To (re)create them on a fresh Jira:
```
python3 test_sandbox/live/setup_jira_projects.py            # create 21 projects + their issue types
python3 test_sandbox/live/setup_jira_projects.py --reset    # delete them (never touches your ST project)
```

---

## 3. Run a recipe live

```
python3 test_sandbox/run.py <recipe-id> --live            # fire SF+Jira+Slack+Sheets live
python3 test_sandbox/run.py <recipe-id> --live --trace    # + full step trace
```
(Jira/Slack/Sheets go live automatically when their `.env`/CLI creds are present;
without creds they stay mocked.)
It prints `live providers: salesforce jira slack google_sheets` to stderr, then JSON with
`status`, `side_effects`, and (with `--trace`) the step trace. Real outcomes
(created issue keys, Slack `ts`, SF ids) appear in `side_effects`.

**Supplying trigger input** (for recipes whose content comes from the trigger,
e.g. a Jira issue summary or an issue key to read):
```
python3 test_sandbox/run.py <id> --live --input bundle.json
# bundle.json: {"trigger": {"parameters": {"summary": "...", "description": "..."}}}
```

---

## 4. Salesforce
Reads and writes go to the real org. Trigger records are realized from real org
data (`live/realize.py`). Nothing more to configure.

## 4b. Google Sheets
Recipes carry foreign spreadsheet ids, so (like the Slack channel redirect) every
append is routed to the configured `SHEETS_SPREADSHEET_ID` / `SHEETS_TAB`.
`live/google_sheets.py` handles the `add_row*_v4*` ops: it flattens the row dicts
to a values matrix, writes a header row when the tab is empty, then appends. Other
sheet ops (read/update cells) return empty so they never break a run. Auth is the
`gcloud` access token (re-minted automatically on a 401).

## 5. Slack messages
- **Channel redirect:** recipes hard-code channel IDs from *other* workspaces
  (e.g. `C031GRNUVLL`) that don't exist here. `SLACK_CHANNEL_OVERRIDE` redirects
  every post/reply/upload to `#sandbox` so you can see them. Remove the env var to
  fire as-is (posts to missing channels return `channel_not_found`, recorded).
- **Block translation:** recipes store messages/modals in Workato's own block DSL
  (`block_type: "section_with_text"`, …), not Slack Block Kit. `live/slack.py`
  translates the common types and always sets a plain-text fallback.

## 6. Slack interactive modals — the bridge
`block_kit_modals` needs a real `trigger_id`, which Slack only issues to a public
webhook during a live interaction. `live/slack_bridge.py` is that webhook.

**Start it (one session):**
```
python3 test_sandbox/live/slack_bridge.py --setup     # prints full instructions
python3 test_sandbox/live/slack_bridge.py --port 3000 # start the server
cloudflared tunnel --url http://localhost:3000        # get a public https URL
```
Then in your Slack app: set the slash-command + Interactivity Request URLs to
`https://<tunnel>/slack/command` and `/slack/interact`, add the `commands` scope,
put the signing secret in `.env`. Run the slash command in `#sandbox` → the recipe
fires with a real `trigger_id` → the modal opens. **(Verified: `/create standup`
→ recipe 102724746 → modal.)**

> Note: the cloudflared quick-tunnel URL changes every restart — reconfigure the
> Slack URLs if you restart it.

---

## 7. What works vs. what's limited

**Fully live & verified:** Salesforce read/write · Jira create/read/comment/transition
· Slack messages to `#sandbox` · Slack modals (via the bridge) · Google Sheets row appends.

Three kinds of expected failures remain (recorded as soft-fails, never crashes):

| Category | Example | Status |
|----------|---------|--------|
| **Needs trigger input** | `create_comment` needs `parameters.comment_body` | supply via `--input`; we don't fabricate content |
| **`get_user_by_email` non-member** | email not in `sandbox-slack-dev` → `users_not_found` | left as-is (the true answer); only `jesseliu@cs.unc.edu` is a member |
| **Interaction-only Slack ops** | `update_blocks_by_block_id` (needs a live message `ts`) | covered for modals via the bridge; the rest need a live interaction |

Soft-fail behavior is deliberate: a 4xx from Jira (missing field/project) or a
Slack `ok:false` is recorded in `side_effects` and the run continues, so one bad
step doesn't hide the rest of the recipe.

---

## 8. Check current progress (step by step)
1. **Salesforce:** `sf org display --target-org my-dev-org` → Connected.
2. **Jira:** open `https://test-sandbox-dev.atlassian.net` → 22 projects (ST + 21).
   Run a create: `python3 run.py 127910849 --live --input bundle.json` → new issue key.
3. **Slack messages:** `python3 run.py 109210865 --live` → message appears in `#sandbox`.
4. **Slack modals:** start the bridge + tunnel (§6), run the slash command → modal opens.

## 9. Open items / next steps
- **Bridge `view_submission`:** when a modal is submitted, the bridge currently
  acks it (modal closes) but does **not** yet route the entered values back into a
  recipe to act on them. Building that is the next step if interactive recipes need
  to complete their action.
- **`get_user_by_email`:** invite the real people the recipes reference, or accept
  `users_not_found`. (Your decision: leave as-is.)
- **Broader testing:** run more recipes per §3; real outcomes show in `side_effects`.

---

## 10. Benchmark — live execution at scale

We recorded **3,383 recipes** fired live across all four connectors (one ground-truth
record each in `stage3_test/groundtruth/`). From those, `stage3_test/build_benchmark.py`
derives two splits under `stage3_test/benchmark/`:

### `main_1k` — the scored benchmark (n = 1,000)
Recipes that executed **≥1 live action** (a real SF / Slack / Jira / Sheets read or
write) with **no failed live effect** — i.e. they cleanly exercised the real software.

| Breakdown | Counts |
|-----------|--------|
| **tier** | `live_write` 489 · `live_read` 511 |
| **primary_app** | Slack 387 · Salesforce 207 · Jira 207 · Google Sheets 199 |

`live_read` recipes genuinely hit the live API but only read (no write side-effect) —
accepted as success per the benchmark definition. Selection takes all clean live-writes
+ all non-Slack clean reads + enough Slack reads to reach 1,000 (Slack is ~46% of the
clean pool, so it's trimmed for connector diversity). Deterministic by id.

### `partials_split` — labelled, NOT scored (n = 321)
Recipes that landed some live effect but had a blocked one. Kept as a platform-limited
/ stress split, **not counted as success**:

| label | count | meaning |
|-------|-------|---------|
| `platform_limited` | 287 | blocked by `block_kit_modals` — needs a real single-use Slack `trigger_id` from a live interaction (no API to mint one). Still exercises live Slack. |
| `mock_blank` | 34 | a Slack/Sheets write whose content came from mocked-upstream steps returning empty, or blank-by-design. Not honestly fixable in batch. |

> The committed repo keeps the aggregate `groundtruth/index.jsonl` and both benchmark
> splits; the 3.3k per-recipe `groundtruth/*.json` dumps are gitignored (regenerate
> locally). See `stage3_test/README.md` for the earlier 200-recipe fire-as-is run and
> its caveats (zero-input floor, the Zscaler/SSL environment issue).
