# Recipe `110408597`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | QUERY |
| **SF operation(s)** | search_sobjects |
| **Salesforce object(s)** | User |
| **Triggered by** | `workato_recipe_function::execute` (recipe-fn) |
| **Total steps** | 3 |

## Trigger input fields
| field | type |
|---|---|
| `parameters.genie_id` | ? |
| `parameters.impact` | ? |
| `parameters.salesforce_object.id` | ? |
| `parameters.salesforce_object.name` | ? |
| `parameters.salesforce_object.owner_id` | ? |
| `parameters.validation` | ? |
| `parameters.validation_result` | ? |
| `parameters.genie_name` | string |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `workato_recipe_function::execute`
- #2 action `salesforce::search_sobjects`
- #3 action `byin_workato_recipe_ops_connector_3165546_1699532902::start_process`
