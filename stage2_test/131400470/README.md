# Recipe `131400470` — append rows to Google Sheets (LIVE Google Sheets)

**Connector:** Google Sheets (live) &nbsp;|&nbsp; **Trigger:** `salesforce::sobject_batch_created_or_updated` &nbsp;|&nbsp; **Op:** `google_sheets::add_row_v4_bulk`

> The **4th live connector**. A batch of records → real rows appended to a real Google Sheet.

## What it does
A batch trigger delivers records (`skilljar__Course_Progress__c`); the recipe maps each record's
fields to columns and **appends them to a Google Sheet** via `add_row_v4_bulk`.

## Live setup (auth via gcloud, no key files)
- `gcloud auth login --enable-gdrive-access` (Drive scope covers the Sheets API — the plain
  `spreadsheets` scope is blocked on the ADC client) → tokens minted by `gcloud auth print-access-token`.
- `gcloud services enable sheets.googleapis.com`
- `SHEETS_SPREADSHEET_ID` / `SHEETS_TAB` in `.env` → all appends redirect here (recipes carry
  foreign sheet ids, like the Slack channel redirect).

## Input supplied
The recipe's columns map to nested record fields (`Account__r.Name`, `skilljar__Course__r.skilljar__Title__c`,
`skilljar__Student__r.skilljar__Email__c`, …), so the batch is shaped to match:
```json
{ "trigger": { "skilljar__Course_Progress__c": [
  {"Name":"CP-001","skilljar__Completed_At__c":"2026-06-01","skilljar__Success_Status__c":"Completed",
   "Account__r":{"Name":"Acme Corp"},
   "skilljar__Course__r":{"skilljar__Title__c":"Intro to Workato"},
   "skilljar__Student__r":{"Name":"Jane Doe","skilljar__Email__c":"jane@acme.com"}},
  { … CP-002 … }
]}}
```

## Run command
```bash
cd ~/Desktop
python3 test_sandbox/run.py 131400470 --live --input /tmp/s2_sheet.json
```

## Live result ✅
- `status: completed`; `google_sheets::add_row_v4_bulk` → appended **2 rows**.
- Read back from the live spreadsheet (`1za81dIH79JpmD15kAxpM-EtiMdWBmUsU_HIX_EshNh0`):

| Account Name | Completion Date | Course Title | Email | Header Name | Student Name | Success Status |
|---|---|---|---|---|---|---|
| Acme Corp | 2026-06-01 | Intro to Workato | jane@acme.com | CP-001 | Jane Doe | Completed |
| Globex Inc | 2026-06-05 | Advanced Recipes | john@globex.com | CP-002 | John Smith | In Progress |

**Proves:** the live Google Sheets connector takes a recipe's `____source` list-map of records →
real rows in a real spreadsheet (header written when the tab is empty). Built on the same pattern
as Jira/Slack; auth via the gcloud CLI.
