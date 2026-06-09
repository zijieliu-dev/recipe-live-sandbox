# Recipe `93505634`

| | |
|---|---|
| **Mode** | WRITE (mutates org) |
| **SF function(s)** | DELETE |
| **SF operation(s)** | delete_sobject |
| **Salesforce object(s)** | Event |
| **Triggered by** | `workato_api_platform::receive_request` (api) |
| **Total steps** | 3 |

## Trigger input fields
| field | type |
|---|---|
| `request.Id` | ? |
| `context.calling_ip` | string |
| `context.access_profile.id` | integer |
| `context.access_profile.name` | string |
| `context.access_profile.type` | string |
| `context.client.id` | string |
| `context.client.name` | string |
| `context.jwt_payload.iat` | date_time |
| `context.jwt_payload.nbf` | date_time |
| `context.jwt_payload.exp` | date_time |
| `context.jwt_payload.aud` | string |
| `context.jwt_payload.jti` | string |
| `context.jwt_payload.iss` | string |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `workato_api_platform::receive_request`
- #2 action `salesforce::delete_sobject`
- #3 action `workato_api_platform::return_response`
