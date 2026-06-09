# Recipe `112244779`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | QUERY |
| **SF operation(s)** | search_sobjects_soql_v2 |
| **Salesforce object(s)** | (soql) |
| **Triggered by** | `byin_workato_recipe_ops_connector_3165546_1699532902::run_process_action_trigger` (byin) |
| **Total steps** | 3 |

## Trigger input fields
| field | type |
|---|---|
| `module_id` | string |
| `process_metadata.core_user_email` | string |
| `process_metadata.core_user_full_name` | string |
| `process_metadata.core_user_company_name` | string |
| `process_metadata.core_user_time_zone` | string |
| `process_metadata.core_parent_process_id` | string |
| `process_metadata.core_latest_run_id` | string |
| `process_metadata.opportunity_id` | string |
| `process_id` | string |
| `agent_id` | string |
| `agent_name` | string |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `byin_workato_recipe_ops_connector_3165546_1699532902::run_process_action_trigger`
- #2 action `salesforce::search_sobjects_soql_v2`
- #3 action `byin_workato_recipe_ops_connector_3165546_1699532902::complete_run_process_action`
