"""
tracker.py - per-sample isolation via tracked teardown (point 6).

TrackedClient wraps SalesforceClient. Reads pass through; every WRITE is logged
with enough info to undo it:
  create -> remember new id           -> teardown deletes it
  update -> snapshot changed fields   -> teardown restores them
  delete -> snapshot (if pre-existing)-> teardown recreates best-effort
            (seeded deletes need no restore)

Run order per sample: seed (creates, tracked) -> run recipe (tracked) ->
teardown() reverses every change in LIFO order, returning the org to its prior
state so the next sample starts clean.
"""


class TrackedClient:
    def __init__(self, client):
        self._c = client
        self.changes = []          # ordered list of (kind, ...)
        self.created = set()        # ids we created (seed or run)
        self._createable = {}       # sobject -> set of createable field names

    def __getattr__(self, name):
        # delegate any non-tracked attribute/method (e.g. _req, _data) to the
        # underlying client, so handlers that use raw requests still work.
        if name == "_c":
            raise AttributeError(name)
        return getattr(self._c, name)

    def _createable_fields(self, sobject):
        if sobject not in self._createable:
            try:
                d = self._c.describe(sobject)
                self._createable[sobject] = {f["name"] for f in d.get("fields", []) if f.get("createable")}
            except Exception:
                self._createable[sobject] = set()
        return self._createable[sobject]

    # -- reads (passthrough) ----------------------------------------------
    def query(self, q):
        return self._c.query(q)

    def query_all(self, q):
        return self._c.query_all(q)

    def describe(self, o):
        return self._c.describe(o)

    def describe_global(self):
        return self._c.describe_global()

    def get(self, o, i, fields=None):
        return self._c.get(o, i, fields)

    # -- writes (tracked) -------------------------------------------------
    def create(self, sobject, data):
        res = self._c.create(sobject, data)
        rid = res.get("id") if isinstance(res, dict) else None
        if rid:
            self.changes.append(("create", sobject, rid))
            self.created.add(rid)
        return res

    def update(self, sobject, rid, data):
        snap = {}
        try:
            cur = self._c.get(sobject, rid, fields=list(data.keys()))
            snap = {k: cur.get(k) for k in data.keys()}
        except Exception:
            snap = {}
        self.changes.append(("update", sobject, rid, snap))
        return self._c.update(sobject, rid, data)

    def upsert(self, sobject, ext_field, ext_value, data):
        res = self._c.upsert(sobject, ext_field, ext_value, data)
        rid = res.get("id") if isinstance(res, dict) else None
        if rid and isinstance(res, dict) and res.get("created"):
            self.changes.append(("create", sobject, rid))
            self.created.add(rid)
        return res

    def delete(self, sobject, rid):
        snap = None
        if rid not in self.created:
            try:
                snap = self._c.get(sobject, rid)
            except Exception:
                snap = None
        self.changes.append(("delete", sobject, rid, snap))
        return self._c.delete(sobject, rid)

    # -- teardown ---------------------------------------------------------
    def teardown(self):
        results = []
        for ch in reversed(self.changes):
            kind = ch[0]
            try:
                if kind == "create":
                    self._c.delete(ch[1], ch[2])
                    results.append(("undo-create", ch[2], "deleted"))
                elif kind == "update":
                    _, o, i, snap = ch
                    restore = {k: v for k, v in (snap or {}).items() if k != "attributes"}
                    if restore:
                        self._c.update(o, i, restore)
                    results.append(("undo-update", i, "restored"))
                elif kind == "delete":
                    _, o, i, snap = ch
                    if i in self.created or not snap:
                        results.append(("undo-delete", i, "skip (seeded)"))
                    else:
                        # recreate the deleted init row from its snapshot
                        # (createable, non-null fields only) -> new id, same data
                        cap = self._createable_fields(o)
                        clean = {k: v for k, v in snap.items()
                                 if k in cap and v not in (None, "") and not isinstance(v, (dict, list))}
                        new = self._c.create(o, clean)
                        results.append(("undo-delete", i, "recreated -> %s" % (new.get("id") if isinstance(new, dict) else "?")))
            except Exception as e:
                results.append((kind, str(ch[1:3]), "ERR %s" % str(e)[:80]))
        self.changes.clear()
        return results
