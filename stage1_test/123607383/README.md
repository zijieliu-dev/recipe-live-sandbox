# Recipe `123607383` — UPDATE on Contract

**Mode:** WRITE (mutates org) | **SF operation(s):** update_sobject | **triggered by:** `workato_genie::start_workflow`

## How each run is reset (isolation)

A **persistent init database** lives in the org as the baseline (seeded once via `setup_init_db.py`): 10 Event rows + 10 Contract rows, alongside the existing Account/Contact/Opportunity data. **Every trial starts from this same init state.**

Each Salesforce write is recorded by a change-tracker; after the trial it is reversed so the init database is put back:

- a **deleted** init row → re-created from its snapshot (same data)
- an **updated** init row → its fields restored
- anything the recipe **created** → deleted

So the init table returns to its full row count and the next trial starts from the identical state.

## Input → Output, per sample (operates on the init table)

### Sample 1 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA2AAL", "Activated_By_ID": "005g5000006ezEDAAY", "Activated_Date": "2026-01-15T10:00:00Z", "Billing_City": "San Francisco", "Billing_Country": "US", "Billin…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000Wvq4JAAR` BEFORE:** `AccountId`="001g500000MKbA2AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000175"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0XAAU", `OwnerExpirationNotice`="15", `StartDate`="2026-01-15", `EndDate`="2026-02-14", `BillingStreet`="123 Market St", `BillingCity`="San Francisco", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 2 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA4AAL", "Activated_By_ID": "005g5000006f03pAAA", "Activated_Date": "2026-02-10T10:00:00Z", "Billing_City": "Austin", "Billing_Country": "US", "Billing_Geoco…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000WwKvOAAV` BEFORE:** `AccountId`="001g500000MKbA4AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000177"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0YAAU", `OwnerExpirationNotice`="30", `StartDate`="2026-02-10", `EndDate`="2026-04-09", `BillingStreet`="456 Oak Ave", `BillingCity`="Austin", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 3 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA6AAL", "Activated_By_ID": "005g5000006f03vAAA", "Activated_Date": "2026-03-05T10:00:00Z", "Billing_City": "Seattle", "Billing_Country": "US", "Billing_Geoc…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000Wx4F0AAJ` BEFORE:** `AccountId`="001g500000MKbA6AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000179"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0XAAU", `OwnerExpirationNotice`="45", `StartDate`="2026-03-05", `EndDate`="2026-06-04", `BillingStreet`="789 Pine Rd", `BillingCity`="Seattle", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 4 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA8AAL", "Activated_By_ID": "005g5000006qRIPAA2", "Activated_Date": "2026-04-20T10:00:00Z", "Billing_City": "New York", "Billing_Country": "US", "Billing_Geo…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000WxKxLAAV` BEFORE:** `AccountId`="001g500000MKbA8AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000181"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0YAAU", `OwnerExpirationNotice`="60", `StartDate`="2026-04-20", `EndDate`="2026-08-19", `BillingStreet`="321 Maple Dr", `BillingCity`="New York", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 5 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbABAA1", "Activated_By_ID": "005g5000006ezEDAAY", "Activated_Date": "2026-05-12T10:00:00Z", "Billing_City": "Chicago", "Billing_Country": "US", "Billing_Geoc…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000WxnnGAAR` BEFORE:** `AccountId`="001g500000MKbABAA1", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000184"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0XAAU", `OwnerExpirationNotice`="90", `StartDate`="2026-05-12", `EndDate`="2026-10-11", `BillingStreet`="654 Cedar Ln", `BillingCity`="Chicago", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 6 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA5AAL", "Activated_By_ID": "005g5000006f03pAAA", "Activated_Date": "2026-06-08T10:00:00Z", "Billing_City": "Boston", "Billing_Country": "US", "Billing_Geoco…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000Wxpx7AAB` BEFORE:** `AccountId`="001g500000MKbA5AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000178"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0YAAU", `OwnerExpirationNotice`="120", `StartDate`="2026-06-08", `EndDate`="2026-12-07", `BillingStreet`="987 Elm Blvd", `BillingCity`="Boston", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 7 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbAAAA1", "Activated_By_ID": "005g5000006f03vAAA", "Activated_Date": "2026-07-22T10:00:00Z", "Billing_City": "Denver", "Billing_Country": "US", "Billing_Geoco…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000Wy4b1AAB` BEFORE:** `AccountId`="001g500000MKbAAAA1", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000183"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0XAAU", `OwnerExpirationNotice`="15", `StartDate`="2026-07-22", `EndDate`="2027-02-21", `BillingStreet`="159 Spruce Way", `BillingCity`="Denver", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 8 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA3AAL", "Activated_By_ID": "005g5000006qRIPAA2", "Activated_Date": "2026-08-30T10:00:00Z", "Billing_City": "Atlanta", "Billing_Country": "US", "Billing_Geoc…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000WyLNJAA3` BEFORE:** `AccountId`="001g500000MKbA3AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000176"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0YAAU", `OwnerExpirationNotice`="30", `StartDate`="2026-08-30", `EndDate`="2027-04-29", `BillingStreet`="753 Birch Ct", `BillingCity`="Atlanta", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 9 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA7AAL", "Activated_By_ID": "005g5000006ezEDAAY", "Activated_Date": "2026-09-14T10:00:00Z", "Billing_City": "Miami", "Billing_Country": "US", "Billing_Geocod…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000WyLQYAA3` BEFORE:** `AccountId`="001g500000MKbA7AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000180"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0XAAU", `OwnerExpirationNotice`="45", `StartDate`="2026-09-14", `EndDate`="2027-06-13", `BillingStreet`="852 Willow Pl", `BillingCity`="Miami", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

### Sample 10 — `completed`
- **Input (trigger):** `{"parameters": {"Account_ID": "001g500000MKbA9AAL", "Activated_By_ID": "005g5000006f03pAAA", "Activated_Date": "2026-10-03T10:00:00Z", "Billing_City": "Portland", "Billing_Country": "US", "Billing_Geo…``
- **Init table:** `Contract` has **10 rows** (baseline)
- **Targeted row `800g500000WyLWzAAN` BEFORE:** `AccountId`="001g500000MKbA9AAL", `OwnerId`="005g5000006qRIPAA2", `Status`="Draft", `StatusCode`="Draft", `ContractNumber`="00000182"
- **AFTER recipe:** row **UPDATED** → `Pricebook2Id`="01sg5000003mE0YAAU", `OwnerExpirationNotice`="60", `StartDate`="2026-10-03", `EndDate`="2027-08-02", `BillingStreet`="426 Ash Ter", `BillingCity`="Portland", … (table still 10 rows)
- **Reset:** 5 write(s) reversed → init table restored to **10 rows**

