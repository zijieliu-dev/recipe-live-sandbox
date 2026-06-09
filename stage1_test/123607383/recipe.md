# Recipe `123607383`

| | |
|---|---|
| **Mode** | WRITE (mutates org) |
| **SF function(s)** | UPDATE |
| **SF operation(s)** | update_sobject |
| **Salesforce object(s)** | Contract |
| **Triggered by** | `workato_genie::start_workflow` (genie) |
| **Total steps** | 3 |

## Trigger input fields
| field | type |
|---|---|
| `parameters.Account_ID` | ? |
| `parameters.Activated_By_ID` | ? |
| `parameters.Activated_Date` | ? |
| `parameters.Billing_City` | ? |
| `parameters.Billing_Country` | ? |
| `parameters.Billing_Geocode_Accuracy` | ? |
| `parameters.Billing_Latitude` | ? |
| `parameters.Billing_Longitude` | ? |
| `parameters.Billing_State_or_Province` | ? |
| `parameters.Billing_Street` | ? |
| `parameters.Billing_Zip_or_Postal_Code` | ? |
| `parameters.Company_Signed_By_ID` | ? |
| `parameters.Company_Signed_Date` | ? |
| `parameters.Contract_ID` | ? |
| `parameters.Contract_Start_Date` | ? |
| `parameters.Contract_Term` | ? |
| `parameters.Customer_Signed_By_ID` | ? |
| `parameters.Customer_Signed_Date` | ? |
| `parameters.Customer_Signed_Title` | ? |
| `parameters.Description` | ? |
| `parameters.Owner_Expiration_Notice` | ? |
| `parameters.Owner_ID` | ? |
| `parameters.Price_Book_ID` | ? |
| `parameters.Special_Terms` | ? |
| `parameters.Status` | ? |
| `parameters.Owner_Experiation_Date` | date_time |
| `parameters.Amendment_Opportunity_Record_Type_Id` | string |
| `parameters.Amendment_Opportunity_Stage` | string |
| `parameters.Amendment_Owner` | string |
| `parameters.Amendment_Pricebook_Id` | string |
| `parameters.Amendment_and_Renewal_Behavior` | string |
| `parameters.Amendment_Start_Date` | date_time |
| `parameters.Default_Renewal_Contact_Roles` | boolean |
| `parameters.Default_Renewal_Partners` | boolean |
| `parameters.Disable_Amendment_Co_Term` | boolean |
| `parameters.MDQ_Renewal_Behavior` | string |
| `parameters.Master_Contract` | boolean |
| `parameters.Opportunity` | string |
| `parameters.Order` | string |
| `parameters.Preserve_Bundle_Structure` | boolean |
| `parameters.Quote` | string |
| `parameters.Renewal_Forecast` | boolean |
| `parameters.Renewal_Opportunity_Record_Type_Id` | string |
| `parameters.Renewal_Opportunity_Stage` | string |
| `parameters.Renewal_Opportunity` | string |
| `parameters.Renewal_Owner` | string |
| `parameters.Renewal_Pricebook_Id` | string |
| `parameters.Renewal_Quoted` | boolean |
| `parameters.Renewal_Term` | string |
| `parameters.Renewal_Uplift` | number |
| `parameters.Combine_Subscription_Quantities` | boolean |
| `parameters.Evergreen` | boolean |

## Branch conditions
_No if/elsif branches._

## Workflow (step sequence)
- #1 trigger `workato_genie::start_workflow`
- #2 action `salesforce::update_sobject`
- #3 action `workato_genie::workflow_return_result`
