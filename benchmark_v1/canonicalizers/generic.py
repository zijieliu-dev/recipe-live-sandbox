"""generic canonicalizer + shared helpers."""
import re

# volatile input keys never compared
VOLATILE = {"uuid", "ts", "timestamp", "trigger_id", "view_id", "run_id",
            "job_id", "request_id", "idempotency_key", "nonce", "token"}

_FAMILIES = (
    # (regex on "provider::operation", family)
    (re.compile(r"slack(_bot)?::post_(bot_)?(message|reply).*"), "slack.post_message"),
    (re.compile(r"slack(_bot)?::message_action"), "slack.post_message"),
    (re.compile(r"slack(_bot)?::update_.*"), "slack.update_message"),
    (re.compile(r"slack(_bot)?::delete_message"), "slack.delete_message"),
    (re.compile(r"slack(_bot)?::block_kit_modals"), "slack.open_modal"),
    (re.compile(r"slack(_bot)?::upload_file"), "slack.upload_file"),
    (re.compile(r"jira(_service_desk)?::create_(issue|customer_request)"), "jira.create_issue"),
    (re.compile(r"jira(_service_desk)?::update_issue$"), "jira.update_issue"),
    (re.compile(r"jira(_service_desk)?::(create|update)_comment"), "jira.comment"),
    (re.compile(r"jira(_service_desk)?::(update_issue_status|transition_issue)"), "jira.transition"),
    (re.compile(r"jira(_service_desk)?::assign_issue"), "jira.assign"),
    (re.compile(r"google_sheets::(add_row|append).*"), "sheets.append_rows"),
    (re.compile(r"google_sheets::(update_row|update_cell|batch_update).*"), "sheets.update"),
    (re.compile(r"salesforce::.*create.*"), "salesforce.create"),
    (re.compile(r"salesforce::(update_sobject|composite_update_sobject|updated_custom_object)"),
     "salesforce.update"),
    (re.compile(r"salesforce::upsert_sobject"), "salesforce.upsert"),
    (re.compile(r"salesforce::delete_sobject"), "salesforce.delete"),
)


def family(provider, operation):
    key = "%s::%s" % (provider, operation)
    for rx, fam in _FAMILIES:
        if rx.fullmatch(key):
            return fam
    return key                          # long tail: the op IS its own family


def norm_text(v):
    """Whitespace-collapsed text for tolerant comparison."""
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def scrub(value, depth=0):
    """Drop volatile keys, normalize strings, sort nothing (json sort later)."""
    if depth > 6:
        return None
    if isinstance(value, dict):
        return {k: scrub(v, depth + 1) for k, v in sorted(value.items())
                if k not in VOLATILE}
    if isinstance(value, list):
        return [scrub(v, depth + 1) for v in value]
    if isinstance(value, str):
        return norm_text(value)
    return value


def canonicalize(effect):
    return {
        "provider": effect.get("provider"),
        "family": family(effect.get("provider"), effect.get("operation")),
        "object": effect.get("object"),
        "input": scrub(effect.get("input")),
    }


def canonical_reads(reads):
    """Dedup read calls to (provider, family, object) - the reads signature."""
    seen, out = set(), []
    for r in reads:
        sig = (r.get("provider"), family(r.get("provider"), r.get("operation")),
               r.get("object"))
        if sig not in seen:
            seen.add(sig)
            out.append({"provider": sig[0], "family": sig[1], "object": sig[2]})
    return out
