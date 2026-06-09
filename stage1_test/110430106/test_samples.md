# Test samples — recipe `110430106` (realized against live `my-dev-org`)

10 samples. Each trigger payload below is the **actual input fed to the recipe**, populated with real org data: real filter values fetched from the org, and real target ids from seeded records.

## Sample 1
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5RAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Year",
    "StartDate": "2025-01-01",
    "EndDate": "2025-12-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": false,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 1,
    "FullyQualifiedLabel": "FY 2025"
  }
}
```

## Sample 2
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5SAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Quarter",
    "StartDate": "2025-01-01",
    "EndDate": "2025-03-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": false,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 1,
    "FullyQualifiedLabel": "FQ1 FY 2025"
  }
}
```

## Sample 3
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5TAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Quarter",
    "StartDate": "2025-04-01",
    "EndDate": "2025-06-30",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": false,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 2,
    "FullyQualifiedLabel": "FQ2 FY 2025"
  }
}
```

## Sample 4
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5UAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Quarter",
    "StartDate": "2025-07-01",
    "EndDate": "2025-09-30",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": false,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 3,
    "FullyQualifiedLabel": "FQ3 FY 2025"
  }
}
```

## Sample 5
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5VAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Quarter",
    "StartDate": "2025-10-01",
    "EndDate": "2025-12-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": false,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 4,
    "FullyQualifiedLabel": "FQ4 FY 2025"
  }
}
```

## Sample 6
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5WAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Month",
    "StartDate": "2025-01-01",
    "EndDate": "2025-01-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": true,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 1,
    "FullyQualifiedLabel": "January FY 2025"
  }
}
```

## Sample 7
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5XAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Month",
    "StartDate": "2025-02-01",
    "EndDate": "2025-02-28",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": true,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 2,
    "FullyQualifiedLabel": "February FY 2025"
  }
}
```

## Sample 8
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5YAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Month",
    "StartDate": "2025-03-01",
    "EndDate": "2025-03-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": true,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 3,
    "FullyQualifiedLabel": "March FY 2025"
  }
}
```

## Sample 9
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5ZAAS",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Month",
    "StartDate": "2025-04-01",
    "EndDate": "2025-04-30",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": true,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 4,
    "FullyQualifiedLabel": "April FY 2025"
  }
}
```

## Sample 10
Realized from org:
- SF-triggered: real Period record
```json
{
  "trigger": {
    "Id": "026g5000001Mm5aAAC",
    "FiscalYearSettingsId": "022g5000001U2DVAA0",
    "Type": "Month",
    "StartDate": "2025-05-01",
    "EndDate": "2025-05-31",
    "SystemModstamp": "2026-06-03T23:45:22.000+0000",
    "IsForecastPeriod": true,
    "QuarterLabel": null,
    "PeriodLabel": null,
    "Number": 5,
    "FullyQualifiedLabel": "May FY 2025"
  }
}
```

