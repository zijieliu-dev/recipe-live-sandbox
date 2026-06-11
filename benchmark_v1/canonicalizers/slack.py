"""Slack canonicalizer: channel + plain text extracted from the Workato block
DSL (or native Block Kit) + button titles/params. Volatile ts/uuid dropped."""
import json

from . import generic


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


def _blocks_text(blocks):
    """Concatenate visible text from Workato-DSL or Block Kit blocks."""
    parts = []

    def grab(d):
        if isinstance(d, dict):
            for k in ("section_text", "text", "title", "value", "alt_text",
                      "label_text", "placeholder_text", "modal_title"):
                v = d.get(k)
                if isinstance(v, str) and v.strip():
                    parts.append(v.strip())
            for v in d.values():
                grab(v)
        elif isinstance(d, list):
            for v in d:
                grab(v)
    grab(blocks)
    return generic.norm_text(" \n ".join(parts))


def _buttons(blocks):
    """Button titles + the param payloads behind them (both DSL dialects)."""
    titles, params = [], []

    def grab(d):
        if isinstance(d, dict):
            if d.get("type") == "button":                    # native Block Kit
                t = (d.get("text") or {}).get("text") if isinstance(d.get("text"), dict) else d.get("text")
                if t:
                    titles.append(generic.norm_text(t))
                if d.get("value"):
                    params.append(generic.norm_text(d["value"]))
            for k, v in d.items():
                if "button" in str(k).lower() and isinstance(v, str) and v.strip():
                    if "text" in k or "title" in k or "label" in k:
                        titles.append(generic.norm_text(v))
                    else:
                        params.append(generic.norm_text(v))
                grab(v)
        elif isinstance(d, list):
            for v in d:
                grab(v)
    grab(blocks)
    return titles, params


def canonicalize(effect):
    inp = effect.get("input") or {}
    if not isinstance(inp, dict):
        inp = {}
    blocks = (_as_list(inp.get("blocks")) or _as_list(inp.get("message_json"))
              or _as_list(inp.get("blocks_to_update")) or inp.get("view") or [])
    text_parts = [generic.norm_text(inp.get(k)) for k in
                  ("text", "message", "message_text", "fallback_text") if inp.get(k)]
    btext = _blocks_text(blocks)
    if btext:
        text_parts.append(btext)
    titles, params = _buttons(blocks)
    out = {
        "provider": effect.get("provider"),
        "family": generic.family(effect.get("provider"), effect.get("operation")),
        "channel": generic.norm_text(inp.get("channel") or inp.get("channel_id")) or None,
        "text": generic.norm_text(" \n ".join(p for p in text_parts if p)),
        "button_titles": titles,
        "button_params": params,
    }
    if effect.get("operation") == "block_kit_modals":
        view = inp.get("view") if isinstance(inp.get("view"), dict) else {}
        out["modal_title"] = generic.norm_text(view.get("modal_title")) or None
        out["modal_action"] = generic.norm_text(inp.get("modal_action_type")) or "open"
    if effect.get("operation") == "upload_file":
        out["file_name"] = generic.norm_text(inp.get("file_name") or inp.get("filename")) or None
    if inp.get("email"):
        out["email"] = generic.norm_text(inp.get("email"))
    return out
