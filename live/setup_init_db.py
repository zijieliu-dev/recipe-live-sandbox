#!/usr/bin/env python3
"""
setup_init_db.py - (re)define and PIN the init database snapshot. ONE job.

Wipes the write-target objects (Event, Contract), seeds a fresh fixed set of
rows, and SAVES their exact field-sets to init_snapshot.json. This DEFINES the
baseline (overwriting any previous snapshot). It does NOT restore later — use
recover_init_db.py to restore the org to this snapshot.

  python3 test_sandbox/live/setup_init_db.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_sandbox.salesforce_live import SalesforceClient        # noqa: E402
from test_sandbox.live.realize import seed_record                # noqa: E402
from test_sandbox.live.recover_init_db import SNAP               # noqa: E402

INIT = {"Event": 10, "Contract": 10}


def main():
    c = SalesforceClient.from_cli("my-dev-org")
    snap = {}
    for sob, n in INIT.items():
        ids = [r["Id"] for r in c.query_all("SELECT Id FROM %s" % sob)]   # wipe existing
        for rid in ids:
            c.delete(sob, rid)
        payloads = []
        for k in range(n):
            _, payload = seed_record(c, sob, i=k)        # create row, capture its exact field-set
            payloads.append(payload)
        snap[sob] = payloads
        print("%-10s wiped %d, seeded %d fresh rows" % (sob, len(ids), n))

    json.dump(snap, open(SNAP, "w"), indent=2, default=str)
    print("PINNED new init snapshot -> %s" % SNAP)


if __name__ == "__main__":
    main()
