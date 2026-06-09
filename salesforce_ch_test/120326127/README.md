# Recipe `120326127` — Chatter post when a lost-deal Success Owner needs unassigning

**Mode:** WRITE (posts to Salesforce Chatter) &nbsp;|&nbsp; 
**Trigger:** `salesforce::updated_custom_object` (watches **Opportunity**) &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** lookup_table

---

## What this recipe does (plain steps)

1. **Trigger** — fires when an **Opportunity** is updated.
2. **Branch** — "Success Owner may have been unassigned already."
3. **`search_sobjects_soql` on `User`** — live SF read (finds the relevant user).
4. **`__adhoc_http_action` → `POST /services/data/v61.0/chatter/feed-elements`** — live SF write.
   Posts a **Chatter FeedItem onto the Opportunity's Account feed** with the text:
   > "Unfortunately, we lost the deal for this Account after the Success Owner assignment was triggered. Please unassign."
   …and **@mentions** the user's `ManagerId` and the Account's `Expansion_CSM__c`.
5. **`lookup_table` search + delete** — removes a tracking entry so the message isn't re-sent. **Mocked** (no real Workato lookup tables locally).

### Live vs mocked
- **LIVE:** the Opportunity trigger record, the `User` query, the Chatter POST.
- **MOCKED:** the two `lookup_table` steps.

---

## Prerequisites
- Salesforce connected: `sf org display --target-org my-dev-org` → *Connected*.
- Run from `~/Desktop`.

## Steps to run

1. Fire it live with the full trace:
   ```bash
   cd ~/Desktop
   python3 test_sandbox/run.py 120326127 --live --trace
   ```
2. In the JSON output, note:
   - **`status`** — expect `completed`.
   - **`trigger_fired`** — the real Opportunity used. Note its **`AccountId`** (the Chatter post lands on that Account).
   - **`side_effects`** — find:
     - the `salesforce::search_sobjects_soql` entry (the live User read), and
     - the `salesforce::__adhoc_http_action` entry (the Chatter POST). Its result is either the new feed-element JSON **or** `{"__http_error__": …}`.

## Where to see the effect

- **Salesforce → the Account** behind the fired Opportunity (use the `AccountId` from `trigger_fired`) → **Chatter feed**. You should see a new post beginning *"Unfortunately, we lost the deal…"*.
- ⚠️ If the @mentioned users don't resolve in your org (e.g. `Expansion_CSM__c` is empty or the manager id is blank), the Chatter API may reject the post. The adhoc handler **records the error** (`__http_error__`) instead of crashing, so the run still shows `completed` — just with no visible post. That's an expected outcome to note, not a failure of the sandbox.

---

## Results (fill in after you run it)

- **Date run:**
- **status:**
- **trigger_fired** — Opportunity Id / AccountId:
- **User query** — rows returned:
- **Chatter post:**
  - ☐ appeared in Salesforce (paste link / screenshot of the Account feed)
  - ☐ `__http_error__` returned (paste the error)
- **lookup_table:** mocked (no real effect) — confirm both steps recorded as side-effects: ☐
- **formula_errors:** (count from output)
- **Notes / surprises:**
