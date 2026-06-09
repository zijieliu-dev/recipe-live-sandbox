#!/usr/bin/env python3
"""
gen_comps.py - scaffold a comp folder for every provider in the manifest.

Hand-written runtime primitives are left untouched. Every other provider (the
external connectors) gets a thin folder whose handle() delegates to the shared
default (mock I/O: record the call, return fabricated output). This gives each
"fake comp" its own folder under comps/, as intended, without 300+ copies of
real logic - the behavior lives once in comps/_default.py.

Usage:
  python3 gen_comps.py --manifest test_sandbox/manifest.json --comps test_sandbox/comps
"""
import argparse
import json
import os

# providers with hand-written behavior - do not overwrite
HANDWRITTEN = {
    "workato_variable", "workato_db_table", "lookup_table", "workato_list",
    "workato_smart_list", "clock", "logger", "json_parser",
}

STUB = '''"""Auto-generated comp stub for {provider!r} (external connector).

Mock I/O: records the call as a side-effect and returns fabricated output.
Behavior lives in comps/_default.py; edit this file to give the connector
bespoke behavior.
"""
from .._default import default_handle as handle
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="test_sandbox/manifest.json")
    ap.add_argument("--comps", default="test_sandbox/comps")
    args = ap.parse_args()

    providers = json.load(open(args.manifest))["providers"]
    created = skipped = 0
    for provider in providers:
        if provider in HANDWRITTEN:
            continue
        if not provider.isidentifier():
            skipped += 1
            continue
        folder = os.path.join(args.comps, provider)
        init = os.path.join(folder, "__init__.py")
        if os.path.exists(init):
            skipped += 1
            continue
        os.makedirs(folder, exist_ok=True)
        with open(init, "w") as f:
            f.write(STUB.format(provider=provider))
        created += 1

    print("generated %d external comp folders (%d skipped/existing)" % (created, skipped))


if __name__ == "__main__":
    main()
