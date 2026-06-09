# Recipe `123586145`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | HTTP |
| **SF operation(s)** | __adhoc_http_action |
| **Salesforce object(s)** | (soql) |
| **Triggered by** | `clock::scheduled_event` (scheduled) |
| **Total steps** | 6 |

## Trigger input fields
_No structured trigger input fields (event/scheduled/SF-triggered)._

## Branch conditions
- `#{_ref("workato_variable","b821d2dd",["l greater_than 0` — on non-trigger (SF/computed) data

## Workflow (step sequence)
- #1 trigger `clock::scheduled_event`
- #2 action `workato_variable::declare_variable`
- #3 action `salesforce::__adhoc_http_action`
- #4 action `workato_variable::declare_list`
- #5 if
- #6 action `snowflake::sync_objects_to_snowflake_v2`
