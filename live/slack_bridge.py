#!/usr/bin/env python3
"""
slack_bridge.py - receive REAL Slack interactions and drive recipes live, so the
interaction-only ("red") ops work end-to-end.

The local sandbox normally fabricates triggers, so block_kit_modals / dialogs have
no valid trigger_id. This bridge fixes that: it is a tiny public webhook (exposed
via a tunnel) that Slack calls when you run a slash command or click a button. It
extracts the REAL trigger_id / response_url / channel from Slack's payload, builds
the recipe's trigger event from it, and runs the recipe with the live dispatch -
so block_kit_modals opens an actual modal in Slack.

Flow:
  Slack  --(slash command / interaction)-->  tunnel  -->  this server
  server: verify signature -> pick recipe -> build trigger {context:{trigger_id..}}
          -> run recipe live (thread) -> ack 200 within Slack's 3s window
  recipe: block_kit_modals reads context.trigger_id -> views.open(real id) -> modal

Setup (see print_setup()):  python3 test_sandbox/live/slack_bridge.py --setup

Run:    python3 test_sandbox/live/slack_bridge.py --port 3000
        (then point a tunnel at :3000 and set the Slack app Request URLs to it)
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.engine import interpreter, loader            # noqa: E402
from test_sandbox.engine.context import RunContext             # noqa: E402
from test_sandbox.salesforce_live import SalesforceClient      # noqa: E402
from test_sandbox.jira_live import JiraClient                  # noqa: E402
from test_sandbox.slack_live import SlackClient, load_slack_env  # noqa: E402
from test_sandbox.live import salesforce as live               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RECIPES = os.path.join(os.path.dirname(HERE), "recipes_clean")


def build_command_map():
    """Map (domain, name) -> recipe id for every slack_bot::bot_command_v2 recipe,
    so an incoming '/domain name ...' picks the right recipe to run."""
    import glob
    cmd = {}
    for f in glob.glob(os.path.join(RECIPES, "*.json")):
        rid = os.path.basename(f)[:-5]
        try:
            r = json.load(open(f)).get("recipe")
        except Exception:
            continue
        if not r:
            continue
        t = loader.get_trigger(r) or {}
        if t.get("provider") == "slack_bot" and t.get("name") == "bot_command_v2":
            ci = t.get("input") or {}
            key = ((ci.get("domain") or "").lower(), (ci.get("name") or "").lower())
            cmd.setdefault(key, rid)
    return cmd


def _sign_ok(secret, ts, body, sig):
    if not secret or not ts or not sig:
        return False
    if abs(time.time() - int(ts)) > 60 * 5:        # replay window
        return False
    base = ("v0:%s:%s" % (ts, body)).encode()
    mine = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mine, sig)


def _build_trigger(recipe, ctx_fields, parameters):
    """Trigger event a bot_command recipe reads: real trigger_id under context.*,
    plus any collected parameters."""
    return {"context": ctx_fields, "parameters": parameters or {},
            "user_id": ctx_fields.get("user_id"), "channel": ctx_fields.get("channel_id"),
            **(parameters or {})}


class Clients:
    def __init__(self, org):
        self.sf = SalesforceClient.from_cli(org)
        self.jira = JiraClient.from_env()
        self.slack = SlackClient.from_env()
        self.dispatch = live.make_dispatch(self.sf, jira_client=self.jira,
                                            slack_client=self.slack)


def run_recipe_async(recipe_id, recipe, trigger, clients):
    def _go():
        try:
            # stash the real trigger_id so block_kit_modals can use it even when
            # the recipe step doesn't explicitly reference context.trigger_id
            clients.slack.pending_trigger_id = (trigger.get("context") or {}).get("trigger_id")
            ctx = RunContext(fixtures={"trigger": trigger, "config": {}, "reads": {}})
            res = interpreter.run(recipe, ctx, dispatch=clients.dispatch)
            print("  [recipe %s] %s | side-effects=%d" % (
                recipe_id, res["status"], len(res["side_effects"])))
        except Exception as e:
            print("  [recipe %s] ERROR %r" % (recipe_id, e))
    threading.Thread(target=_go, daemon=True).start()


def make_handler(secret, cmd_map, clients):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _read(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n).decode()

        def _ack(self, text=""):
            self.send_response(200)
            if text:
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"response_type": "ephemeral", "text": text}).encode())
            else:
                # empty 200 -> Slack shows nothing (modal arrives via views.open)
                self.send_header("Content-Length", "0")
                self.end_headers()

        def _verify(self, body):
            return _sign_ok(secret, self.headers.get("X-Slack-Request-Timestamp"),
                            body, self.headers.get("X-Slack-Signature"))

        def do_POST(self):
            body = self._read()
            if not self._verify(body):
                self.send_response(401); self.end_headers(); return

            if self.path.rstrip("/").endswith("/command"):
                form = {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}
                domain = (form.get("command") or "").lstrip("/").lower()
                text = (form.get("text") or "").strip()
                name = text.split(" ")[0].lower() if text else ""
                rid = cmd_map.get((domain, name)) or cmd_map.get((domain, ""))
                if not rid:
                    self._ack("No sandbox recipe mapped to /%s %s" % (domain, name)); return
                recipe = json.load(open(os.path.join(RECIPES, "%s.json" % rid)))["recipe"]
                trig = _build_trigger(recipe, {
                    "trigger_id": form.get("trigger_id"),
                    "channel_id": form.get("channel_id"),
                    "user_id": form.get("user_id"),
                    "response_url": form.get("response_url")}, {})
                print("/%s %s -> recipe %s (trigger_id=%s)" % (
                    domain, name, rid, (form.get("trigger_id") or "")[:20]))
                run_recipe_async(rid, recipe, trig, clients)
                self._ack()                       # ack fast; modal opens via views.open
                return

            if self.path.rstrip("/").endswith("/interact"):
                form = {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}
                payload = json.loads(form.get("payload") or "{}")
                # view_submission carries the collected parameter values
                tid = payload.get("trigger_id")
                print("interaction type=%s trigger_id=%s" % (
                    payload.get("type"), (tid or "")[:20]))
                # (mapping a submission back to its recipe is recipe-specific;
                #  v1 just acks so the modal closes cleanly)
                self._ack()
                return

            self.send_response(404); self.end_headers()

    return H


def print_setup():
    print("""\
SLACK BRIDGE SETUP
==================
1) Install a tunnel (pick one):
     brew install ngrok           # then: ngrok config add-authtoken <token>
     brew install cloudflared
2) Start the bridge:
     python3 test_sandbox/live/slack_bridge.py --port 3000
3) Expose it:
     ngrok http 3000              # copy the https URL, e.g. https://abc123.ngrok.app
4) In your Slack app (api.slack.com/apps -> your app):
   - Slash Commands: create the command(s) your recipes use (domain = command name,
     e.g. /eventbot). Request URL = https://<tunnel>/slack/command
   - Interactivity & Shortcuts: ON. Request URL = https://<tunnel>/slack/interact
   - OAuth scopes: add 'commands'. Reinstall the app.
   - Basic Information -> Signing Secret: copy it.
5) Put the signing secret in test_sandbox/.env:
     SLACK_SIGNING_SECRET=<signing secret>
6) Reinstall app if prompted, then run the slash command in #sandbox.
   The recipe fires with a REAL trigger_id -> the modal opens in Slack.
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=3000)
    ap.add_argument("--org", default="my-dev-org")
    ap.add_argument("--setup", action="store_true", help="print setup instructions")
    args = ap.parse_args()
    if args.setup:
        print_setup(); return

    secret = load_slack_env().get("SLACK_SIGNING_SECRET") or \
        os.environ.get("SLACK_SIGNING_SECRET")
    if not secret:
        # load_slack_env only returns token keys; read the raw .env for the secret
        from test_sandbox.slack_live.client import ENV_PATH
        if os.path.exists(ENV_PATH):
            for line in open(ENV_PATH):
                if line.strip().startswith("SLACK_SIGNING_SECRET="):
                    secret = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not secret:
        raise SystemExit("set SLACK_SIGNING_SECRET in .env (run --setup for steps)")

    cmd_map = build_command_map()
    print("loaded %d bot-command recipes" % len(cmd_map))
    clients = Clients(args.org)
    print("live connectors ready (sf/jira/slack). listening on :%d" % args.port)
    print("routes: POST /slack/command  POST /slack/interact")
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(secret, cmd_map, clients))
    srv.serve_forever()


if __name__ == "__main__":
    main()
