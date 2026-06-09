"""
slack_live/client.py - a thin live Slack Web API client (stdlib only).

No third-party deps (works behind Zscaler via SSL_CERT_FILE). Auth is a bearer
token; a bot token (xoxb-...) covers the slack_bot operations our recipes use.

Credentials come from test_sandbox/.env (gitignored) or the environment:
  SLACK_BOT_TOKEN   = xoxb-...        (used for slack_bot + slack)
  SLACK_USER_TOKEN  = xoxp-...        (optional; legacy 'slack' provider if set)

call(method, payload) POSTs JSON to https://slack.com/api/<method> and returns
the parsed response. Slack signals failure with HTTP 200 + {"ok": false, ...};
we return that body as-is so the caller can record it (we don't raise on ok:false
so a single bad message doesn't abort the recipe run).
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(os.path.dirname(HERE), ".env")
API = "https://slack.com/api/"


class SlackError(Exception):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__("SLACK %s: %s" % (status, body))


def load_slack_env(path=ENV_PATH):
    """Read SLACK_* from .env (env vars take precedence)."""
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("SLACK_BOT_TOKEN", "SLACK_USER_TOKEN", "SLACK_CHANNEL_OVERRIDE"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return {k: env[k] for k in ("SLACK_BOT_TOKEN", "SLACK_USER_TOKEN",
                                "SLACK_CHANNEL_OVERRIDE") if env.get(k)}


def _ssl_ctx():
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


class SlackClient:
    def __init__(self, env=None):
        self.env = env if env is not None else load_slack_env()
        self.bot = self.env.get("SLACK_BOT_TOKEN")
        self.user = self.env.get("SLACK_USER_TOKEN")
        # optional: redirect every posted message to this channel/DM id so recipe
        # posts (which carry foreign channel ids) become visible in your workspace
        self.channel_override = self.env.get("SLACK_CHANNEL_OVERRIDE") or None
        if not (self.bot or self.user):
            raise SlackError(0, "missing SLACK_BOT_TOKEN in .env")
        self.ctx = _ssl_ctx()

    @classmethod
    def from_env(cls):
        env = load_slack_env()
        if not env:
            return None
        return cls(env)

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

    def call(self, method, payload=None, use_user_token=False, http_get=False):
        """POST (or GET) a Web API method. Returns the parsed JSON response."""
        token = (self.user if use_user_token and self.user else self.bot) or self.user
        headers = {"Authorization": "Bearer " + token}
        payload = payload or {}
        if http_get:
            url = API + method + "?" + urllib.parse.urlencode(payload)
            _, resp = self._raw("GET", url, headers=headers)
        else:
            headers["Content-Type"] = "application/json; charset=utf-8"
            url = API + method
            _, resp = self._raw("POST", url, data=json.dumps(payload).encode(), headers=headers)
        return resp if isinstance(resp, dict) else {"ok": False, "raw": resp}
