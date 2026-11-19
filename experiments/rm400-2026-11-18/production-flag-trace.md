# Production-flag trace and dense projections

A CUPTI lab build used the deployed flags, model and expert profile,
with all new prototype switches off. The table shows GPU 0's summed
kernel time per window; overlapping time and waits cannot be counted
as independent savings. Exclude 37 extra graph-warm windows for the
six-lane trace and the first captured benchmark window in both modes.

| Workload | Traced wall median | Dense Q8, incl. fused | Expert copy | Sparse score + selection |
|---|---:|---:|---:|---:|
| Eight verification rows, 4K | 20.630 ms | 3.544 ms | 0.157 ms | 0.327 ms |
| Eight verification rows, 48K | 21.136 ms | 3.549 ms | 0.158 ms | 0.867 ms |
| Six lanes, 4K each | 22.273 ms | 3.436 ms | 0.224 ms | 0.338 ms |
| Six lanes, 48K each | 23.711 ms | 3.436 ms | 0.920 ms | 1.114 ms |

Only the last case began lending K/V slots: up to 773/773/902 slots
per card. The copy kernel also launches for empty lists, so its short
time is an upper bound on any short-context placement win, not a PCIe
byte count. Long-context latency does have two targets: the extra expert
copies when the arena lends slots, and sparse scoring/selection even
when no slots are lent.

The first dense screen lowered activation tiles from four to two in
large/segmented Q8 and added a separate two-token tile for the recurrent
fused projection. It preserved the column accumulation order. A fresh
worker per profile gave byte-identical six- and eight-row `code1` logits.
These are untraced hot lab medians:

| Measure | Controls, first/last | Large Q8 tile | Fused recurrent tile |
|---|---:|---:|---:|
| Six verification rows | 17.187 / 17.179 ms | 17.271 ms | 17.148 ms |
| Eight verification rows | 19.877 / 19.922 ms | 20.067 ms | 19.739 ms |
| Six lanes, 4K each | 19.482 / 19.495 ms | 19.669 ms | 19.539 ms |

The fused change lowered six/eight-row register allocation from 99/119
to 61/71 with no spill, and helped solo verification by 0.20%/0.81%
against the control means. Six-lane timing did not establish a gain;
that path uses separate projections. Leave both flags off in production.
Before another API A/B, test savings in sparse selection and, separately,
whether a lower-overhead copy launch helps the 48K six-lane trace.

To reproduce the first dense screen, apply `sfnx-q8s-dense-token-tiles-2026-11-19.patch`
on top of the deployed stack and enable only `FNX_RM400_Q8S_TILE2=1` or
`FNX_RM400_Q8S_AB_TILE2=1` in a fresh lab worker. Use `bench ref/long64.bin T 200`
at `FNX_BENCH_CTX=4096`, T=6/8, and `bench_step ref/long64.bin 6 100 4096 step`.
Trace with `tools/lab.sh trace` and use the included summary script rather
than splitting decode windows by idle gaps.
