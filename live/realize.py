"""
realize.py - make stage-1 samples use REAL org data.

seed_record(client, sobject): create a valid record of any object by reading its
describe and filling required createable fields (references -> an existing id or
a seeded one; picklists -> first active value; scalars -> typed values).

realize_trigger(recipe, client, alias): trace each trigger field into the SF
steps that consume it and fill it with real data:
  - input key `id`  (delete/update target) -> seed the target object, use its id
  - input field filter (Field = #{trigger})  -> a real value of that field
  - SOQL `query` referencing the trigger     -> a real value (best effort)
All seeded records go through the (tracked) client so teardown removes them.
"""
import re

from test_sandbox.engine import loader, refs
from test_sandbox.salesforce_live import SalesforceError


def _slug(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower()) or "example"

# business-realistic value pools (varied by sample index)
FIRST = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "David", "Sarah"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Anderson"]
COMPANY = ["Acme Corp", "Globex Inc", "Initech LLC", "Umbrella Group", "Soylent Co",
           "Stark Industries", "Wayne Enterprises", "Hooli", "Pied Piper", "Vandelay Industries"]
TITLES = ["Account Executive", "Sales Manager", "VP of Sales", "Director of Ops", "CEO",
          "CTO", "Business Analyst", "Consultant", "Solutions Engineer", "Coordinator"]
STREETS = ["123 Market St", "456 Oak Ave", "789 Pine Rd", "321 Maple Dr", "654 Cedar Ln",
           "987 Elm Blvd", "159 Spruce Way", "753 Birch Ct", "852 Willow Pl", "426 Ash Ter"]
CITIES = [("San Francisco", "California", "US", "94105"), ("Austin", "Texas", "US", "78701"),
          ("Seattle", "Washington", "US", "98101"), ("New York", "New York", "US", "10001"),
          ("Chicago", "Illinois", "US", "60601"), ("Boston", "Massachusetts", "US", "02108"),
          ("Denver", "Colorado", "US", "80202"), ("Atlanta", "Georgia", "US", "30303"),
          ("Miami", "Florida", "US", "33101"), ("Portland", "Oregon", "US", "97201")]
DATES = ["2026-01-15", "2026-02-10", "2026-03-05", "2026-04-20", "2026-05-12",
         "2026-06-08", "2026-07-22", "2026-08-30", "2026-09-14", "2026-10-03"]


def business_value(name, i):
    j = i % 10
    first, last = FIRST[j], LAST[j]
    city, state, country, zipc = CITIES[j]
    if "first" in name and "name" in name:
        return first
    if "last" in name and "name" in name:
        return last
    if "email" in name:
        return ("%s.%s@%s.com" % (first, last, _slug(COMPANY[j]))).lower()
    if "phone" in name or "fax" in name:
        return "+1 (415) 555-%04d" % (1000 + j)
    if "title" in name:
        return TITLES[j]
    if "street" in name or name == "address":
        return STREETS[j]
    if "city" in name:
        return city
    if "state" in name or "province" in name:
        return state
    if "country" in name:
        return country
    if "postal" in name or "zip" in name:
        return zipc
    if "company" in name or "name" in name:
        return COMPANY[j]
    if any(k in name for k in ("description", "comment", "note", "terms", "summary")):
        return "Sandbox test record %d — generated for automated recipe testing." % (j + 1)
    if "subject" in name:
        return "Follow-up meeting %d" % (j + 1)
    if "url" in name or "website" in name or "link" in name:
        return "https://www.%s.com" % _slug(COMPANY[j])
    return "Sample %d" % (j + 1)


def _ref_id(client, ref, i):
    """A valid existing id of `ref`. For User, restrict to active Standard users
    (others, e.g. integration/automated users, can't own records -> 403)."""
    queries = []
    if ref == "User":
        queries.append("SELECT Id FROM User WHERE IsActive = true AND UserType = 'Standard'")
    queries.append("SELECT Id FROM %s" % ref)
    for q in queries:
        try:
            recs = client.query_all(q + " LIMIT 10")
            if recs:
                return recs[i % len(recs)]["Id"]
        except Exception:
            pass
    return None


def field_value(client, f, depth=0, i=0):
    t = f.get("type")
    name = (f.get("name") or "").lower()
    if t == "reference":
        for ref in f.get("referenceTo", []) or ["Account"]:
            rid = _ref_id(client, ref, i)
            if rid:
                return rid
        if depth < 1:
            rid, _ = seed_record(client, (f.get("referenceTo") or ["Account"])[0], depth + 1, i=i)
            return rid
        return None
    if t == "picklist":
        vals = [p["value"] for p in f.get("picklistValues", []) if p.get("active")]
        return vals[i % len(vals)] if vals else "x"
    if t in ("double", "currency", "percent"):
        return round(1000.0 * (i + 1), 2)
    if t == "int":
        return i + 1
    if t == "boolean":
        return bool(i % 2)
    if t == "date":
        return DATES[i % len(DATES)]
    if t == "datetime":
        return DATES[i % len(DATES)] + "T10:00:00Z"
    if t == "url":
        return "https://example.com/%d" % i
    return business_value(name, i)


def _missing_fields(err):
    out = []
    body = err.body if isinstance(err.body, list) else [err.body]
    for e in body:
        if isinstance(e, dict) and e.get("errorCode") == "REQUIRED_FIELD_MISSING":
            out += e.get("fields", [])
    return out


def seed_record(client, sobject, depth=0, overrides=None, i=0):
    """Create a valid record of `sobject`; return (id, payload).

    Fills metadata-required fields with business-realistic values (varied by i),
    then retries on REQUIRED_FIELD_MISSING to cover Salesforce's conditionally-
    required fields (which describe marks nillable, e.g. Event.DurationInMinutes)."""
    d = client.describe(sobject)
    fmap = {f["name"]: f for f in d.get("fields", [])}
    payload = {}
    for f in d.get("fields", []):
        if not f.get("createable"):
            continue
        if (not f.get("nillable")) and (not f.get("defaultedOnCreate")):
            payload[f["name"]] = field_value(client, f, depth, i)
    if overrides:
        payload.update(overrides)

    for _ in range(6):
        try:
            res = client.create(sobject, payload)
            return (res.get("id") if isinstance(res, dict) else None), payload
        except SalesforceError as e:
            miss = _missing_fields(e)
            if not miss:
                raise
            for name in miss:
                payload[name] = field_value(client, fmap.get(name, {"type": "string"}), depth, i)
    raise SalesforceError(400, "could not satisfy required fields for %s" % sobject)


def seed_init_table(client, sobject, n=5, base=0):
    """Seed an INITIAL TABLE of `n` business-realistic rows of `sobject`.
    Returns their ids. These rows are the starting state a write recipe acts on
    (e.g. delete one row of this table). All are tracked, so teardown restores
    the full table."""
    ids = []
    for k in range(n):
        rid, _ = seed_record(client, sobject, i=base * n + k)
        if rid:
            ids.append(rid)
    return ids


def realize_sf_trigger(client, recipe, i=0):
    """For a Salesforce-TRIGGERED recipe: return a REAL record of the watched
    object as the trigger event (variant i; generating one if the object is empty).

    Salesforce normally fires these (new/changed record). Locally we read real
    records of `sobject_name` and pick the i-th (for variety across samples).
    For OpportunityFieldHistory (which can't be inserted), we generate a row by
    bumping a tracked Opportunity field.
    """
    t = loader.get_trigger(recipe)
    sob = (t.get("input") or {}).get("sobject_name")
    if not sob:
        return {}

    def fetch():
        for q in ("SELECT FIELDS(STANDARD) FROM %s ORDER BY CreatedDate DESC LIMIT 20" % sob,
                  "SELECT FIELDS(STANDARD) FROM %s LIMIT 20" % sob,
                  "SELECT Id FROM %s LIMIT 20" % sob):
            try:
                rows = client.query_all(q)
                if rows:
                    return rows
            except Exception:
                pass
        return []

    rows = fetch()
    if not rows and sob == "OpportunityFieldHistory":
        opp = client.query("SELECT Id, Amount FROM Opportunity LIMIT 1")["records"][0]
        client.update("Opportunity", opp["Id"], {"Amount": (opp.get("Amount") or 0) + 5000 + i})
        rows = fetch()
    if not rows:
        return {}
    rec = rows[i % len(rows)]
    return {k: v for k, v in rec.items() if k != "attributes"}


def _trigger_uses(recipe, alias):
    """For each SF step, how does it consume trigger fields?
    Returns list of dicts: {role, sobject, path, key}."""
    uses = []
    for s in loader.iter_steps(recipe):
        if s.get("provider") != "salesforce":
            continue
        inp = s.get("input") or {}
        sob = inp.get("sobject_name")
        for key, val in inp.items():
            if not isinstance(val, str):
                continue
            for r in refs.find_refs(val):
                if r["line"] != alias:
                    continue
                path = [p for p in r["path"] if isinstance(p, str)]
                if not path:
                    continue
                if key == "id":
                    uses.append({"role": "id", "sobject": sob, "path": path})
                elif key == "query":
                    uses.append({"role": "soql", "sobject": sob, "path": path})
                elif key not in ("sobject_name", "field_list", "limit", "table_list",
                                 "output_schema", "query_field", "since_offset"):
                    uses.append({"role": "field", "sobject": sob, "path": path, "key": key})
    return uses


def _set(d, path, value):
    cur = d
    for k in path[:-1]:
        cur = cur.setdefault(k, {})
    cur[path[-1]] = value


def _nth(client, soql, i):
    try:
        recs = client.query_all(soql)
        return recs[i % len(recs)] if recs else None
    except Exception:
        return None


_DESCRIBE_CACHE = {}


def _field_meta(client, sobject, name):
    if sobject not in _DESCRIBE_CACHE:
        try:
            d = client.describe(sobject)
            _DESCRIBE_CACHE[sobject] = {f["name"]: f for f in d.get("fields", [])}
        except Exception:
            _DESCRIBE_CACHE[sobject] = {}
    return _DESCRIBE_CACHE[sobject].get(name)


def realize_trigger(recipe, client, alias, i=0, target_pool=None):
    """
    Build a trigger event populated with real org data (variant i).

    Returns (trigger, notes). For a write target id, pick one row from the
    provided init table (`target_pool[sobject]`); otherwise seed one. Fetches
    real values for query filters.
    """
    target_pool = target_pool or {}
    trig, notes = {}, []
    for u in _trigger_uses(recipe, alias):
        sob, path = u["sobject"], u["path"]
        dotted = ".".join(path)
        if u["role"] == "id" and sob:
            pool = target_pool.get(sob)
            if pool:
                rid = pool[i % len(pool)]
                notes.append("target row from init table: %s.%s = %s (1 of %d rows)"
                             % (sob, dotted, rid, len(pool)))
            else:
                rid, _ = seed_record(client, sob, i=i)
                notes.append("seeded %s -> trigger.%s = %s" % (sob, dotted, rid))
            _set(trig, path, rid)
        elif u["role"] == "field" and sob and u.get("key"):
            rec = _nth(client, "SELECT %s FROM %s WHERE %s != null LIMIT 20"
                       % (u["key"], sob, u["key"]), i)
            val = rec.get(u["key"]) if rec else None
            src = "real"
            if val is None:                       # empty table -> business-realistic fallback
                fmeta = _field_meta(client, sob, u["key"])
                val = field_value(client, fmeta, i=i) if fmeta else business_value(u["key"].lower(), i)
                src = "business"
            _set(trig, path, val)
            notes.append("%s %s.%s -> trigger.%s = %r" % (src, sob, u["key"], dotted, val))
        elif u["role"] == "soql" and sob:
            rec = _nth(client, "SELECT Name FROM %s WHERE Name != null LIMIT 20" % sob, i)
            val = (rec.get("Name") if rec else "") or ""
            val = val[:3] or "SBX"          # substring -> matches LIKE '%val%'
            _set(trig, path, val)
            notes.append("real %s.Name[:3] -> trigger.%s = %r" % (sob, dotted, val))
    return trig, notes
