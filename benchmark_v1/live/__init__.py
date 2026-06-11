"""live - the live-write-verified track (hybrid: fixture reads + REAL writes).

The sandbox track (../) proves a candidate emits write CALLS equivalent to the
original's. This track proves the candidate produces equivalent REAL external
state: writes go to the actual Slack/Jira/Sheets/Salesforce test environment,
and the verdict comes from real API READ-BACK, not from connector return codes.

Track metric: pass@1_live_write_verified_strict  (reported separately from the
sandbox track's pass@1_execution_equivalent_strict).

Design (per the 2026-06 live-track design review):
  - reads stay fixture-backed (same world for original & candidate, no flake);
  - original and candidate run in EQUIVALENT BUT ISOLATED namespaces
    (Sheets: per-run tabs; Jira: bench project + marker labels; Slack: bench
    channel + text markers; SF: created-id registry) - never the same objects;
  - every write goes through an allowlist gateway and is logged (extra-write
    detection never relies on read-back alone);
  - canonicalization maps real ids back to logical resources / placeholders
    (<JIRA_ISSUE_KEY>, <TS>, ...) so original and candidate can compare equal;
  - gold = canonicalized live state diff of the ORIGINAL's run, via read-back;
  - cleanup is planned per run and reported as a metric, never silent.

Pipeline:  build_live_materialization -> run_original_live -> run_candidate_live
           -> score_predictions_live -> cleanup_live;  selfcheck_live validates
           the harness (original-as-candidate vs its own live gold).
"""
