"""Google Sheets canonicalizer: spreadsheet/sheet target + the row value
matrix (order-stable, volatile-free)."""
from . import generic


def _rows(inp):
    rows = inp.get("rows") or inp.get("records") or inp.get("row") or []
    if isinstance(rows, dict):
        rows = [rows]
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def canonicalize(effect):
    inp = effect.get("input") or {}
    if not isinstance(inp, dict):
        inp = {}
    rows = _rows(inp)
    # stable column order: first-seen across rows (matches live/google_sheets.py)
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    values = [[generic.norm_text(r.get(c)) for c in cols] for r in rows]
    return {
        "provider": effect.get("provider"),
        "family": generic.family(effect.get("provider"), effect.get("operation")),
        "spreadsheet": generic.norm_text(inp.get("spreadsheet_id")
                                         or inp.get("spreadsheet")) or None,
        "sheet": generic.norm_text(inp.get("sheet_name") or inp.get("sheet")
                                   or inp.get("worksheet")) or None,
        "columns": cols,
        "values": values,
        "n_rows": len(rows),
    }
