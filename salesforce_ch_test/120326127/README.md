# Recipe `120326127` — Chatter post when a lost-deal Success Owner needs unassigning

**Mode:** WRITE (Chatter post) &nbsp;|&nbsp; **Trigger:** `salesforce::updated_custom_object` (watches **Opportunity**) &nbsp;|&nbsp; **Live:** Salesforce &nbsp;|&nbsp; **Mocked:** lookup_table

> ## ⚠️ Verdict: runs `completed`, but **no observable effect in this org**
> This recipe's only write is a **Chatter post**, and it can't be seen here for two reasons:
> 1. The post is **gated** behind `if present(Account.Expansion_CSM__c)`, and that custom
>    field **doesn't exist** in this org → the condition is false → the whole post branch is
>    **skipped**. A plain run only does the (mocked) `lookup_table` steps.
> 2. Even if forced, the post **@mentions the user's manager**, and this single-user org has
>    **no manager** → the Chatter API rejects the post (`__http_error__`).
>
> So there's no table row and no visible Chatter message to verify. Kept here for the record;
> for a recipe that **does** show a real table change, see [`../123607383`](../123607383/README.md).

---

## What this recipe does
1. **Trigger** — fires when an **Opportunity** is updated.
2. **Branch** — `if Account.Expansion_CSM__c is present` (← false in this org; field absent).
3. **`search_sobjects_soql` on `User`** — `WHERE Id = <Account.Expansion_CSM__c>` (live read).
4. **`__adhoc_http_action` → `POST /chatter/feed-elements`** — posts a Chatter FeedItem to the
   Opportunity's Account feed, @mentioning the user's `ManagerId` and `Expansion_CSM__c`.
5. **`lookup_table` search + delete** — clears a tracking entry. **Mocked.**

Steps 3–4 are inside the branch from step 2, so in this org they never run.

## Live vs mocked
- **LIVE (if the branch ran):** the `User` read and the Chatter POST.
- **MOCKED:** the two `lookup_table` steps.

---

## How to run it (to confirm the verdict)
```bash
cd ~/Desktop
python3 test_sandbox/run.py 120326127 --live --trace
```
Expect:
- `status: completed`
- `side_effects` shows **only** `lookup_table::delete_entry` (mocked) — the Chatter branch was skipped.

### (Optional) force the post branch — to see it get rejected
Supply a trigger where `Expansion_CSM__c` is set to a real User id; the branch then runs and
the Chatter POST is attempted, but fails on the empty manager mention:
```bash
cat > /tmp/opp_force.json <<'EOF'
{ "trigger": { "Id": "006g5000003ukwDAAQ", "AccountId": "001g500000MKbA2AAL",
               "Account": { "Expansion_CSM__c": "005g5000006ezEDAAY" } } }
EOF
python3 test_sandbox/run.py 120326127 --live --input /tmp/opp_force.json --trace
```
The `__adhoc_http_action` side-effect will carry an `__http_error__` (invalid/empty mention).

---

## Results (fill in after you run it)

- **Date run:**
- **status:** (expect `completed`)
- **side_effects seen:** (expect only `lookup_table::delete_entry`)
- **Chatter post:** ☐ none (branch skipped) ☐ forced → `__http_error__` (paste)
- **Conclusion:** no observable effect in this org — ☐ confirmed
- **Notes:**
