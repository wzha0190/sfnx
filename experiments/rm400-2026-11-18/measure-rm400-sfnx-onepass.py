#!/usr/bin/env python3
"""2026-11-18: matched, authenticated hot one-pass test for RM400 sFNX.

The upstream API benchmarks split prompt reads from generation. This uses
its streamed chat response and usage/timings fields for the rack's combined
128-output-token, zero-reuse comparison.
"""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import random
import time
import urllib.request


MODEL = "qwen3.8-flash-next-huihui-v2-ud-q4-k-xl-v2"
WORDS = "server cache kernel tensor socket memory request decode prefill expert layer token batch lane queue".split()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("output", type=Path)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--config", type=Path, default=Path("/etc/sfnx/sfnx.json"))
    parser.add_argument("--engine", type=Path, default=Path("/srv/sfnx/bin/sfnx"))
    parser.add_argument("--seed", type=int, default=488400)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("invalid loopback port")
    if args.output.exists():
        parser.error("output already exists")

    env = Path("/etc/sfnx/environment").read_text().splitlines()
    key = next(line.partition("=")[2].strip().strip("\"'") for line in env if line.startswith("STRATA_API_KEY="))
    if not key:
        raise SystemExit("empty API key")
    base = f"http://127.0.0.1:{args.port}"

    def open_request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            base + path, data=data,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        return urllib.request.urlopen(request, timeout=120)

    def object_at(path):
        with open_request(path) as response:
            return json.load(response)

    def idle():
        live = object_at("/metrics")["live"]
        keys = ("running", "queued", "waiting", "admitting", "outside_slots")
        return live["state"] == "idle" and all(live.get(name) == 0 for name in keys)

    def run(case, words, seed):
        rnd = random.Random(seed)
        prompt = (f"Note {seed}.\n" + " ".join(rnd.choice(WORDS) for _ in range(words)) +
                  "\nWrite 256 numbered fictional place names, one per line.")
        payload = dict(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            max_tokens=128, temperature=0, reasoning_effort="none", seed=42,
            cache_prompt=False, stream=True,
            stream_options={"include_usage": True},
            chat_template_kwargs={"enable_thinking": False},
        )
        t0 = time.monotonic()
        first = usage = timing = None
        done = False
        text = hashlib.sha256()
        with open_request("/v1/chat/completions", payload) as response:
            for line in response:
                if not line.startswith(b"data:"):
                    continue
                body = line[5:].strip()
                if body == b"[DONE]":
                    done = True
                    break
                event = json.loads(body)
                if event.get("error"):
                    raise RuntimeError("error event from the measured server")
                for choice in event.get("choices", []):
                    value = choice.get("delta", {}).get("content")
                    if value:
                        if first is None:
                            first = time.monotonic() - t0
                        text.update(value.encode())
                if event.get("usage"):
                    usage = event["usage"]
                if event.get("timings"):
                    timing = event["timings"]
        if not done or first is None or usage is None or timing is None:
            raise RuntimeError(f"{case}: incomplete stream, usage, or timing")
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens", timing.get("cache_n"))
        if cached != 0 or usage["completion_tokens"] != 128:
            raise RuntimeError(f"{case}: expected zero reused tokens and 128 outputs")
        return dict(case=case, prompt_tokens=usage["prompt_tokens"], output_tokens=128, cached_tokens=cached,
                    ttft_s=round(first, 6), wall_s=round(time.monotonic() - t0, 6),
                    prefill_tok_s=timing["prompt_per_second"], decode_tok_s=timing["predicted_per_second"],
                    output_sha256=text.hexdigest())

    health = object_at("/health")
    if not health.get("loaded") or health.get("model") != MODEL or health.get("max_context") != 262144:
        raise SystemExit("expected the loaded RM400 model with native 262,144-token context")
    if not idle():
        raise SystemExit("sFNX is not idle")

    def digest(path):
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()

    report = dict(
        label=args.label, verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        model=MODEL, max_context=health["max_context"], seed=args.seed,
        engine_sha256=digest(args.engine), config_sha256=digest(args.config),
        warmup=[], measured=[],
    )
    shapes = (("512", 448, 512), ("4K", 3800, 4096), ("16K", 15300, 16384))
    for pass_n, phase in enumerate(("warmup", "measured")):
        for n, (case, words, target) in enumerate(shapes):
            row = run(case, words, args.seed + 10 * pass_n + n)
            if abs(row["prompt_tokens"] - target) > target * 0.03:
                raise RuntimeError(f"{case}: measured prompt outside 3% of target")
            report[phase].append(row)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(phase, json.dumps(row), flush=True)
    if not idle():
        raise SystemExit("post-benchmark sFNX metrics are not idle; results need review")


if __name__ == "__main__":
    main()
