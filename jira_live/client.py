"""
jira_live/client.py - a thin live Jira Cloud REST client (stdlib only).

No third-party deps (works behind Zscaler via SSL_CERT_FILE). Auth is Atlassian
basic auth: the account email + an API token
(https://id.atlassian.com/manage-profile/security/api-tokens), base64-encoded.

Credentials come from test_sandbox/.env (gitignored) or the environment:
  JIRA_BASE_URL   = https://your-domain.atlassian.net
  JIRA_EMAIL      = you@example.com
  JIRA_API_TOKEN  = <atlassian api token>

Covers the platform REST API (/rest/api/...) and the Service Management API
(/rest/servicedeskapi/...). Writes use API v2 so descriptions/comments can be
plain strings instead of ADF.
"""
import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(HERE), ".env")


class JiraError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__("JIRA %s: %s" % (status, body))


def load_jira_env(path=ENV_PATH):
    """Read JIRA_* from .env (env vars take precedence)."""
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return {k: env[k] for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
            if env.get(k)}


def _ssl_ctx():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


class JiraClient:
    def __init__(self, env=None):
        self.env = env if env is not None else load_jira_env()
        missing = [k for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
                   if not self.env.get(k)]
        if missing:
            raise JiraError(0, "missing %s in .env" % ", ".join(missing))
        self.base = self.env["JIRA_BASE_URL"].rstrip("/")
        token = "%s:%s" % (self.env["JIRA_EMAIL"], self.env["JIRA_API_TOKEN"])
        self.auth = "Basic " + base64.b64encode(token.encode()).decode()
        self.ctx = _ssl_ctx()

    @classmethod
    def from_env(cls):
        env = load_jira_env()
        if len(env) < 3:
            return None
        return cls(env)

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
                last = e
                time.sleep(1.0 * (attempt + 1))
        raise last

    def _req(self, method, path, body=None, params=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {"Authorization": self.auth,
                   "Content-Type": "application/json",
                   "Accept": "application/json"}
        data = json.dumps(body).encode() if body is not None else None
        status, resp = self._raw(method, url, data=data, headers=headers)
        if status >= 400:
            raise JiraError(status, resp)
        return resp

    # -- platform API ------------------------------------------------------
    def create_issue(self, fields):
        return self._req("POST", "/rest/api/2/issue", body={"fields": fields})

    def update_issue(self, key, fields):
        self._req("PUT", "/rest/api/2/issue/%s" % key, body={"fields": fields})
        return {"key": key, "success": True}

    def get_issue(self, key, fields=None):
        params = {"fields": fields} if fields else None
        return self._req("GET", "/rest/api/2/issue/%s" % key, params=params)

    def search_jql(self, jql, max_results=50):
        # /rest/api/2/search was removed (410); use the new search/jql endpoint.
        return self._req("POST", "/rest/api/3/search/jql",
                         body={"jql": jql, "maxResults": max_results,
                               "fields": ["summary", "status", "issuetype", "project"]})

    def find_user(self, query):
        return self._req("GET", "/rest/api/3/user/search", params={"query": query})

    def assign_issue(self, key, account_id):
        self._req("PUT", "/rest/api/2/issue/%s/assignee" % key,
                  body={"accountId": account_id})
        return {"key": key, "success": True}

    def create_comment(self, key, body):
        return self._req("POST", "/rest/api/2/issue/%s/comment" % key,
                         body={"body": body})

    def get_comments(self, key):
        return self._req("GET", "/rest/api/2/issue/%s/comment" % key)

    def transitions(self, key):
        return self._req("GET", "/rest/api/2/issue/%s/transitions" % key)

    def transition_issue(self, key, transition_id):
        self._req("POST", "/rest/api/2/issue/%s/transitions" % key,
                  body={"transition": {"id": str(transition_id)}})
        return {"key": key, "success": True}

    # -- service management API -------------------------------------------
    def sd_create_comment(self, issue, body, public=True):
        return self._req("POST", "/rest/servicedeskapi/request/%s/comment" % issue,
                         body={"body": body, "public": bool(public)})

    def sd_create_request(self, body):
        return self._req("POST", "/rest/servicedeskapi/request", body=body)
