"""ops.py - classify connector operations (read / write / internal) and extract
the business object an operation targets.

The classification decides which sandbox calls become *effects* (writes, the
scored answer) vs *reads* (diagnostic). Explicit per-provider tables cover the
four primary apps (mirroring live/runner.py + the live mappers); a prefix
heuristic covers the long tail of mocked connectors.
"""

# providers whose calls count as EXTERNAL (effects/reads live here); everything
# routed to a real comps implementation (clock, json_parser, ...) is internal.
PRIMARY_PROVIDERS = {"salesforce", "jira", "jira_service_desk", "slack",
                     "slack_bot", "google_sheets"}

_SF_WRITES = {"create_sobject", "update_sobject", "upsert_sobject",
              "delete_sobject", "composite_update_sobject",
              "composite_create_sobject", "updated_custom_object",
              "create_custom_object", "__adhoc_http_action"}
_SF_READS = {"get_sobject_schema", "search_sobjects", "get_sobject_by_id",
             "get_sobject", "describe", "search_sobjects_es", "query"}

_SLACK_WRITES = {"post_bot_message", "post_message_to_channel", "post_message",
                 "post_bot_reply_v2", "post_reply", "message_action",
                 "delete_message", "update_blocks_by_block_id", "update_message",
                 "block_kit_modals", "upload_file", "add_reminder",
                 "invite_user_to_channel", "create_channel", "archive_channel",
                 "set_channel_topic", "add_pin", "add_reaction"}
_SLACK_READS = {"get_user_by_email", "get_user_by_id", "get_users",
                "get_channel", "list_channels", "get_message",
                "get_message_details", "search_messages", "dynamic_menu"}

_JIRA_WRITES = {"create_issue", "update_issue", "delete_issue", "create_comment",
                "update_comment", "assign_issue", "update_issue_status",
                "transition_issue", "add_attachment", "add_watcher",
                "create_customer_request", "link_issues", "add_worklog"}
_JIRA_READS = {"get_issue", "search_issues", "search_issues_by_JQL", "find_user",
               "get_issue_comments", "get_project", "list_projects",
               "get_transitions", "get_user"}

_SHEETS_WRITES = {"add_row", "add_row_v4", "add_rows_v4", "add_row_v4_bulk",
                  "update_row", "update_rows", "update_cell", "update_cells",
                  "clear_rows", "delete_row", "append_values", "batch_update"}
_SHEETS_READS = {"get_rows", "search_rows", "get_cell", "get_cells",
                 "read_values", "get_sheet", "list_sheets", "get_spreadsheet"}

_EXPLICIT = {
    "salesforce": (_SF_READS, _SF_WRITES),
    "jira": (_JIRA_READS, _JIRA_WRITES),
    "jira_service_desk": (_JIRA_READS, _JIRA_WRITES),
    "slack": (_SLACK_READS, _SLACK_WRITES),
    "slack_bot": (_SLACK_READS, _SLACK_WRITES),
    "google_sheets": (_SHEETS_READS, _SHEETS_WRITES),
}

_WRITE_PREFIXES = ("create", "update", "upsert", "delete", "post", "add", "send",
                   "upload", "insert", "remove", "archive", "invite", "assign",
                   "move", "set_", "transition", "push", "write", "append",
                   "publish", "schedule", "cancel", "submit", "complete",
                   "approve", "reject", "merge", "close", "reopen", "execute",
                   "run_", "trigger", "start", "stop_", "notify", "share",
                   "attach", "copy", "clone", "import", "sync", "revoke",
                   "activate", "deactivate", "enable", "disable", "register")
_READ_PREFIXES = ("get", "search", "list", "lookup", "find", "read", "download",
                  "describe", "fetch", "query", "retrieve", "check", "count",
                  "watch", "view", "export", "verify", "validate", "test",
                  "parse", "extract", "dynamic", "select")


def is_write(provider, operation):
    op = (operation or "").lower()
    tabs = _EXPLICIT.get(provider)
    if tabs:
        reads, writes = tabs
        if operation in writes:
            return True
        if operation in reads:
            return False
    if op.startswith(_READ_PREFIXES):
        return False
    if op.startswith(_WRITE_PREFIXES):
        return True
    # unknown verbs: treat as a write only when the name smells mutating
    return any(t in op for t in ("create", "update", "delete", "send", "post",
                                 "add_", "_add", "upload", "write"))


# input fields that name the business object / target of an operation, in
# priority order. Used both as the fixture-routing key and in canonical effects.
_OBJECT_FIELDS = ("sobject_name", "object", "object_type", "object_name",
                  "entity", "table", "table_name", "list_id",
                  "lookup_table_id", "table_id",
                  "project_issuetype", "project_key", "project",
                  "spreadsheet_id", "spreadsheet", "sheet_name", "sheet",
                  "channel", "channel_id", "form", "report_id", "board_id")


def object_of(inp):
    """Best-effort business-object key from a (resolved or raw) step input."""
    if not isinstance(inp, dict):
        return None
    for k in _OBJECT_FIELDS:
        v = inp.get(k)
        if isinstance(v, (str, int)) and str(v).strip():
            s = str(v).strip()
            # project_issuetype is "PROJ : Issue Type" -> keep the project key
            if k == "project_issuetype" and ":" in s:
                s = s.split(":")[0].strip()
            if "_ref(" in s or "#{" in s:
                continue                     # dynamic - not a stable key
            return s[:80]
    return None


def fixture_key(provider, operation, obj=None):
    base = "%s::%s" % (provider, operation)
    return "%s::%s" % (base, obj) if obj else base
