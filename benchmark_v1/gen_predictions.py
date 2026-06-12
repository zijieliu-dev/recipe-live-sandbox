#!/usr/bin/env python3
"""
gen_predictions.py - generate model predictions for the sandbox track.

Reads prompts/<task_id>.txt, calls the Claude API per task, and writes
results/<name>.predictions.jsonl rows {"task_id": ..., "output": <raw text>}
ready for score_predictions.py.

Requires ANTHROPIC_API_KEY (env or ../.env) and the `anthropic` package
(e.g. /tmp/nlenv/bin/python).

  /tmp/nlenv/bin/python gen_predictions.py --limit 10 --name opus_pilot
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks", "main_1k.jsonl")
PROMPTS = os.path.join(HERE, "prompts")
RESULTS = os.path.join(HERE, "results")

DEFAULT_MODEL = "claude-opus-4-8"


def load_env_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = os.path.join(HERE, "..", ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip("'\"")
                return


def task_ids(limit, offset):
    ids = []
    with open(TASKS) as f:
        for line in f:
            ids.append(json.loads(line)["task_id"])
    return ids[offset:offset + limit if limit else None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="pilot")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=16000)
    args = ap.parse_args()

    load_env_key()
    import anthropic
    client = anthropic.Anthropic()

    os.makedirs(RESULTS, exist_ok=True)
    out_path = os.path.join(RESULTS, f"{args.name}.predictions.jsonl")
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            done.add(json.loads(line)["task_id"])

    ids = task_ids(args.limit, args.offset)
    with open(out_path, "a") as out:
        for i, tid in enumerate(ids):
            if tid in done:
                print(f"[{i+1}/{len(ids)}] {tid} already done, skipping")
                continue
            prompt = open(os.path.join(PROMPTS, f"{tid}.txt")).read()
            try:
                with client.messages.stream(
                    model=args.model,
                    max_tokens=args.max_tokens,
                    thinking={"type": "adaptive"},
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    msg = stream.get_final_message()
                text = "".join(b.text for b in msg.content if b.type == "text")
                usage = f"in={msg.usage.input_tokens} out={msg.usage.output_tokens}"
            except anthropic.APIError as e:
                print(f"[{i+1}/{len(ids)}] {tid} API error: {e}", file=sys.stderr)
                continue
            out.write(json.dumps({"task_id": tid, "output": text}) + "\n")
            out.flush()
            print(f"[{i+1}/{len(ids)}] {tid} ok ({usage})")

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
