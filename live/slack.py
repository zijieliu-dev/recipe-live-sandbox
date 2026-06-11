"""
live/slack.py - a real-API Slack comp handler.

Maps Workato Slack operations (providers "slack_bot" and "slack") to live Web API
calls via SlackClient, returning data shaped like the mocked connector so
downstream datapills resolve unchanged.

Fire-and-forget ops (post message, lookup user, delete) call the real API. Ops
that require live interaction context the sandbox can't fabricate (a real
trigger_id for modals, a response_url for ephemeral replies) attempt the call
and degrade gracefully: Slack returns {"ok": false, ...}, which we record and
pass through rather than raising, so the recipe run continues.

Recipe `blocks` are stored in Workato's internal DSL (block_type:"section_with_text"
...), not Slack's Block Kit. _to_slack_blocks translates the common message block
types; anything unrecognized is dropped, and a plain-text fallback is always set so
the message still renders (and Slack has notification text).
"""
import json

_MRKDWN = 3000          # Slack's per-text-object character cap
# zero-width / directional marks that recipes use as spacers; not real content
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍‎‏﻿"), None)


def _as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else None
        except Exception:
            return None
    return None


def _clip(s, cap=_MRKDWN):
    """Trim, drop invisible spacer chars, and cap length. Invisible-only -> ''."""
    s = ("" if s is None else str(s)).translate(_INVISIBLE).strip()
    return s[:cap]


def _mrkdwn(s):
    return {"type": "mrkdwn", "text": _clip(s) or " "}


def _is_slack_native(blocks):
    return all(isinstance(b, dict) and "type" in b and "block_type" not in b
               for b in blocks)


def _to_slack_blocks(blocks):
    """Translate Workato block DSL -> Slack Block Kit (best-effort, common types)."""
    if not isinstance(blocks, list):
        return []
    if blocks and _is_slack_native(blocks):
        return blocks                          # already Slack format
    out = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        bt = b.get("block_type")
        if bt in ("section_with_text", "text_block", "section_with_button",
                  "section_with_button_with_long_action", "section_with_image",
                  "section_with_select_menu"):
            txt = b.get("section_text") or b.get("text")
            if _clip(txt):
                sec = {"type": "section", "text": _mrkdwn(txt)}
                if b.get("image_url"):
                    sec["accessory"] = {"type": "image", "image_url": b["image_url"],
                                        "alt_text": _clip(b.get("alt_text")) or "image"}
                out.append(sec)
        elif bt == "section_with_fields":
            fields = [{"type": "mrkdwn", "text": _clip(f) or " "}
                      for f in (b.get("fields") or b.get("elements") or [])][:10]
            sec = {"type": "section"}
            if _clip(b.get("section_text")):
                sec["text"] = _mrkdwn(b.get("section_text"))
            if fields:
                sec["fields"] = fields
            if sec.get("text") or sec.get("fields"):
                out.append(sec)
        elif bt == "fact_set":
            lines = []
            for f in (b.get("elements") or b.get("fields") or []):
                if isinstance(f, dict):
                    lines.append("*%s*: %s" % (f.get("title", ""), f.get("value", "")))
                else:
                    lines.append(str(f))
            if lines:
                out.append({"type": "section", "text": _mrkdwn("\n".join(lines))})
        elif bt == "divider":
            out.append({"type": "divider"})
        elif bt == "context":
            txt = b.get("section_text") or b.get("text")
            elems = b.get("elements")
            items = ([_mrkdwn(e if not isinstance(e, dict) else e.get("text"))
                      for e in elems] if isinstance(elems, list) and elems
                     else ([_mrkdwn(txt)] if _clip(txt) else []))
            if items:
                out.append({"type": "context", "elements": items[:10]})
        elif bt == "image" and b.get("image_url"):
            out.append({"type": "image", "image_url": b["image_url"],
                        "alt_text": _clip(b.get("alt_text")) or "image"})
        elif bt == "header":
            if _clip(b.get("section_text") or b.get("text")):
                out.append({"type": "header", "text": {"type": "plain_text",
                            "text": _clip(b.get("section_text") or b.get("text"), 150)}})
        # input/menu/actions blocks belong to modals, not messages -> skip
    return out[:50]                            # Slack caps a message at 50 blocks


def _options(b):
    """Slack option-objects from a Workato input block's options list."""
    out = []
    for o in (b.get("options") or []):
        if isinstance(o, dict):
            label = o.get("label") or o.get("text") or o.get("value") or "option"
            value = str(o.get("value") if o.get("value") is not None else label)
        else:
            label = value = str(o)
        out.append({"text": {"type": "plain_text", "text": _clip(label, 75) or "option"},
                    "value": _clip(value, 75) or "v"})
    return out[:100]


def _input_block(b):
    """Translate a Workato *_input modal block -> a Slack `input` block."""
    bt = b.get("block_type", "")
    aid = b.get("block_id") or "act"
    blk = {"type": "input", "block_id": b.get("block_id") or aid,
           "label": {"type": "plain_text", "text": _clip(b.get("label_text") or "Field", 2000) or "Field"},
           "optional": str(b.get("optional")).lower() == "true"}
    ph = b.get("placeholder_text")
    if bt in ("plain_text_input", "multiline_plain_text_input"):
        el = {"type": "plain_text_input", "action_id": aid}
        if bt.startswith("multiline"):
            el["multiline"] = True
        if ph:
            el["placeholder"] = {"type": "plain_text", "text": _clip(ph, 150)}
        blk["element"] = el
    elif bt in ("select_menu_input", "multi_select_menu_input"):
        opts = _options(b)
        if not opts:                       # a select with no options is invalid
            blk["element"] = {"type": "plain_text_input", "action_id": aid}
        else:
            blk["element"] = {"type": "static_select" if bt == "select_menu_input"
                              else "multi_static_select", "action_id": aid, "options": opts}
    elif bt == "datepicker_input":
        blk["element"] = {"type": "datepicker", "action_id": aid}
    elif bt in ("radio_buttons_input", "checkboxes_input"):
        opts = _options(b) or [{"text": {"type": "plain_text", "text": "Option 1"}, "value": "1"}]
        blk["element"] = {"type": "radio_buttons" if bt.startswith("radio") else "checkboxes",
                          "action_id": aid, "options": opts}
    else:
        return None
    return blk


def _to_slack_view(view):
    """Translate a Workato modal `view` -> a Slack Block Kit modal view object."""
    if not isinstance(view, dict):
        return None
    blocks, has_input = [], False
    for b in view.get("blocks", []):
        if not isinstance(b, dict) or not b:
            continue
        if b.get("block_type", "").endswith("_input"):
            ib = _input_block(b)
            if ib:
                blocks.append(ib); has_input = True
        else:
            blocks += _to_slack_blocks([b])
    if not blocks:
        blocks = [{"type": "section", "text": _mrkdwn(" ")}]
    out = {"type": "modal",
           "title": {"type": "plain_text", "text": _clip(view.get("modal_title") or "Form", 24) or "Form"},
           "blocks": blocks}
    sv = view.get("submit_view")
    if isinstance(sv, dict) or has_input:      # input blocks require a submit button
        sv = sv if isinstance(sv, dict) else {}
        out["submit"] = {"type": "plain_text", "text": _clip(sv.get("submit_text") or "Submit", 24) or "Submit"}
        out["close"] = {"type": "plain_text", "text": _clip(sv.get("close_text") or "Cancel", 24) or "Cancel"}
    return out


def _blocks_text(blocks):
    """Concatenate any text in the (Workato or Slack) blocks for a fallback string."""
    parts = []

    def grab(d):
        if isinstance(d, dict):
            for k in ("section_text", "text", "title", "value", "alt_text"):
                v = d.get(k)
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
            for v in d.values():
                grab(v)
        elif isinstance(d, list):
            for v in d:
                grab(v)
    grab(blocks)
    return _clip(" \n".join(parts)) if parts else ""


_COLORS = {"danger": "#e01e5a", "good": "#2eb67d", "warning": "#ecb22e"}


def _text(inp):
    """Best message text: explicit text, else a string `message`, else text from
    blocks ('' if none). A dict `message` is an attachment, handled separately."""
    msg = inp.get("message") if isinstance(inp.get("message"), str) else None
    return (_clip(inp.get("text")) or _clip(msg)
            or _blocks_text(_as_list(inp.get("blocks"))) or "")


def _attachment(src):
    """Build one Slack attachment from a Workato attachment dict (message{} or
    the top-level title/color/attachment_text form)."""
    if not isinstance(src, dict):
        return None
    a = {}
    if src.get("title"):
        a["title"] = _clip(src["title"], 1000)
    if src.get("title_link"):
        a["title_link"] = src["title_link"]
    if src.get("attachment_text") and _clip(src["attachment_text"]):
        a["text"] = _clip(src["attachment_text"])
    if src.get("color"):
        a["color"] = _COLORS.get(src["color"], src["color"])
    return a if (a.get("title") or a.get("text")) else None


def _attachments(inp):
    out = []
    for a in (_attachment(inp.get("message")), _attachment(inp)):
        if a:
            out.append(a)
    return out


def make_handler(client):
    override = getattr(client, "channel_override", None)

    def _chan(requested):
        """Redirect to the override channel if one is configured, else as-is."""
        return override or requested

    def post_message(inp):
        text = _text(inp)
        blocks = _to_slack_blocks(_as_list(inp.get("blocks")))
        attachments = _attachments(inp)
        if not text and not blocks and not attachments:
            # nothing real to say (e.g. datapills resolved empty) -> don't post a blank
            return {"ok": False, "error": "empty_message_skipped"}
        payload = {"channel": _chan(inp.get("channel")), "text": text or " "}
        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments
        if inp.get("thread_ts"):
            payload["thread_ts"] = inp["thread_ts"]
        return client.call("chat.postMessage", payload)

    def _usable(v):
        return isinstance(v, str) and v.strip()

    def _seed_message(channel):
        """Post a real message (to the override or requested channel) and return
        (channel_id, ts). Lets delete/update ops act on a message that truly
        exists, instead of failing on a ts fabricated from an empty trigger."""
        ch = _chan(channel)
        if not ch:
            return None, None
        res = client.call("chat.postMessage",
                          {"channel": ch, "text": "Sandbox live test message (seed)"})
        if res.get("ok"):
            return res.get("channel") or ch, res.get("ts")
        return None, None

    def handle(provider, operation, inp, ctx):
        if not isinstance(inp, dict):
            inp = {}

        if operation in ("post_bot_message", "post_message_to_channel"):
            res = post_message(inp)
            ctx.log_side_effect(provider, operation, channel=_chan(inp.get("channel")),
                                requested=inp.get("channel"), ok=res.get("ok"), ts=res.get("ts"))
            return res

        if operation in ("post_bot_reply_v2", "message_action"):
            # real reply needs a response_url/channel from the live interaction;
            # post if we have a channel (or an override), else record and skip.
            if _chan(inp.get("channel")):
                res = post_message(inp)
            else:
                res = {"ok": False, "error": "no_channel_in_sandbox"}
            ctx.log_side_effect(provider, operation, channel=_chan(inp.get("channel")),
                                ok=res.get("ok"))
            return res

        if operation == "get_user_by_email":
            res = client.call("users.lookupByEmail", {"email": inp.get("email")},
                              http_get=True)
            user = res.get("user") if isinstance(res, dict) else None
            user = user or {}
            return dict(user, ok=res.get("ok"), user=user)

        if operation == "delete_message":
            ch, ts = _chan(inp.get("channel")), inp.get("ts")
            res = client.call("chat.delete", {"channel": ch, "ts": ts}) \
                if (ch and _usable(ts)) else {"ok": False}
            if not res.get("ok"):       # ts empty/fabricated -> seed a real message, delete it
                ch, ts = _seed_message(inp.get("channel"))
                if ts:
                    res = client.call("chat.delete", {"channel": ch, "ts": ts})
            ctx.log_side_effect(provider, operation, channel=ch, ts=ts, ok=res.get("ok"))
            return res

        if operation == "update_blocks_by_block_id":
            blocks = _to_slack_blocks(_as_list(inp.get("blocks_to_update")) or
                                      _as_list(inp.get("message_json")))
            ch, ts = _chan(inp.get("channel")), inp.get("ts")
            payload = {"channel": ch, "ts": ts}
            if blocks:
                payload["blocks"] = blocks
            else:
                payload["text"] = _text(inp) or "Sandbox live test update"
            res = client.call("chat.update", payload) if (ch and _usable(ts)) else {"ok": False}
            if not res.get("ok"):       # ts empty/fabricated -> seed a real message, update it
                ch, ts = _seed_message(inp.get("channel"))
                if ts:
                    payload["channel"], payload["ts"] = ch, ts
                    res = client.call("chat.update", payload)
            ctx.log_side_effect(provider, operation, channel=ch, ts=ts, ok=res.get("ok"))
            return res

        if operation == "block_kit_modals":
            # views.open/update/push all require a real trigger_id, which only
            # exists during a live Slack interaction. Attempt, then degrade.
            action = (inp.get("modal_action_type") or "open").lower()
            method = {"open": "views.open", "update": "views.update",
                      "push": "views.push"}.get(action, "views.open")
            view = _to_slack_view(inp.get("view"))
            payload = {"view": view}
            # the recipe may not name trigger_id (Workato fills it implicitly);
            # the live bridge stashes the real one on the client as a fallback.
            tid = inp.get("trigger_id") or getattr(client, "pending_trigger_id", None)
            if tid:
                payload["trigger_id"] = tid
            if inp.get("view_id"):
                payload["view_id"] = inp["view_id"]
            res = client.call(method, payload) if (tid or inp.get("view_id")) \
                else {"ok": False, "error": "no_trigger_id_in_sandbox"}
            ctx.log_side_effect(provider, operation, action=action, ok=res.get("ok"),
                                trigger_id=bool(tid))
            return res

        if operation == "upload_file":
            # files.upload accepts a text/content body; binary upload needs the
            # newer external-upload flow, which we skip in the sandbox.
            content = inp.get("file")
            if isinstance(content, str):
                payload = {"channels": _chan(inp.get("channels")),
                           "filename": inp.get("filename"), "content": content}
                if inp.get("initial_comment"):
                    payload["initial_comment"] = inp["initial_comment"]
                if inp.get("thread_ts"):
                    payload["thread_ts"] = inp["thread_ts"]
                res = client.call("files.upload", payload)
            else:
                res = {"ok": False, "error": "binary_upload_unsupported_in_sandbox"}
            ctx.log_side_effect(provider, operation, ok=res.get("ok"))
            return res

        # generate_menu_options / dynamic_menu / triggers / unsupported -> empty
        return {}

    return handle
