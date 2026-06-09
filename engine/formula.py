"""
formula.py - Phase 3 formula engine.

Evaluates the Ruby-flavored expressions that appear inside #{...}, plus the
structured if/elsif condition trees. Three public entry points:

  interpolate(s, ctx)          -> resolve #{...} inside a string value
  evaluate(expr, ctx)          -> evaluate a single bare expression
  eval_condition_tree(node, ctx) -> bool, for if/elsif conditions

Design: a small tokenizer + Pratt (precedence-climbing) parser -> AST, then an
evaluator with a method-dispatch table covering the 42 methods the corpus uses.
Unsupported constructs raise FormulaError; the interpreter catches these and
degrades the value to None (so coverage can grow without breaking ping-through).
"""
import datetime
import hashlib
import json
import re

from . import refs


class FormulaError(Exception):
    pass


class _Skip:
    def __repr__(self):
        return "<SKIP>"


SKIP = _Skip()


class _Workato:
    """The Workato global object (workato.uuid, workato.timestamp, ...)."""


WORKATO = _Workato()


def _det_str(key):
    return "value_%d" % (int(hashlib.md5(str(key).encode("utf-8")).hexdigest()[:6], 16) % 100000)


# --------------------------------------------------------------------------- #
# tokenizer                                                                   #
# --------------------------------------------------------------------------- #
_TOK = re.compile(r"""
    (?P<nl>[\r\n]+)
  | (?P<ws>[ \t]+)
  | (?P<num>\d+\.\d+|\d+)
  | (?P<dstr>"(?:\\.|[^"\\])*")
  | (?P<sstr>'(?:\\.|[^'\\])*')
  | (?P<op>&\.|==|!=|<=|>=|=>|&&|\|\||[-+*/%<>!.,()\[\]{}?:=])
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*[?!]?)
""", re.VERBOSE)

_KEYWORDS = {"if", "elsif", "else", "end", "unless", "then", "do"}

_REGEX_PRECEDERS = {None, "(", "[", ",", "==", "!=", "<", ">", "<=", ">=",
                    "&&", "||", "!", "+", "-", "*", "%", "and", "or", ":", "?"}


def _unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def tokenize(s):
    toks = []
    i = 0
    n = len(s)
    last = None
    while i < n:
        # regex literal: a '/' where an operand is expected
        if s[i] == "/" and last in _REGEX_PRECEDERS:
            j = i + 1
            buf = []
            while j < n and s[j] != "/":
                if s[j] == "\\" and j + 1 < n:
                    buf.append(s[j:j + 2])
                    j += 2
                else:
                    buf.append(s[j])
                    j += 1
            j += 1                                   # closing /
            while j < n and s[j] in "imxo":          # flags
                j += 1
            toks.append(("regex", "".join(buf)))
            last = "regex"
            i = j
            continue
        m = _TOK.match(s, i)
        if not m:
            raise FormulaError("cannot tokenize at %r" % s[i:i + 12])
        i = m.end()
        kind = m.lastgroup
        val = m.group()
        if kind == "ws":
            continue
        if kind == "nl":
            toks.append(("nl", "\n"))
            last = None
            continue
        if kind == "num":
            toks.append(("num", float(val) if "." in val else int(val)))
        elif kind in ("dstr", "sstr"):
            toks.append(("str", _unescape(val[1:-1])))
        elif kind == "op":
            toks.append(("op", val))
        elif kind == "ident":
            if val in ("and", "or"):
                toks.append(("op", val))
            elif val in _KEYWORDS:
                toks.append(("kw", val))
            else:
                toks.append(("ident", val))
        last = toks[-1][1] if toks else None
    toks.append(("eof", None))
    return toks


# --------------------------------------------------------------------------- #
# parser (Pratt)                                                              #
# --------------------------------------------------------------------------- #
# AST nodes are tuples: (tag, ...)
_BINPREC = {
    "or": 1, "||": 1, "and": 2, "&&": 2,
    "==": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 4, "-": 4, "*": 5, "/": 5, "%": 5,
}


class _Parser:
    def __init__(self, toks):
        self.toks = toks
        self.p = 0

    def peek(self):
        return self.toks[self.p]

    def next(self):
        t = self.toks[self.p]
        self.p += 1
        return t

    def expect(self, val):
        k, v = self.next()
        if v != val:
            raise FormulaError("expected %r got %r" % (val, v))

    def parse(self):
        seq = self.stmt_seq()
        self._skip_nl()
        if self.peek()[0] != "eof":
            raise FormulaError("trailing tokens: %r" % (self.peek(),))
        return seq

    # -- statement layer (Ruby if/elsif/else/end, assignments, sequences) --
    def _skip_nl(self):
        while self.peek()[0] == "nl":
            self.next()

    def _at_block_end(self):
        k, v = self.peek()
        return k == "eof" or (k == "kw" and v in ("elsif", "else", "end"))

    def stmt_seq(self):
        stmts = []
        while True:
            self._skip_nl()
            if self._at_block_end():
                break
            before = self.p
            stmts.append(self.stmt())
            self._skip_nl()
            if self.p == before:            # no progress -> stop (avoid loop)
                break
        return ("seq", stmts)

    def stmt(self):
        k, v = self.peek()
        if k == "kw" and v in ("if", "unless"):
            return self.if_stmt()
        if k == "ident" and self.toks[self.p + 1] == ("op", "="):
            name = self.next()[1]
            self.next()                     # '='
            self._skip_nl()
            return ("assign", name, self.ternary())
        return self.ternary()

    def if_stmt(self):
        _, kw = self.next()                 # if / unless
        cond = self.ternary()
        if self.peek() == ("kw", "then"):
            self.next()
        self._skip_nl()
        then_seq = self.stmt_seq()
        elifs = []
        while self.peek() == ("kw", "elsif"):
            self.next()
            c = self.ternary()
            if self.peek() == ("kw", "then"):
                self.next()
            self._skip_nl()
            elifs.append((c, self.stmt_seq()))
        else_seq = None
        if self.peek() == ("kw", "else"):
            self.next()
            self._skip_nl()
            else_seq = self.stmt_seq()
        if self.peek() != ("kw", "end"):
            raise FormulaError("expected 'end'")
        self.next()
        return ("ifst", cond, then_seq, elifs, else_seq, kw == "unless")

    def ternary(self):
        cond = self.binary(0)
        if self.peek() == ("op", "?"):
            self.next()
            self._skip_nl()
            a = self.ternary()
            self.expect(":")
            self._skip_nl()
            b = self.ternary()
            return ("tern", cond, a, b)
        return cond

    def binary(self, minprec):
        left = self.unary()
        while True:
            k, v = self.peek()
            if k == "op" and v in _BINPREC and _BINPREC[v] >= minprec:
                self.next()
                self._skip_nl()                  # line-continuation after operator
                right = self.binary(_BINPREC[v] + 1)
                left = ("bin", v, left, right)
            else:
                return left

    def unary(self):
        k, v = self.peek()
        if v == "-":
            self.next()
            return ("neg", self.unary())
        if v == "+":                                 # unary plus -> identity
            self.next()
            return self.unary()
        if v == "!":
            self.next()
            return ("not", self.unary())
        return self.postfix()

    def postfix(self):
        node = self.primary()
        while True:
            k, v = self.peek()
            if v == "." or v == "&.":
                safe = (v == "&.")
                self.next()
                mk, mname = self.next()
                args = []
                if self.peek() == ("op", "("):
                    args = self.call_args()
                node = ("method", node, mname, args, safe)
            elif v == "[":
                self.next()
                idx = [self.ternary()]
                while self.peek() == ("op", ","):
                    self.next()
                    idx.append(self.ternary())
                self.expect("]")
                node = ("index", node, idx)
            else:
                return node

    def call_args(self):
        self.expect("(")
        self._skip_nl()
        args = []
        if self.peek() == ("op", ")"):
            self.next()
            return args
        while True:
            # keyword/hash-pair arg:  "key": value  or  key: value
            if (self.peek()[0] in ("str", "ident")
                    and self.toks[self.p + 1] == ("op", ":")):
                key = self.next()[1]
                self.next()                          # ':'
                val = self.ternary()
                args.append(("pair", key, val))
            else:
                args.append(self.ternary())
            self._skip_nl()
            if self.peek() == ("op", ","):
                self.next()
                self._skip_nl()
                continue
            break
        self.expect(")")
        return args

    def primary(self):
        k, v = self.next()
        if k == "num":
            return ("lit", v)
        if k == "str":
            return ("lit", v)
        if k == "regex":
            return ("regex", v)
        if v == "(":
            node = self.ternary()
            self.expect(")")
            return node
        if v == "[":
            self._skip_nl()
            items = []
            if self.peek() != ("op", "]"):
                items.append(self.ternary())
                self._skip_nl()
                while self.peek() == ("op", ","):
                    self.next()
                    self._skip_nl()
                    items.append(self.ternary())
                    self._skip_nl()
            self.expect("]")
            return ("array", items)
        if v == "{":
            self._skip_nl()
            pairs = []
            if self.peek() != ("op", "}"):
                while True:
                    kk, kv = self.next()
                    if kk not in ("str", "ident", "num"):
                        raise FormulaError("bad hash key %r" % (kv,))
                    sep = self.next()[1]
                    if sep not in (":", "=>"):
                        raise FormulaError("expected : in hash, got %r" % sep)
                    self._skip_nl()
                    pairs.append((kv, self.ternary()))
                    self._skip_nl()
                    if self.peek() == ("op", ","):
                        self.next()
                        self._skip_nl()
                        continue
                    break
            self.expect("}")
            return ("hash", pairs)
        if v == ":":                                 # :symbol literal
            sk, sv = self.next()
            return ("lit", sv)
        if k == "ident":
            if v == "_ref" and self.peek() == ("op", "("):
                return ("ref", self.call_args())
            if v == "true":
                return ("lit", True)
            if v == "false":
                return ("lit", False)
            if v in ("nil", "null"):
                return ("lit", None)
            if v == "skip":
                return ("lit", SKIP)
            if self.peek() == ("op", "("):           # bare function call: lookup(...), uuid(...)
                return ("funcall", v, self.call_args())
            return ("name", v)
        raise FormulaError("unexpected token %r" % (v,))


def parse(expr):
    return _Parser(tokenize(expr)).parse()


# --------------------------------------------------------------------------- #
# evaluator                                                                   #
# --------------------------------------------------------------------------- #
def _blank(v):
    if v is None or v is refs.MISSING or v is SKIP:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def _is_true(v):
    return v in (True, "true", "True", 1, "1")


def _num(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return int(v) if re.fullmatch(r"-?\d+", v.strip()) else float(v)
        except ValueError:
            raise FormulaError("not numeric: %r" % v)
    raise FormulaError("not numeric: %r" % (v,))


def _to_dt(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(s)
        except ValueError:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.datetime.strptime(s[:len(fmt) + 6], fmt)
                except ValueError:
                    continue
    raise FormulaError("not a date: %r" % (v,))


# a tiny country map for to_country_alpha2 (common cases); fallback = first 2 up
_COUNTRY = {
    "united states": "US", "usa": "US", "us": "US", "united kingdom": "GB",
    "uk": "GB", "canada": "CA", "australia": "AU", "germany": "DE",
    "france": "FR", "india": "IN", "japan": "JP", "china": "CN",
    "singapore": "SG", "brazil": "BR", "mexico": "MX", "spain": "ES",
    "italy": "IT", "netherlands": "NL",
}


def _funcall(name, args, ev):
    """Bare function call: lookup(table, key), uuid(), etc. -> fabricated value."""
    if name == "lookup":
        return _det_str(("lookup",) + tuple(str(a) for a in args))
    if name == "uuid":
        return "00000000-0000-4000-8000-000000000000"
    return None                                  # unknown function -> degrade


def _method(recv, name, args, ev):
    """Dispatch a method call. `args` already evaluated (with pairs as tuples)."""
    pos = [a for a in args if not (isinstance(a, tuple) and a and a[0] == "__pair__")]
    pairs = dict((a[1], a[2]) for a in args if isinstance(a, tuple) and a and a[0] == "__pair__")

    if recv is WORKATO:                          # workato.uuid / workato.timestamp / ...
        if name == "uuid":
            return "00000000-0000-4000-8000-000000000000"
        if name in ("timestamp", "now"):
            return _to_dt(ev.scope["now"])
        return None

    # duration helpers on numbers
    if name in ("weeks", "week"):
        return datetime.timedelta(weeks=_num(recv))
    if name in ("days", "day"):
        return datetime.timedelta(days=_num(recv))
    if name in ("hours", "hour"):
        return datetime.timedelta(hours=_num(recv))
    if name in ("minutes", "minute"):
        return datetime.timedelta(minutes=_num(recv))
    if name in ("seconds", "second"):
        return datetime.timedelta(seconds=_num(recv))
    if name in ("months", "month"):
        return datetime.timedelta(days=30 * _num(recv))
    if name in ("years", "year"):
        return datetime.timedelta(days=365 * _num(recv))

    if name in ("present?", "present"):
        return not _blank(recv)
    if name in ("blank?", "blank"):
        return _blank(recv)
    if name == "presence":
        return None if _blank(recv) else recv
    if name in ("is_true?", "is_true"):
        return _is_true(recv)
    if name in ("is_not_true?", "is_not_true"):
        return not _is_true(recv)
    if name in ("include?", "includes?"):
        try:
            return pos[0] in recv
        except TypeError:
            return False
    if name == "to_s":
        return "" if recv is None or recv is refs.MISSING else str(recv)
    if name == "to_i":
        return int(_num(recv))
    if name == "to_f":
        return float(_num(recv))
    if name == "to_json":
        return json.dumps(recv if recv is not refs.MISSING else None)
    if name == "to_param":
        return str(recv)
    if name in ("downcase", "lower"):
        return str(recv).lower()
    if name in ("upcase", "upper"):
        return str(recv).upper()
    if name == "capitalize":
        return str(recv).capitalize()
    if name == "titleize":
        return re.sub(r"[_\s]+", " ", str(recv)).title()
    if name == "strip":
        return str(recv).strip()
    if name == "reverse":
        return recv[::-1] if isinstance(recv, (str, list)) else str(recv)[::-1]
    if name == "split":
        sep = pos[0] if pos else None
        return str(recv).split(sep) if sep else str(recv).split()
    if name == "join":
        sep = pos[0] if pos else ""
        return sep.join("" if x is None else str(x) for x in (recv or []))
    if name == "smart_join":
        sep = pos[0] if pos else ""
        return sep.join(str(x) for x in (recv or []) if not _blank(x))
    if name == "concat":
        if isinstance(recv, list):
            return recv + (pos[0] if pos else [])
        return str(recv) + "".join(str(p) for p in pos)
    if name in ("gsub", "sub"):
        pat, rep = pos[0], (pos[1] if len(pos) > 1 else "")
        count = 0 if name == "gsub" else 1
        try:
            return re.sub(pat, rep.replace("\\\\", "\\"), str(recv), count=count)
        except re.error as e:
            raise FormulaError("bad regex: %s" % e)
    if name in ("match", "match?"):
        try:
            m = re.search(pos[0], str(recv)) if pos else None
        except re.error as e:
            raise FormulaError("bad regex: %s" % e)
        return bool(m) if name == "match?" else (m.group(0) if m else None)
    if name == "dig":
        return refs.dig(recv, pos, ev.ctx)
    if name == "pluck":
        keys = pos[0] if (pos and isinstance(pos[0], list)) else pos
        rows = recv or []
        if len(keys) == 1:
            return [r.get(keys[0]) if isinstance(r, dict) else None for r in rows]
        return [[r.get(k) if isinstance(r, dict) else None for k in keys] for r in rows]
    if name == "uniq":
        seen, out = set(), []
        for x in (recv or []):
            key = json.dumps(x, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out
    if name == "compact":
        return [x for x in (recv or []) if x is not None]
    if name == "flatten":
        out = []
        for x in (recv or []):
            out.extend(x) if isinstance(x, list) else out.append(x)
        return out
    if name == "first":
        return recv[0] if isinstance(recv, list) and recv else (None if isinstance(recv, list) else recv)
    if name == "last":
        return recv[-1] if isinstance(recv, list) and recv else (None if isinstance(recv, list) else recv)
    if name in ("count", "size", "length"):
        return len(recv) if isinstance(recv, (list, dict, str)) else 0
    if name == "sort":
        return sorted(recv or [])
    if name == "sum":
        return sum(_num(x) for x in (recv or []))
    if name == "scan":
        try:
            return re.findall(pos[0], str(recv))
        except re.error as e:
            raise FormulaError("bad regex: %s" % e)
    if name == "to_csv":
        rows = recv if isinstance(recv, list) else []
        lines = []
        for r in rows:
            if isinstance(r, (list, tuple)):
                lines.append(",".join("" if x is None else str(x) for x in r))
            else:
                lines.append("" if r is None else str(r))
        return "\n".join(lines)
    if name == "except":
        return {k: v for k, v in (recv or {}).items() if k not in pos}
    if name == "slice":
        if isinstance(recv, str):
            a = int(pos[0])
            return recv[a:a + int(pos[1])] if len(pos) > 1 else recv[a:]
        return recv
    if name == "floor":
        import math
        return math.floor(_num(recv))
    if name == "ceil":
        import math
        return math.ceil(_num(recv))
    if name == "round":
        return round(_num(recv), int(pos[0]) if pos else 0)
    if name == "abs":
        return abs(_num(recv))
    if name == "rjust":
        return str(recv).rjust(int(pos[0]), str(pos[1]) if len(pos) > 1 else " ")
    if name == "ljust":
        return str(recv).ljust(int(pos[0]), str(pos[1]) if len(pos) > 1 else " ")
    if name == "to_date":
        return _to_dt(recv).date() if not isinstance(recv, datetime.date) else recv
    if name == "to_time":
        return _to_dt(recv)
    if name in ("ago", "from_now"):
        base = _to_dt(ev.scope["now"])
        if isinstance(recv, datetime.timedelta):
            return base - recv if name == "ago" else base + recv
        return base
    if name in ("beginning_of_day", "at_beginning_of_day", "midnight"):
        return _to_dt(recv).replace(hour=0, minute=0, second=0, microsecond=0)
    if name == "end_of_day":
        return _to_dt(recv).replace(hour=23, minute=59, second=59, microsecond=0)
    if name == "format_map":
        fmt = pos[0] if pos else "%s"
        out = []
        for r in (recv or []):
            try:
                out.append(fmt.format(**r) if isinstance(r, dict) else (fmt % r))
            except Exception:
                out.append(str(r))
        return "\n".join(out)
    if name == "strftime":
        return _to_dt(recv).strftime(pos[0])
    if name in ("in_time_zone", "utc"):
        return _to_dt(recv)                     # tz best-effort: identity
    if name == "now":
        return _to_dt(ev.scope["now"])
    if name == "to_country_alpha2":
        s = str(recv).strip().lower()
        return _COUNTRY.get(s, str(recv).strip()[:2].upper())
    if name == "extname":
        import os
        return os.path.splitext(str(recv))[1]
    if name == "quote":
        return "'%s'" % str(recv).replace("'", "''")
    if name == "where":
        return _where(recv, pairs)
    if name == "lstrip":
        return str(recv).lstrip()
    if name == "rstrip":
        return str(recv).rstrip()
    if name == "wday":
        return (_to_dt(recv).weekday() + 1) % 7      # Ruby: Sunday = 0
    if name in ("year", "month", "day", "hour", "min", "sec"):
        d = _to_dt(recv)
        return {"year": d.year, "month": d.month, "day": d.day,
                "hour": getattr(d, "hour", 0), "min": getattr(d, "minute", 0),
                "sec": getattr(d, "second", 0)}[name]
    if name in ("beginning_of_month", "at_beginning_of_month"):
        return _to_dt(recv).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if name == "end_of_month":
        d = _to_dt(recv)
        nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        return nxt - datetime.timedelta(days=1)
    if name in ("encode_url", "url_encode"):
        import urllib.parse
        return urllib.parse.quote(str(recv), safe="")
    if name == "unicode_normalize":
        import unicodedata
        return unicodedata.normalize("NFC", str(recv))
    if name in ("length",):
        return len(recv) if isinstance(recv, (list, dict, str)) else 0
    if name == "starts_with?":
        return str(recv).startswith(str(pos[0])) if pos else False
    if name == "ends_with?":
        return str(recv).endswith(str(pos[0])) if pos else False
    if name == "to_currency":
        try:
            return "${:,.2f}".format(_num(recv))
        except FormulaError:
            return str(recv)
    if name == "strip_tags":
        return re.sub(r"<[^>]+>", "", str(recv))
    if name in ("beginning_of_week", "at_beginning_of_week"):
        d = _to_dt(recv)
        return d - datetime.timedelta(days=d.weekday())
    if name == "end_of_week":
        d = _to_dt(recv)
        return d + datetime.timedelta(days=6 - d.weekday())

    raise FormulaError("unimplemented method .%s" % name)


def _where(rows, pairs):
    """Minimal Workato .where: pairs are {"field op": value}."""
    if not isinstance(rows, list):
        return rows
    def keep(row):
        for key, want in pairs.items():
            parts = key.rsplit(" ", 1)
            field, op = (parts[0], parts[1]) if len(parts) == 2 else (key, "==")
            have = row.get(field) if isinstance(row, dict) else None
            if op in ("<=",) and not (have <= want):
                return False
            if op in (">=",) and not (have >= want):
                return False
            if op in ("<",) and not (have < want):
                return False
            if op in (">",) and not (have > want):
                return False
            if op in ("==", "=") and not (have == want):
                return False
        return True
    return [r for r in rows if keep(r)]


class _Env:
    def __init__(self, ctx):
        self.ctx = ctx
        self.locals = {}                             # assignment targets
        cur = ctx.current_scope
        self.scope = {
            "now": ctx.clock["now"],
            "today": _to_dt(ctx.clock["now"]).date(),
            "field": cur.get("field"),
            "index": cur.get("index"),
            "input": ctx.fixtures.get("config", {}),
            "event": ctx.fixtures.get("trigger", {}),
            "clear": None,                           # Workato 'clear' = empty field
        }


def _eval(node, ev):
    tag = node[0]
    if tag == "lit":
        return node[1]
    if tag == "regex":
        return node[1]
    if tag == "array":
        return [_eval(x, ev) for x in node[1]]
    if tag == "hash":
        return {k: _eval(v, ev) for k, v in node[1]}
    if tag == "seq":
        val = None
        for s in node[1]:
            val = _eval(s, ev)
        return val
    if tag == "assign":
        val = _eval(node[2], ev)
        ev.locals[node[1]] = val
        return val
    if tag == "ifst":
        _, cond, then_s, elifs, else_s, is_unless = node
        c = _truthy(_eval(cond, ev))
        if is_unless:
            c = not c
        if c:
            return _eval(then_s, ev)
        for ec, es in elifs:
            if _truthy(_eval(ec, ev)):
                return _eval(es, ev)
        return _eval(else_s, ev) if else_s is not None else None
    if tag == "funcall":
        return _funcall(node[1], [_eval(a, ev) for a in node[2]
                                  if not (isinstance(a, tuple) and a and a[0] == "pair")], ev)
    if tag == "name":
        nm = node[1]
        if nm in ev.locals:
            return ev.locals[nm]
        if nm == "today":
            return ev.scope["today"]
        if nm == "now":
            return _to_dt(ev.scope["now"])
        if nm == "workato":
            return WORKATO
        if nm in ev.scope:
            return ev.scope[nm]
        raise FormulaError("unknown name %r" % nm)
    if tag == "ref":
        prov, line, path = [_eval(a, ev) if isinstance(a, tuple) else a for a in
                            _ref_args(node[1], ev)]
        v = refs.resolve(prov, line, path, ev.ctx)
        return None if v is refs.MISSING else v
    if tag == "neg":
        return -_num(_eval(node[1], ev))
    if tag == "not":
        return not _truthy(_eval(node[1], ev))
    if tag == "tern":
        return _eval(node[2], ev) if _truthy(_eval(node[1], ev)) else _eval(node[3], ev)
    if tag == "bin":
        return _binop(node[1], node[2], node[3], ev)
    if tag == "index":
        recv = _eval(node[1], ev)
        idxs = [_eval(x, ev) for x in node[2]]
        return _do_index(recv, idxs)
    if tag == "method":
        recv = _eval(node[1], ev)
        if len(node) > 4 and node[4] and (recv is None or recv is refs.MISSING):
            return None                          # &. safe navigation on nil
        args = []
        for a in node[3]:
            if a[0] == "pair":
                args.append(("__pair__", a[1], _eval(a[2], ev)))
            else:
                args.append(_eval(a, ev))
        return _method(recv, node[2], args, ev)
    raise FormulaError("cannot eval node %r" % (tag,))


def _ref_args(arglist, ev):
    """_ref's three args are literal-ish; eval them to (provider, line, path)."""
    out = []
    for a in arglist:
        out.append(_eval(a, ev))
    if len(out) != 3:
        raise FormulaError("_ref expects 3 args")
    return out


def _truthy(v):
    if v is None or v is refs.MISSING or v is SKIP or v is False:
        return False
    if v == "" or v == [] or v == {}:
        return False
    return True


def _do_index(recv, idxs):
    if recv is None or recv is refs.MISSING:
        return None
    if len(idxs) == 2 and isinstance(recv, (str, list)):
        a, b = int(idxs[0]), int(idxs[1])
        return recv[a:a + b]
    key = idxs[0]
    if isinstance(recv, list):
        try:
            return recv[int(key)]
        except (IndexError, ValueError, TypeError):
            return None
    if isinstance(recv, dict):
        return recv.get(key)
    return None


def _binop(op, ln, rn, ev):
    if op in ("and", "&&"):
        l = _eval(ln, ev)
        return _eval(rn, ev) if _truthy(l) else l
    if op in ("or", "||"):
        l = _eval(ln, ev)
        return l if _truthy(l) else _eval(rn, ev)
    l = _eval(ln, ev)
    r = _eval(rn, ev)
    if op == "+":
        if isinstance(l, str) or isinstance(r, str):
            return ("" if l is None else str(l)) + ("" if r is None else str(r))
        if isinstance(l, list):
            return l + (r or [])
        if isinstance(l, (datetime.date, datetime.datetime)) and isinstance(r, datetime.timedelta):
            return l + r
        return _num(l) + _num(r)
    if op == "-":
        if isinstance(l, (datetime.date, datetime.datetime)) and isinstance(r, datetime.timedelta):
            return l - r
        return _num(l) - _num(r)
    if op == "*":
        return _num(l) * _num(r)
    if op == "/":
        rr = _num(r)
        return _num(l) / rr if rr else None
    if op == "%":
        rr = _num(r)
        return _num(l) % rr if rr else None
    if op == "==":
        return l == r or str(l) == str(r)
    if op == "!=":
        return not (l == r or str(l) == str(r))
    if op in ("<", ">", "<=", ">="):
        try:
            l, r = _num(l), _num(r)
        except FormulaError:
            l, r = str(l), str(r)
        return {"<": l < r, ">": l > r, "<=": l <= r, ">=": l >= r}[op]
    raise FormulaError("bad operator %r" % op)


def evaluate(expr, ctx):
    """Evaluate a single bare expression string."""
    return _eval(parse(expr), _Env(ctx))


# --------------------------------------------------------------------------- #
# interpolation (#{...} inside a field value)                                 #
# --------------------------------------------------------------------------- #
def _spans(s):
    spans = []
    i, n = 0, len(s)
    while i < n:
        if s[i] == "#" and i + 1 < n and s[i + 1] == "{":
            depth, in_str, esc, q, k = 0, False, False, "", i + 1
            while k < n:
                c = s[k]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == q:
                        in_str = False
                else:
                    if c in ('"', "'"):
                        in_str, q = True, c
                    elif c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            spans.append((i, k + 1))
                            break
                k += 1
            i = k + 1
        else:
            i += 1
    return spans


def interpolate(s, ctx, errors=None):
    """Resolve #{...} in a string. On a formula error, that fragment -> None
    (and the error is appended to `errors` if provided, for coverage tracking)."""
    # leading '=' marks a formula-mode field: the whole value is one expression
    if s[:1] == "=" and s[1:2] != "=" and "#{" not in s:
        try:
            return evaluate(s[1:].strip(), ctx)
        except Exception as e:           # a bad formula must never crash a recipe
            if errors is not None:
                errors.append(str(e))
            return None

    spans = _spans(s)
    if not spans:
        return s

    def one(inner):
        try:
            return evaluate(inner, ctx)
        except Exception as e:           # FormulaError or any runtime error -> None
            if errors is not None:
                errors.append(str(e))
            return None

    if len(spans) == 1 and spans[0] == (0, len(s)):
        return one(s[2:-1])
    out, pos = [], 0
    for a, b in spans:
        out.append(s[pos:a])
        v = one(s[a + 2:b - 1])
        out.append("" if v is None or v is refs.MISSING or v is SKIP else str(v))
        pos = b
    out.append(s[pos:])
    return "".join(out)


# --------------------------------------------------------------------------- #
# if/elsif condition trees                                                     #
# --------------------------------------------------------------------------- #
def _cmp(op, lhs, rhs):
    if op == "present":
        return not _blank(lhs)
    if op == "blank":
        return _blank(lhs)
    if op == "is_true":
        return _is_true(lhs)
    if op == "is_not_true":
        return not _is_true(lhs)
    if op == "equals_to":
        return lhs == rhs or str(lhs) == str(rhs)
    if op == "not_equals_to":
        return not (lhs == rhs or str(lhs) == str(rhs))
    if op == "contains":
        return str(rhs) in str(lhs) if not isinstance(lhs, list) else rhs in lhs
    if op == "not_contains":
        return not (_cmp("contains", lhs, rhs))
    if op == "starts_with":
        return str(lhs).startswith(str(rhs))
    if op == "not_starts_with":
        return not str(lhs).startswith(str(rhs))
    if op == "ends_with":
        return str(lhs).endswith(str(rhs))
    if op == "not_ends_with":
        return not str(lhs).endswith(str(rhs))
    if op in ("greater_than", "less_than"):
        try:
            l, r = _num(lhs), _num(rhs)
        except FormulaError:
            l, r = str(lhs), str(rhs)
        return l > r if op == "greater_than" else l < r
    return True                                  # unknown / empty operand


def eval_condition_tree(node, ctx, errors=None):
    if not isinstance(node, dict):
        return True
    if node.get("type") == "compound":
        conds = node.get("conditions", [])
        results = [eval_condition_tree(c, ctx, errors) for c in conds]
        if not results:
            return True
        return any(results) if node.get("operand") == "or" else all(results)
    # leaf condition
    op = node.get("operand")
    lhs = interpolate(node.get("lhs", ""), ctx, errors) if isinstance(node.get("lhs"), str) else node.get("lhs")
    rhs = interpolate(node.get("rhs", ""), ctx, errors) if isinstance(node.get("rhs"), str) else node.get("rhs")
    if rhs == "":
        rhs = None
    try:
        return _cmp(op, lhs, rhs)
    except Exception:
        return True
