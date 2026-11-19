#!/usr/bin/env python3
"""2026-11-18: compare physical-card arrival in sFNX Flash-Next CUPTI traces.

Upstream kernel_groups.py splits windows on time gaps; back-to-back bench
windows have no reliable gap. Match ordered collective invocations instead.
Use on traces from the pinned three-card fnx_run bench, not the live server.
"""

import argparse
import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


def summarize(path, mapping, windows):
    calls = [[] for _ in mapping]
    count = [0] * len(mapping)
    open_trace = gzip.open if path.suffix == ".gz" else open
    with open_trace(path, "rt", encoding="utf-8", newline="") as trace:
        for d, start, end, graph_stream, name in list_rows(trace):
            if graph_stream.partition(":")[0] == "0":
                continue
            card = int(d)
            if "k_argmax_fin" in name:
                count[card] += 1
            kind = (
                "sum" if "k_ring<" in name else "attention-merge" if "k_att_merge" in name else None
            )
            if kind:
                calls[card].append((int(start), int(end), kind))
    if count != [windows] * len(mapping):
        raise ValueError(f"{path}: expected {windows} verification windows on each card; got {count}")
    for card in calls:
        card.sort()
    samples = {k: [] for k in ("expert", "layer-output", "attention-merge")}
    sums = merges = 0
    for i, events in enumerate(zip(*calls, strict=True)):
        kind = events[0][2]
        if any(event[2] != kind for event in events):
            raise ValueError(f"{path}: mismatched collective order at index {i}")
        if kind == "sum":
            kind = "expert" if sums % 2 else "layer-output"
            sums += 1
        else:
            merges += 1
        if (i + 1) % 108 == 0:
            if (sums, merges) != (96, 12):
                raise ValueError(f"{path}: unexpected collective counts: {sums}, {merges}")
            sums = merges = 0
        if i >= 108:
            samples[kind].append(events)
    if any(
        len(rows) != (windows - 1) * (12 if kind == "attention-merge" else 48)
        for kind, rows in samples.items()
    ):
        raise ValueError(f"{path}: incomplete collective samples")
    result = {}
    for kind, rows in samples.items():
        result[kind] = {
            "samples": len(rows),
            "physical_gpu": {
                physical: {
                    "strictly_first_percent": round(
                        100 * sum(
                            row[i][0] < min(e[0] for j, e in enumerate(row) if j != i)
                            for row in rows
                        ) / len(rows), 2
                    ),
                    "median_lead_over_last_us": round(
                        median(max(e[0] for e in row) - row[i][0] for row in rows) / 1000, 2
                    ),
                    "median_duration_us": round(
                        median(row[i][1] - row[i][0] for row in rows) / 1000, 2
                    ),
                }
                for i, physical in enumerate(mapping)
            },
        }
    return result


def list_rows(trace):
    # Kernel names have unquoted commas in the upstream output.
    next(trace)
    for line in trace:
        yield line.rstrip("\n").split(",", 4)


def kernel_budget(path, mapping, windows, limit, warm_windows=0, variants=False):
    """Use the graph's final argmax as the boundary, even with no idle gap."""
    cards = [[] for _ in mapping]
    open_trace = gzip.open if path.suffix == ".gz" else open
    with open_trace(path, "rt", encoding="utf-8", newline="") as trace:
        for d, start, end, graph_stream, name in list_rows(trace):
            if graph_stream.partition(":")[0] == "0":
                continue
            kernel = re.search(r"\bk_[a-zA-Z0-9_]+\b", name)
            label = name if variants else kernel[0] if kernel else name
            cards[int(d)].append((int(start), int(end), label))
    result = {}
    for physical, card in zip(mapping, cards, strict=True):
        groups, block = [], []
        for event in sorted(card):
            block.append(event)
            if re.search(r"\bk_argmax_fin\b", event[2]):
                groups.append(block)
                block = []
        if len(groups) != windows + warm_windows or block:
            raise ValueError(f"{path}: GPU {physical}: expected {windows + warm_windows} complete graphs; "
                             f"got {len(groups)}, with {len(block)} trailing events")
        totals = defaultdict(list)
        launches = Counter()
        graph_us = []
        for group in groups[warm_windows + 1:]:
            by_name = Counter()
            graph_us.append((max(e[1] for e in group) - group[0][0]) / 1000)
            for start, end, name in group:
                by_name[name] += end - start
                launches[name] += 1
            for name, ns in by_name.items():
                totals[name].append(ns)
        count = len(graph_us)
        top = sorted(totals, key=lambda key: sum(totals[key]), reverse=True)[:limit]
        result[physical] = {
            "windows": count,
            "median_graph_ms": round(median(graph_us) / 1000, 3),
            "kernels": [
                {
                    "name": name,
                    "mean_us_per_window": round(sum(totals[name]) / count / 1000, 2),
                    "calls_per_window": round(launches[name] / count, 2),
                }
                for name in top
            ],
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    parser.add_argument("mapping", help="physical GPU indices in logical-device order, e.g. 102")
    parser.add_argument("--windows", type=int, default=200)
    parser.add_argument("--kernel-budget", type=int, metavar="TOP_N",
                        help="report summed per-kernel time instead of arrival order")
    parser.add_argument("--warm-windows", type=int, default=0,
                        help="extra warm-graph windows before the measured command")
    parser.add_argument("--variants", action="store_true", help="retain CUDA kernel template names")
    args = parser.parse_args()
    if sorted(args.mapping) != list("012") or args.windows < 2:
        parser.error("mapping must permute 012 and there must be at least two windows")
    if args.kernel_budget is not None:
        if args.kernel_budget < 1 or args.warm_windows < 0:
            parser.error("kernel budget needs a positive top count and nonnegative warm count")
        result = kernel_budget(args.trace, args.mapping, args.windows, args.kernel_budget, args.warm_windows, args.variants)
    else:
        if args.warm_windows or args.variants:
            parser.error("warm windows and variants require --kernel-budget")
        result = summarize(args.trace, args.mapping, args.windows)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
