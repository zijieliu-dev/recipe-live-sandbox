"""
live/google_sheets.py - a real-API Google Sheets comp handler.

Maps Workato Google Sheets operations to live Sheets v4 calls via SheetsClient.
Recipes carry foreign spreadsheet ids, so (like the Slack channel redirect) every
append is sent to the configured `SHEETS_SPREADSHEET_ID` / `SHEETS_TAB`.

`add_row_v4_bulk` takes `rows` (a list of record dicts); we flatten them to a
values matrix, write a header row when the tab is empty, and append.
"""
import json


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def _rows(inp):
    rows = inp.get("rows") or inp.get("records") or inp.get("row") or []
    if isinstance(rows, dict):
        rows = [rows]
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def make_handler(client):
    def handle(provider, operation, inp, ctx):
        if not isinstance(inp, dict):
            inp = {}

        if operation in ("add_row_v4_bulk", "add_rows_v4", "add_row_v4", "add_row"):
            rows = _rows(inp)
            if not rows:
                ctx.log_side_effect(provider, operation, appended=0, note="no rows (empty trigger)")
                return {"appended": 0}
            # stable column order: keys in first-seen order across the rows
            cols = []
            for r in rows:
                for k in r:
                    if k not in cols:
                        cols.append(k)
            values = []
            if not client.get_values():          # empty tab -> write a header first
                values.append(cols)
            for r in rows:
                values.append([_cell(r.get(c)) for c in cols])
            res = client.append(values)
            updates = res.get("updates", {}) if isinstance(res, dict) else {}
            ctx.log_side_effect(provider, operation, spreadsheet=client.spreadsheet_id,
                                tab=client.tab, appended=len(rows), columns=cols)
            return {"appended": len(rows), "updatedRange": updates.get("updatedRange"),
                    "success": True}

        # other sheet ops (read/update cells/etc.) -> empty (won't break the run)
        return {}

    return handle
