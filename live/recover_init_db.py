#!/usr/bin/env python3
"""
recover_init_db.py - restore the org to the EXACT pinned init snapshot.

For each object in the snapshot: delete all current rows, then re-create them
from the saved field-sets. Field values match the init state exactly
(Salesforce assigns new ids, which can't be reused after a delete).

  python3 test_sandbox/live/recover_init_db.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.salesforce_live import SalesforceClient   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "init_snapshot.json")


def recover(client):
    snap = json.load(open(SNAP))
    for sob, payloads in snap.items():
        ids = [r["Id"] for r in client.query_all("SELECT Id FROM %s" % sob)]
        for rid in ids:
            client.delete(sob, rid)
        for p in payloads:
            client.create(sob, p)
        print("%-10s wiped %d, recreated %d from snapshot" % (sob, len(ids), len(payloads)))


def main():
    if not os.path.exists(SNAP):
        raise SystemExit("no snapshot at %s — run setup_init_db.py first" % SNAP)
    recover(SalesforceClient.from_cli("my-dev-org"))
    print("recovered to pinned init state.")


if __name__ == "__main__":
    main()
