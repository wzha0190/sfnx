#!/usr/bin/env python3
"""2026-11-18: bounds-check the RM400 compact recurrent rollback layout."""

from itertools import combinations


def check(max_rows=16, max_lanes=6, heads=16, head_size=128):
    frame = heads * head_size * head_size
    update = heads * (1 + 2 * head_size)
    arena = (max_rows - 1) * frame
    assert update <= frame
    tested = 0
    for total in range(1, max_rows + 1):
        for count in range(min(total, max_lanes)):
            for cuts in combinations(range(1, total), count):
                bounds = (0, *cuts, total)
                last = 0
                for lo, hi in zip(bounds, bounds[1:]):
                    rows = hi - lo
                    if rows == 1:
                        continue  # no intermediate state or partial commit
                    start = lo * frame
                    end = start + frame + (rows - 2) * update
                    assert last <= start <= end <= min(hi * frame, arena), bounds
                    for keep in range(1, rows):
                        assert start + frame + (keep - 1) * update <= end, (bounds, keep)
                    last = end
                tested += 1
    return tested


if __name__ == "__main__":
    print(f"{check()} segment layouts passed compact rollback bounds")
