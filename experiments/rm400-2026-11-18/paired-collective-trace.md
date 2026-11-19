# Paired cross-GPU trace analysis

The same production-flag CUPTI traces can pair collectives by graph
window and invocation, rather than summing each card independently.
In six-lane 4K decode, the attention half's ring accumulated 2.053 ms
of first-to-last arrival skew per graph. From the last arrival to the
last finish it accumulated 0.677 ms. Those figures are not separately
recoverable: early arrivals can already be doing useful ring work.

| Workload | Attention ring arrival skew | Attention ring tail | FFN ring arrival skew | FFN ring tail |
|---|---:|---:|---:|---:|
| Eight verification rows, 4K | 0.184 ms | 0.799 ms | 0.762 ms | 0.830 ms |
| Eight verification rows, 48K | 0.440 ms | 0.820 ms | 0.455 ms | 1.145 ms |
| Six lanes, 4K each | 2.053 ms | 0.677 ms | 0.640 ms | 0.934 ms |
| Six lanes, 48K each | 2.168 ms | 0.714 ms | 0.954 ms | 0.946 ms |

The six-lane attention ring's 4K sum can look large because it includes
waiting: finish skew was just 0.024 ms across all 48 calls. This favors
reducing work before that ring over another ring block-size sweep. The
wide-window `k_hc` work, measured from latest start to latest finish
and summed across invocations, was 3.53 ms at 4K. Striped reduction
tests whether spreading the same independent per-row math over more
SMs reduces that cost without changing arithmetic. A saving of
0.2–0.3 ms would be useful in a bundle; this is a target, not a
prediction, because the trace does not time the internal barrier phase.

Reproduce with `summarize-sfnx-topology-trace.py TRACE 012 --windows 24
--paired-collectives`; add `--warm-windows 37` for the six-lane traces.
The script checks 96 ring, 12 merge and 97 hyper-connection calls per
graph; its kernel-budget output still matches the original wide-4K report.
