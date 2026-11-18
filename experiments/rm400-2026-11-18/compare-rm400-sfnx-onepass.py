#!/usr/bin/env python3
"""2026-11-19: compare matched RM400 hot API passes."""

import argparse
import json
from math import isfinite
from pathlib import Path
from statistics import mean


CASES = ("512", "4K", "16K")
METRICS = {"decode_tok_s": 1, "prefill_tok_s": 1, "ttft_s": -1}


def positive_metrics(case, before, after, key):
    for value in (before[key], after[key]):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{case}: invalid {key}")


def compare(control, candidate, target, metric, threshold=3):
    for key in ("model", "max_context", "seed"):
        if control[key] != candidate[key]:
            raise ValueError(f"unmatched test metadata: {key}")
    for result in (control, candidate):
        for phase in ("warmup", "measured"):
            if tuple(row["case"] for row in result[phase]) != CASES:
                raise ValueError(f"{result['label']}: expected one complete {phase} pass")

    deltas = {}
    different = []
    for phase in ("warmup", "measured"):
        for base, trial in zip(control[phase], candidate[phase], strict=True):
            case = base["case"]
            if (base["prompt_tokens"] != trial["prompt_tokens"] or
                base["output_tokens"] != 128 or trial["output_tokens"] != 128 or
                base["cached_tokens"] != 0 or trial["cached_tokens"] != 0):
                raise ValueError(f"{phase}/{case}: unmatched token counts or cache reuse")
            if base["output_sha256"] != trial["output_sha256"]:
                different.append(f"{phase}/{case}")
            if phase == "measured":
                deltas[case] = {}
                for key, direction in METRICS.items():
                    positive_metrics(case, base, trial, key)
                    deltas[case][key] = 100 * direction * (trial[key] - base[key]) / base[key]
    regressions = [f"{case}/{key}" for case in CASES for key in METRICS if deltas[case][key] < 0]
    gain = deltas[target][metric]
    return {
        "target": f"{target}/{metric}",
        "measured_gain_percent": round(gain, 3),
        "required_gain_percent": threshold,
        "deltas_percent": {case: {key: round(v, 3) for key, v in row.items()} for case, row in deltas.items()},
        "regressions": regressions,
        "different_response_hashes": different,
        "performance_gate_pass": gain >= threshold and not regressions,
        "response_hash_gate_pass": not different,
        "full_acceptance": "not evaluated by this tool",
    }


def bracket(first, second):
    for key in ("engine_sha256", "model", "max_context", "seed"):
        if first[key] != second[key]:
            raise ValueError(f"bracket changes {key}")
    result = dict(first)
    for phase in ("warmup", "measured"):
        if any(tuple(row["case"] for row in data[phase]) != CASES for data in (first, second)):
            raise ValueError(f"bracket: incomplete {phase} pass")
        result[phase] = []
        for before, after in zip(first[phase], second[phase], strict=True):
            for key in ("prompt_tokens", "output_tokens", "cached_tokens", "output_sha256"):
                if before[key] != after[key]:
                    raise ValueError(f"bracket {phase}/{before['case']}: unmatched {key}")
            metrics = {}
            for key in METRICS:
                positive_metrics(f"bracket {phase}/{before['case']}", before, after, key)
                metrics[key] = mean((before[key], after[key]))
            result[phase].append(dict(before, **metrics))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--upstream-repeat", type=Path)
    parser.add_argument("--candidate-repeat", type=Path)
    parser.add_argument("--case", required=True, choices=CASES)
    parser.add_argument("--metric", required=True, choices=METRICS)
    args = parser.parse_args()
    upstream, candidate = (json.loads(p.read_text()) for p in (args.upstream, args.candidate))
    if bool(args.upstream_repeat) != bool(args.candidate_repeat):
        parser.error("supply both repeats for an ABBA bracket")
    if args.upstream_repeat:
        upstream = bracket(upstream, json.loads(args.upstream_repeat.read_text()))
        candidate = bracket(candidate, json.loads(args.candidate_repeat.read_text()))
    report = compare(upstream, candidate, args.case, args.metric)
    report["recorded_passes_per_profile"] = 2 if args.upstream_repeat else 1
    print(json.dumps(report, indent=2))
    return 0 if report["performance_gate_pass"] and report["response_hash_gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
