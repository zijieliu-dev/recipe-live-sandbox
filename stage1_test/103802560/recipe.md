# Recipe `103802560`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | SCHEMA |
| **SF operation(s)** | get_sobject_schema |
| **Salesforce object(s)** | Account |
| **Triggered by** | `slack_bot::bot_command_v2` (slack) |
| **Total steps** | 4 |

## Trigger input fields
| field | type |
|---|---|
| `context.channel` | ? |
| `parameters.call_id` | ? |
| `ts` | ? |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `slack_bot::bot_command_v2`
- #2 action `salesforce::get_sobject_schema`
- #3 action `byin_workato_recipe_ops_connector_3165546_1699532902::connection_required_acknowledge_process_event`
- #4 action `slack_bot::delete_message`
