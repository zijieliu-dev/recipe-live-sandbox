"""
client.py - a thin live Salesforce REST client (stdlib only).

No third-party deps (works behind Zscaler via SSL_CERT_FILE). Supports the two
OAuth2 connected-app flows that work headless:
  - refresh_token grant   (SF_REFRESH_TOKEN)
  - password grant        (SF_USERNAME + SF_PASSWORD [+ SF_SECURITY_TOKEN])

Credentials come from test_sandbox/.env (gitignored) or the environment.

Methods cover what the chosen recipes need:
  query / query_all / describe_global / describe /
  get / create / update / upsert / delete
"""
import json
import os
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(HERE), ".env")
API_VERSION = "v59.0"


class SalesforceError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__("SF %s: %s" % (status, body))


def load_env(path=ENV_PATH):
    """Read KEY=VALUE lines from .env (env vars take precedence)."""
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("SF_LOGIN_URL", "SF_CLIENT_ID", "SF_CLIENT_SECRET", "SF_REFRESH_TOKEN",
              "SF_USERNAME", "SF_PASSWORD", "SF_SECURITY_TOKEN", "SF_API_VERSION",
              "SF_INSTANCE_URL"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def _ssl_ctx():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


class SalesforceClient:
    def __init__(self, env=None):
        self.env = env or load_env()
        self.ctx = _ssl_ctx()
        self.api = self.env.get("SF_API_VERSION", API_VERSION)
        self.access_token = None
        self.instance_url = self.env.get("SF_INSTANCE_URL")
        self._cli_alias = None              # set when authed via the CLI (for re-auth)

    @classmethod
    def from_cli(cls, alias=None, api_version=API_VERSION):
        """Authenticate using the Salesforce CLI's stored org (the primary path).
        Pulls accessToken + instanceUrl from `sf org display --json`."""
        c = cls(env={})
        c.api = api_version
        c._cli_alias = alias
        c._cli_auth()
        return c

    def _cli_auth(self):
        cmd = ["sf", "org", "display", "--json"]
        if self._cli_alias:
            cmd += ["--target-org", self._cli_alias]
        out = subprocess.run(cmd, capture_output=True, text=True)
        try:
            res = json.loads(out.stdout)["result"]
        except Exception:
            raise SalesforceError(0, "sf CLI org display failed: %s" % (out.stderr or out.stdout)[:200])
        self.access_token = res["accessToken"]
        self.instance_url = res["instanceUrl"]

    # -- auth --------------------------------------------------------------
    def authenticate(self):
        login = self.env.get("SF_LOGIN_URL", "https://login.salesforce.com")
        params = {
            "client_id": self.env.get("SF_CLIENT_ID", ""),
            "client_secret": self.env.get("SF_CLIENT_SECRET", ""),
        }
        if self.env.get("SF_REFRESH_TOKEN"):
            params["grant_type"] = "refresh_token"
            params["refresh_token"] = self.env["SF_REFRESH_TOKEN"]
        elif self.env.get("SF_USERNAME"):
            params["grant_type"] = "password"
            params["username"] = self.env["SF_USERNAME"]
            params["password"] = self.env.get("SF_PASSWORD", "") + self.env.get("SF_SECURITY_TOKEN", "")
        else:
            raise SalesforceError(0, "no SF_REFRESH_TOKEN or SF_USERNAME in .env")

        status, body = self._raw("POST", login + "/services/oauth2/token",
                                 data=urllib.parse.urlencode(params).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
        if status != 200:
            raise SalesforceError(status, body)
        self.access_token = body["access_token"]
        self.instance_url = body.get("instance_url", self.instance_url)
        return self

    # -- low level ---------------------------------------------------------
    def _raw(self, method, url, data=None, headers=None, tries=4):
        last = None
        for attempt in range(tries):
            req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
            try:
                with urllib.request.urlopen(req, context=self.ctx, timeout=60) as r:
                    raw = r.read().decode()
                    return r.status, (json.loads(raw) if raw else {})
            except urllib.error.HTTPError as e:
                raw = e.read().decode()
                try:
                    raw = json.loads(raw)
                except Exception:
                    pass
                return e.code, raw
            except (urllib.error.URLError, OSError) as e:
                # transient (connection reset, timeout, proxy hiccup) -> backoff + retry
                last = e
                time.sleep(1.0 * (attempt + 1))
        raise last

    def _req(self, method, path, body=None, params=None):
        if not self.access_token:
            self.authenticate()
        url = self.instance_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Authorization": "Bearer " + self.access_token,
                   "Content-Type": "application/json"}
        data = json.dumps(body).encode() if body is not None else None
        status, resp = self._raw(method, url, data=data, headers=headers)
        if status == 401 and self._cli_alias is not None:
            # token expired on a long run -> re-auth via the CLI and retry once
            self._cli_auth()
            headers["Authorization"] = "Bearer " + self.access_token
            status, resp = self._raw(method, url, data=data, headers=headers)
        if status >= 400:
            raise SalesforceError(status, resp)
        return resp

    def _data(self, path):
        return "/services/data/%s%s" % (self.api, path)

    # -- API surface -------------------------------------------------------
    def query(self, soql):
        return self._req("GET", self._data("/query"), params={"q": soql})

    def query_all(self, soql):
        """Query and follow pagination, returning all records."""
        out = []
        res = self.query(soql)
        out.extend(res.get("records", []))
        while not res.get("done", True) and res.get("nextRecordsUrl"):
            res = self._req("GET", res["nextRecordsUrl"])
            out.extend(res.get("records", []))
        return out

    def describe_global(self):
        return self._req("GET", self._data("/sobjects/"))

    def describe(self, sobject):
        return self._req("GET", self._data("/sobjects/%s/describe" % sobject))

    def get(self, sobject, rid, fields=None):
        params = {"fields": ",".join(fields)} if fields else None
        return self._req("GET", self._data("/sobjects/%s/%s" % (sobject, rid)), params=params)

    def create(self, sobject, data):
        return self._req("POST", self._data("/sobjects/%s" % sobject), body=data)

    def update(self, sobject, rid, data):
        self._req("PATCH", self._data("/sobjects/%s/%s" % (sobject, rid)), body=data)
        return {"id": rid, "success": True}

    def upsert(self, sobject, ext_field, ext_value, data):
        return self._req("PATCH",
                         self._data("/sobjects/%s/%s/%s" % (sobject, ext_field, ext_value)),
                         body=data)

    def delete(self, sobject, rid):
        self._req("DELETE", self._data("/sobjects/%s/%s" % (sobject, rid)))
        return {"id": rid, "success": True}
