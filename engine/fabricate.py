"""
fabricate.py - Phase 5 deterministic, schema-shaped fake data.

Builds fake values that match a Workato output schema (a list of field dicts
with type / control_type / properties). Used to populate:
  - the trigger event,
  - external-connector read/write outputs,
so downstream _ref digs resolve to real values and foreach iterates real lists.

Determinism: every value is seeded by a stable hash of a key string
(provider::operation.field[...]). No wall-clock, no RNG -> a recipe fabricates
identical data every run, which is what makes gold vs. candidate comparable.
"""
import datetime
import hashlib

_BASE_DATE = datetime.date(2026, 1, 1)
_ARRAY_LEN = 2
_MAX_DEPTH = 5


def _seed(key):
    return int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)


def _scalar(field, key):
    t = (field.get("type") or "").lower()
    ct = (field.get("control_type") or "").lower()
    nm = (field.get("name") or "").lower()
    s = _seed(key)

    if t in ("integer", "int"):
        return s % 1000
    if t in ("number", "float", "decimal"):
        return round((s % 100000) / 100.0, 2)
    if t in ("boolean", "bool"):
        return s % 2 == 0
    if t in ("date", "date_time", "datetime", "timestamp") or ct in ("date", "date_time"):
        d = _BASE_DATE + datetime.timedelta(days=s % 365)
        if t == "date" or ct == "date":
            return d.isoformat()
        return datetime.datetime(d.year, d.month, d.day,
                                 s % 24, s % 60, 0,
                                 tzinfo=datetime.timezone.utc).isoformat()

    # string heuristics by field name
    n = s % 1000
    if "email" in nm:
        return "user%d@example.com" % n
    if nm == "id" or nm.endswith("_id") or nm.endswith("id"):
        return "%s_%d" % (nm or "id", n)
    if "url" in nm or "link" in nm:
        return "https://example.com/%d" % n
    if "phone" in nm:
        return "+1555%07d" % (s % 10000000)
    if "name" in nm:
        return "Name %d" % n
    if "date" in nm or "time" in nm:
        return (_BASE_DATE + datetime.timedelta(days=s % 365)).isoformat()
    if "status" in nm:
        return ["active", "pending", "closed"][s % 3]
    return "value_%d" % n


def _field(field, key, depth):
    t = (field.get("type") or "").lower()
    props = field.get("properties")
    if t == "array" and depth < _MAX_DEPTH:
        if props:
            return [fabricate(props, "%s[%d]" % (key, i), depth + 1)
                    for i in range(_ARRAY_LEN)]
        return [_scalar(field, "%s[%d]" % (key, i)) for i in range(_ARRAY_LEN)]
    if t == "object" and depth < _MAX_DEPTH:
        return fabricate(props or [], key, depth + 1)
    return _scalar(field, key)


def fabricate(schema, seedkey, depth=0):
    """Build a dict matching `schema` (a list of Workato field dicts)."""
    if not isinstance(schema, list):
        return {}
    out = {}
    for f in schema:
        if not isinstance(f, dict):
            continue
        nm = f.get("name")
        if not nm:
            continue
        out[nm] = _field(f, "%s.%s" % (seedkey, nm), depth)
    return out
