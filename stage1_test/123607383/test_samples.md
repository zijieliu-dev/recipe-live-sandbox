# Test samples — recipe `123607383` (realized against live `my-dev-org`)

10 samples. Each trigger payload below is the **actual input fed to the recipe**, populated with real org data: real filter values fetched from the org, and real target ids from seeded records.

## Sample 1
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA9AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006ezEDAAY'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-01-15T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'San Francisco'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'Address'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 1000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 1000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '94105'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'California'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '123 Market St'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-01-15'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006ezEDAAY'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 1
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-01-15'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKkAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Account Executive'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 1 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '15'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0XAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 1 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-01-15'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XDvOsAAL (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA9AAL",
      "Activated_By_ID": "005g5000006ezEDAAY",
      "Activated_Date": "2026-01-15T10:00:00Z",
      "Billing_City": "San Francisco",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "Address",
      "Billing_Latitude": 1000.0,
      "Billing_Longitude": 1000.0,
      "Billing_Zip_or_Postal_Code": "94105",
      "Billing_State_or_Province": "California",
      "Billing_Street": "123 Market St",
      "Company_Signed_Date": "2026-01-15",
      "Company_Signed_By_ID": "005g5000006ezEDAAY",
      "Contract_Term": 1,
      "Customer_Signed_Date": "2026-01-15",
      "Customer_Signed_By_ID": "003g500000G0AKkAAN",
      "Customer_Signed_Title": "Account Executive",
      "Description": "Sandbox test record 1 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "15",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0XAAU",
      "Special_Terms": "Sandbox test record 1 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-01-15",
      "Status": "Draft",
      "Contract_ID": "800g500000XDvOsAAL"
    }
  }
}
```

## Sample 2
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA3AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006f03pAAA'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-02-10T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Austin'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'NearAddress'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 2000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 2000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '78701'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Texas'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '456 Oak Ave'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-02-10'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006f03pAAA'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 2
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-02-10'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKlAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Sales Manager'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 2 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '30'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0YAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 2 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-02-10'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEPupAAH (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA3AAL",
      "Activated_By_ID": "005g5000006f03pAAA",
      "Activated_Date": "2026-02-10T10:00:00Z",
      "Billing_City": "Austin",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "NearAddress",
      "Billing_Latitude": 2000.0,
      "Billing_Longitude": 2000.0,
      "Billing_Zip_or_Postal_Code": "78701",
      "Billing_State_or_Province": "Texas",
      "Billing_Street": "456 Oak Ave",
      "Company_Signed_Date": "2026-02-10",
      "Company_Signed_By_ID": "005g5000006f03pAAA",
      "Contract_Term": 2,
      "Customer_Signed_Date": "2026-02-10",
      "Customer_Signed_By_ID": "003g500000G0AKlAAN",
      "Customer_Signed_Title": "Sales Manager",
      "Description": "Sandbox test record 2 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "30",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0YAAU",
      "Special_Terms": "Sandbox test record 2 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-02-10",
      "Status": "Draft",
      "Contract_ID": "800g500000XEPupAAH"
    }
  }
}
```

## Sample 3
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA2AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006f03vAAA'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-03-05T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Seattle'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'Block'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 3000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 3000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '98101'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Washington'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '789 Pine Rd'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-03-05'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006f03vAAA'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 3
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-03-05'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKmAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'VP of Sales'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 3 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '45'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0XAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 3 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-03-05'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEZJ4AAP (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA2AAL",
      "Activated_By_ID": "005g5000006f03vAAA",
      "Activated_Date": "2026-03-05T10:00:00Z",
      "Billing_City": "Seattle",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "Block",
      "Billing_Latitude": 3000.0,
      "Billing_Longitude": 3000.0,
      "Billing_Zip_or_Postal_Code": "98101",
      "Billing_State_or_Province": "Washington",
      "Billing_Street": "789 Pine Rd",
      "Company_Signed_Date": "2026-03-05",
      "Company_Signed_By_ID": "005g5000006f03vAAA",
      "Contract_Term": 3,
      "Customer_Signed_Date": "2026-03-05",
      "Customer_Signed_By_ID": "003g500000G0AKmAAN",
      "Customer_Signed_Title": "VP of Sales",
      "Description": "Sandbox test record 3 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "45",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0XAAU",
      "Special_Terms": "Sandbox test record 3 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-03-05",
      "Status": "Draft",
      "Contract_ID": "800g500000XEZJ4AAP"
    }
  }
}
```

## Sample 4
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA4AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006qRIPAA2'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-04-20T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'New York'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'Street'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 4000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 4000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '10001'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'New York'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '321 Maple Dr'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-04-20'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006qRIPAA2'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 4
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-04-20'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKnAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Director of Ops'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 4 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '60'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0YAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 4 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-04-20'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcVRAA1 (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA4AAL",
      "Activated_By_ID": "005g5000006qRIPAA2",
      "Activated_Date": "2026-04-20T10:00:00Z",
      "Billing_City": "New York",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "Street",
      "Billing_Latitude": 4000.0,
      "Billing_Longitude": 4000.0,
      "Billing_Zip_or_Postal_Code": "10001",
      "Billing_State_or_Province": "New York",
      "Billing_Street": "321 Maple Dr",
      "Company_Signed_Date": "2026-04-20",
      "Company_Signed_By_ID": "005g5000006qRIPAA2",
      "Contract_Term": 4,
      "Customer_Signed_Date": "2026-04-20",
      "Customer_Signed_By_ID": "003g500000G0AKnAAN",
      "Customer_Signed_Title": "Director of Ops",
      "Description": "Sandbox test record 4 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "60",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0YAAU",
      "Special_Terms": "Sandbox test record 4 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-04-20",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcVRAA1"
    }
  }
}
```

## Sample 5
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA5AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006ezEDAAY'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-05-12T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Chicago'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'ExtendedZip'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 5000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 5000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '60601'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Illinois'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '654 Cedar Ln'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-05-12'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006ezEDAAY'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 5
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-05-12'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKoAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'CEO'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 5 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '90'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0XAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 5 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-05-12'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcX3AAL (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA5AAL",
      "Activated_By_ID": "005g5000006ezEDAAY",
      "Activated_Date": "2026-05-12T10:00:00Z",
      "Billing_City": "Chicago",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "ExtendedZip",
      "Billing_Latitude": 5000.0,
      "Billing_Longitude": 5000.0,
      "Billing_Zip_or_Postal_Code": "60601",
      "Billing_State_or_Province": "Illinois",
      "Billing_Street": "654 Cedar Ln",
      "Company_Signed_Date": "2026-05-12",
      "Company_Signed_By_ID": "005g5000006ezEDAAY",
      "Contract_Term": 5,
      "Customer_Signed_Date": "2026-05-12",
      "Customer_Signed_By_ID": "003g500000G0AKoAAN",
      "Customer_Signed_Title": "CEO",
      "Description": "Sandbox test record 5 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "90",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0XAAU",
      "Special_Terms": "Sandbox test record 5 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-05-12",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcX3AAL"
    }
  }
}
```

## Sample 6
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbABAA1'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006f03pAAA'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-06-08T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Boston'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'Zip'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 6000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 6000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '02108'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Massachusetts'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '987 Elm Blvd'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-06-08'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006f03pAAA'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 6
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-06-08'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKpAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'CTO'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 6 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '120'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0YAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 6 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-06-08'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcX4AAL (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbABAA1",
      "Activated_By_ID": "005g5000006f03pAAA",
      "Activated_Date": "2026-06-08T10:00:00Z",
      "Billing_City": "Boston",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "Zip",
      "Billing_Latitude": 6000.0,
      "Billing_Longitude": 6000.0,
      "Billing_Zip_or_Postal_Code": "02108",
      "Billing_State_or_Province": "Massachusetts",
      "Billing_Street": "987 Elm Blvd",
      "Company_Signed_Date": "2026-06-08",
      "Company_Signed_By_ID": "005g5000006f03pAAA",
      "Contract_Term": 6,
      "Customer_Signed_Date": "2026-06-08",
      "Customer_Signed_By_ID": "003g500000G0AKpAAN",
      "Customer_Signed_Title": "CTO",
      "Description": "Sandbox test record 6 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "120",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0YAAU",
      "Special_Terms": "Sandbox test record 6 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-06-08",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcX4AAL"
    }
  }
}
```

## Sample 7
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA6AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006f03vAAA'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-07-22T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Denver'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'Neighborhood'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 7000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 7000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '80202'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Colorado'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '159 Spruce Way'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-07-22'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006f03vAAA'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 7
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-07-22'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKqAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Business Analyst'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 7 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '15'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0XAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 7 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-07-22'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcYfAAL (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA6AAL",
      "Activated_By_ID": "005g5000006f03vAAA",
      "Activated_Date": "2026-07-22T10:00:00Z",
      "Billing_City": "Denver",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "Neighborhood",
      "Billing_Latitude": 7000.0,
      "Billing_Longitude": 7000.0,
      "Billing_Zip_or_Postal_Code": "80202",
      "Billing_State_or_Province": "Colorado",
      "Billing_Street": "159 Spruce Way",
      "Company_Signed_Date": "2026-07-22",
      "Company_Signed_By_ID": "005g5000006f03vAAA",
      "Contract_Term": 7,
      "Customer_Signed_Date": "2026-07-22",
      "Customer_Signed_By_ID": "003g500000G0AKqAAN",
      "Customer_Signed_Title": "Business Analyst",
      "Description": "Sandbox test record 7 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "15",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0XAAU",
      "Special_Terms": "Sandbox test record 7 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-07-22",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcYfAAL"
    }
  }
}
```

## Sample 8
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA7AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006qRIPAA2'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-08-30T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Atlanta'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'City'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 8000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 8000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '30303'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Georgia'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '753 Birch Ct'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-08-30'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006qRIPAA2'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 8
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-08-30'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKrAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Consultant'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 8 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '30'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0YAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 8 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-08-30'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcaHAAT (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA7AAL",
      "Activated_By_ID": "005g5000006qRIPAA2",
      "Activated_Date": "2026-08-30T10:00:00Z",
      "Billing_City": "Atlanta",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "City",
      "Billing_Latitude": 8000.0,
      "Billing_Longitude": 8000.0,
      "Billing_Zip_or_Postal_Code": "30303",
      "Billing_State_or_Province": "Georgia",
      "Billing_Street": "753 Birch Ct",
      "Company_Signed_Date": "2026-08-30",
      "Company_Signed_By_ID": "005g5000006qRIPAA2",
      "Contract_Term": 8,
      "Customer_Signed_Date": "2026-08-30",
      "Customer_Signed_By_ID": "003g500000G0AKrAAN",
      "Customer_Signed_Title": "Consultant",
      "Description": "Sandbox test record 8 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "30",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0YAAU",
      "Special_Terms": "Sandbox test record 8 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-08-30",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcaHAAT"
    }
  }
}
```

## Sample 9
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbA8AAL'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006ezEDAAY'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-09-14T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Miami'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'County'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 9000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 9000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '33101'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Florida'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '852 Willow Pl'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-09-14'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006ezEDAAY'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 9
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-09-14'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKsAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Solutions Engineer'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 9 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '45'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0XAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 9 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-09-14'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcbtAAD (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbA8AAL",
      "Activated_By_ID": "005g5000006ezEDAAY",
      "Activated_Date": "2026-09-14T10:00:00Z",
      "Billing_City": "Miami",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "County",
      "Billing_Latitude": 9000.0,
      "Billing_Longitude": 9000.0,
      "Billing_Zip_or_Postal_Code": "33101",
      "Billing_State_or_Province": "Florida",
      "Billing_Street": "852 Willow Pl",
      "Company_Signed_Date": "2026-09-14",
      "Company_Signed_By_ID": "005g5000006ezEDAAY",
      "Contract_Term": 9,
      "Customer_Signed_Date": "2026-09-14",
      "Customer_Signed_By_ID": "003g500000G0AKsAAN",
      "Customer_Signed_Title": "Solutions Engineer",
      "Description": "Sandbox test record 9 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "45",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0XAAU",
      "Special_Terms": "Sandbox test record 9 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-09-14",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcbtAAD"
    }
  }
}
```

## Sample 10
Realized from org:
- real Contract.AccountId -> trigger.parameters.Account_ID = '001g500000MKbAAAA1'
- business Contract.ActivatedById -> trigger.parameters.Activated_By_ID = '005g5000006f03pAAA'
- business Contract.ActivatedDate -> trigger.parameters.Activated_Date = '2026-10-03T10:00:00Z'
- business Contract.BillingCity -> trigger.parameters.Billing_City = 'Portland'
- business Contract.BillingCountry -> trigger.parameters.Billing_Country = 'US'
- business Contract.BillingGeocodeAccuracy -> trigger.parameters.Billing_Geocode_Accuracy = 'State'
- business Contract.BillingLatitude -> trigger.parameters.Billing_Latitude = 10000.0
- business Contract.BillingLongitude -> trigger.parameters.Billing_Longitude = 10000.0
- business Contract.BillingPostalCode -> trigger.parameters.Billing_Zip_or_Postal_Code = '97201'
- business Contract.BillingState -> trigger.parameters.Billing_State_or_Province = 'Oregon'
- business Contract.BillingStreet -> trigger.parameters.Billing_Street = '426 Ash Ter'
- business Contract.CompanySignedDate -> trigger.parameters.Company_Signed_Date = '2026-10-03'
- business Contract.CompanySignedId -> trigger.parameters.Company_Signed_By_ID = '005g5000006f03pAAA'
- business Contract.ContractTerm -> trigger.parameters.Contract_Term = 10
- business Contract.CustomerSignedDate -> trigger.parameters.Customer_Signed_Date = '2026-10-03'
- business Contract.CustomerSignedId -> trigger.parameters.Customer_Signed_By_ID = '003g500000G0AKtAAN'
- business Contract.CustomerSignedTitle -> trigger.parameters.Customer_Signed_Title = 'Coordinator'
- business Contract.Description -> trigger.parameters.Description = 'Sandbox test record 10 — generated for automated recipe testing.'
- business Contract.OwnerExpirationNotice -> trigger.parameters.Owner_Expiration_Notice = '60'
- real Contract.OwnerId -> trigger.parameters.Owner_ID = '005g5000006qRIPAA2'
- business Contract.Pricebook2Id -> trigger.parameters.Price_Book_ID = '01sg5000003mE0YAAU'
- business Contract.SpecialTerms -> trigger.parameters.Special_Terms = 'Sandbox test record 10 — generated for automated recipe testing.'
- business Contract.StartDate -> trigger.parameters.Contract_Start_Date = '2026-10-03'
- real Contract.Status -> trigger.parameters.Status = 'Draft'
- target row from init table: Contract.parameters.Contract_ID = 800g500000XEcdVAAT (1 of 10 rows)
```json
{
  "trigger": {
    "parameters": {
      "Account_ID": "001g500000MKbAAAA1",
      "Activated_By_ID": "005g5000006f03pAAA",
      "Activated_Date": "2026-10-03T10:00:00Z",
      "Billing_City": "Portland",
      "Billing_Country": "US",
      "Billing_Geocode_Accuracy": "State",
      "Billing_Latitude": 10000.0,
      "Billing_Longitude": 10000.0,
      "Billing_Zip_or_Postal_Code": "97201",
      "Billing_State_or_Province": "Oregon",
      "Billing_Street": "426 Ash Ter",
      "Company_Signed_Date": "2026-10-03",
      "Company_Signed_By_ID": "005g5000006f03pAAA",
      "Contract_Term": 10,
      "Customer_Signed_Date": "2026-10-03",
      "Customer_Signed_By_ID": "003g500000G0AKtAAN",
      "Customer_Signed_Title": "Coordinator",
      "Description": "Sandbox test record 10 \u2014 generated for automated recipe testing.",
      "Owner_Expiration_Notice": "60",
      "Owner_ID": "005g5000006qRIPAA2",
      "Price_Book_ID": "01sg5000003mE0YAAU",
      "Special_Terms": "Sandbox test record 10 \u2014 generated for automated recipe testing.",
      "Contract_Start_Date": "2026-10-03",
      "Status": "Draft",
      "Contract_ID": "800g500000XEcdVAAT"
    }
  }
}
```

