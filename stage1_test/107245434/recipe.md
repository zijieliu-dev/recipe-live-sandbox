# Recipe `107245434`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | QUERY |
| **SF operation(s)** | search_sobjects_soql |
| **Salesforce object(s)** | Account |
| **Triggered by** | `slack_bot::dynamic_menu` (slack) |
| **Total steps** | 3 |

## Trigger input fields
| field | type |
|---|---|
| `typeahead.value` | ? |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `slack_bot::dynamic_menu`
- #2 action `salesforce::search_sobjects_soql`
- #3 action `slack_bot::generate_menu_options`
