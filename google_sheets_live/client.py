"""
google_sheets_live/client.py - a thin live Google Sheets REST client (stdlib only).

No third-party deps. Auth mirrors the Salesforce CLI pattern: the access token is
minted by the `gcloud` CLI (`gcloud auth print-access-token`), so the user just runs
`gcloud auth login --enable-gdrive-access` once (the Drive scope covers the Sheets
API). On a 401 the token is re-minted and the call retried.

Config (test_sandbox/.env or env):
  SHEETS_SPREADSHEET_ID = <target spreadsheet id>   (required -> else stays mocked)
  SHEETS_TAB            = Sheet1                     (default tab)

Covers what the recipes need: append rows + read values back (for verification).
"""
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(HERE), ".env")
API = "https://sheets.googleapis.com/v4"


class SheetsError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__("SHEETS %s: %s" % (status, body))


def load_sheets_env(path=ENV_PATH):
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("SHEETS_SPREADSHEET_ID", "SHEETS_TAB"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return {k: env[k] for k in ("SHEETS_SPREADSHEET_ID", "SHEETS_TAB") if env.get(k)}


def _ssl_ctx():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


class SheetsClient:
    def __init__(self, env=None):
        self.env = env if env is not None else load_sheets_env()
        self.spreadsheet_id = self.env.get("SHEETS_SPREADSHEET_ID")
        self.tab = self.env.get("SHEETS_TAB", "Sheet1")
        if not self.spreadsheet_id:
            raise SheetsError(0, "missing SHEETS_SPREADSHEET_ID in .env")
        self.ctx = _ssl_ctx()
        self.token = None

    @classmethod
    def from_env(cls):
        env = load_sheets_env()
        if not env.get("SHEETS_SPREADSHEET_ID"):
            return None
        try:                                   # need the gcloud CLI to mint tokens
            subprocess.run(["gcloud", "--version"], capture_output=True, timeout=15)
        except Exception:
            return None
        return cls(env)

    def _auth(self):
        out = subprocess.run(["gcloud", "auth", "print-access-token"],
                             capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            raise SheetsError(0, "gcloud token failed: %s" % (out.stderr or "")[:200])
        self.token = out.stdout.strip()

    def _req(self, method, path, body=None):
        if not self.token:
            self._auth()
        url = API + path
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(2):
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, context=self.ctx, timeout=60) as r:
                    raw = r.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                raw = e.read().decode()
                try:
                    raw = json.loads(raw)
                except Exception:
                    pass
                if e.code == 401 and attempt == 0:    # token expired -> re-mint
                    self._auth()
                    continue
                raise SheetsError(e.code, raw)

    # -- API surface -------------------------------------------------------
    def append(self, values, spreadsheet_id=None, tab=None):
        """Append rows (list of lists) to the sheet."""
        sid = spreadsheet_id or self.spreadsheet_id
        rng = tab or self.tab
        return self._req("POST", "/spreadsheets/%s/values/%s:append"
                         "?valueInputOption=RAW&insertDataOption=INSERT_ROWS" % (sid, rng),
                         body={"values": values})

    def get_values(self, spreadsheet_id=None, tab=None):
        sid = spreadsheet_id or self.spreadsheet_id
        rng = tab or self.tab
        return self._req("GET", "/spreadsheets/%s/values/%s" % (sid, rng)).get("values", [])
