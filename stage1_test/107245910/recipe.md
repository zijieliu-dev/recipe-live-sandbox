# Recipe `107245910`

| | |
|---|---|
| **Mode** | READ-only |
| **SF function(s)** | TRIGGER |
| **SF operation(s)** | new_custom_object |
| **Salesforce object(s)** | OpportunityFieldHistory |
| **Triggered by** | `salesforce::new_custom_object` (sf-trigger) |
| **Total steps** | 2 |

## Trigger input fields
| field | type |
|---|---|
| `CreatedDate` | ? |
| `Field` | ? |
| `Id` | ? |
| `IsDeleted` | ? |
| `NewValue` | ? |
| `OldValue` | ? |
| `OpportunityId` | ? |
| `CreatedById` | string |
| `DataType` | string |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `salesforce::new_custom_object`
- #2 action `workato_pub_sub::publish_to_topic`
