# Recipe `110430106`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | QUERY |
| **SF operation(s)** | scheduled_sobject_soql_query |
| **Salesforce object(s)** | Period |
| **Triggered by** | `salesforce::scheduled_sobject_soql_query` (sf-trigger) |
| **Total steps** | 3 |

## Trigger input fields
| field | type |
|---|---|
| `Period` | ? |
| `first_Period_name` | string |
| `last_Period_name` | string |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `salesforce::scheduled_sobject_soql_query`
- #2 action `workato_variable::declare_variable`
- #3 action `snowflake::sync_objects_to_snowflake_v2`
