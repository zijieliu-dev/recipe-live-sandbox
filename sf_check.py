#!/usr/bin/env python3
"""
sf_check.py - verify live Salesforce connectivity and summarize the org schema.

  python3 sf_check.py            # auth + count objects + list creatable standard objects
  python3 sf_check.py Account    # describe one object's fields

Reads credentials from test_sandbox/.env (see .env.example).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_sandbox.salesforce_live import SalesforceClient, SalesforceError  # noqa: E402


def main():
    org = os.environ.get("SF_ORG_ALIAS")          # default: CLI's default org
    try:
        sf = SalesforceClient.from_cli(org)
    except SalesforceError as e:
        print("AUTH FAILED:", e)
        print("Make sure the Salesforce CLI is authed (sf org list).")
        sys.exit(1)
    print("AUTH OK  instance=%s  api=%s" % (sf.instance_url, sf.api))

    if len(sys.argv) > 1:
        d = sf.describe(sys.argv[1])
        print("\n%s fields (createable):" % sys.argv[1])
        for f in d.get("fields", []):
            if f.get("createable"):
                req = "" if f.get("nillable", True) else "  *required"
                print("  %-30s %s%s" % (f["name"], f["type"], req))
        return

    g = sf.describe_global()
    sobs = g.get("sobjects", [])
    std = [s for s in sobs if not s["name"].endswith("__c") and s.get("createable") and not s.get("customSetting")]
    custom = [s for s in sobs if s["name"].endswith("__c")]
    print("total sobjects: %d  (standard creatable: %d, custom __c: %d)"
          % (len(sobs), len(std), len(custom)))
    print("\nkey standard objects present:")
    for name in ("Account", "Contact", "Lead", "Opportunity", "Case", "Task", "Campaign", "User"):
        present = any(s["name"] == name for s in sobs)
        print("  %-12s %s" % (name, "yes" if present else "NO"))
    if custom:
        print("\ncustom objects (%d):" % len(custom), [s["name"] for s in custom[:20]])


if __name__ == "__main__":
    main()
