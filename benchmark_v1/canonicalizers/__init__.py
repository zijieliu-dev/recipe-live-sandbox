"""canonicalizers - one per primary app, plus a generic fallback.

canonicalize_effect(effect) turns a raw write effect
    {provider, operation, object, input}
into a canonical, comparable dict. Canonical effects never contain volatile
data (timestamps, uuids, run ids) and collapse op-name variants into an
op FAMILY (post_bot_message / post_message_to_channel -> slack.post_message),
so two recipes that produce the same real-world write compare equal.
"""
from . import slack, jira, sheets, salesforce, generic

_BY_PROVIDER = {
    "slack": slack, "slack_bot": slack,
    "jira": jira, "jira_service_desk": jira,
    "google_sheets": sheets,
    "salesforce": salesforce,
}


def canonicalize_effect(effect):
    mod = _BY_PROVIDER.get(effect.get("provider"), generic)
    out = mod.canonicalize(effect)
    out.setdefault("provider", effect.get("provider"))
    out.setdefault("family", generic.family(effect.get("provider"),
                                            effect.get("operation")))
    return out


def canonicalize_run(record):
    """RunRecord -> the gold/observed comparison payload."""
    return {
        "status": record["status"],
        "effects_canonical": [canonicalize_effect(e) for e in record["effects"]],
        "reads_canonical": generic.canonical_reads(record["reads"]),
        "state_diff": record["state_diff"],
        "control_trace": record["control_trace"],
    }
