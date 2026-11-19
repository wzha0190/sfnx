#!/usr/bin/env python3
"""2026-11-19: blend synthetic lab tallies with the pinned sFNX prior."""

import argparse
from pathlib import Path
import struct


SIZE = 48 * 512
LAYOUT = struct.Struct(f"<{2 * SIZE}I")
MASS = 16_000_000


def load(path):
    values = LAYOUT.unpack(path.read_bytes())
    if not all(sum(values[i:i + SIZE]) for i in (0, SIZE)):
        raise ValueError(f"{path}: missing decode or prompt tallies")
    return values


def blend(stock, training):
    out = []
    for start in (0, SIZE):
        baseline = stock[start:start + SIZE]
        measured = [[v for v in run[start:start + SIZE]] for run in training]
        baseline_total = sum(baseline)
        totals = [sum(run) for run in measured]
        for i, v in enumerate(baseline):
            # Keep 75% stock prior. Each independently chosen training
            # fixture contributes the same normalized share of the rest.
            ratio = 0.75 * v / baseline_total
            ratio += sum(run[i] / n for run, n in zip(measured, totals, strict=True)) * 0.25 / len(training)
            out.append(round(MASS * ratio))
    return LAYOUT.pack(*out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stock", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("training", nargs="+", type=Path)
    args = parser.parse_args()
    data = blend(load(args.stock), [load(path) for path in args.training])
    with args.output.open("xb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
