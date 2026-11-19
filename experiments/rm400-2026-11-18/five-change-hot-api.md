# Five-change hot API bracket against the installed engine

Two independently warmed passes per profile on loopback, in
production/candidate/candidate/production order, gave:

| Case | Production decode mean | Candidate decode mean | Decode gain | Prefill change | TTFT change |
|---|---:|---:|---:|---:|---:|
| 512 | 182.85 tok/s | 186.15 tok/s | +1.805% | −0.328% | +0.308% slower |
| 4K | 156.55 tok/s | 160.50 tok/s | +2.523% | +0.250% | −0.235% faster |
| 16K | 169.40 tok/s | 173.95 tok/s | +2.686% | −0.020% | +0.013% slower |

All warm-up and measured response hashes matched, with 128 output
tokens and no cache reuse. The 16K paired gains were 2.715% and
2.656%; the gate failed both the 3% target and the non-regression
requirement. The small prefill deltas are measured values, not yet
attributed to a kernel. No full acceptance or cutover was attempted.

The engine logs show 44 measured 16K rounds with 158 drafts offered,
84 accepted and no lookup matches on every profile: about 4.59
verification rows per round, not eight. The bracket saved about
0.45 ms/round. It needs another 0.052 ms/round merely to reach 3%
under the same round count, plus enough margin to cover short-prompt
prefill and run-to-run variation. Use the serving width and timing
distribution, not the eight-row proxy, to choose the next experiment.

Exact candidate source: [q5-down-fixed-shape-stack.patch](q5-down-fixed-shape-stack.patch)
(SHA-256 `26185b089d00797624fb3b0749b904747084ec34d7f655fed0532e83c579d275`). `make bin/sfnx` on clean
upstream `980873394a532ca0f187aae034ed4819bb205921` plus that stack,
`ARCH=70 FNX_NCARD=3`. Enable the [four bundle flags](exact-decode-bundle.md)
and `FNX_RM400_Q5_DOWN_FIXED_SHAPE=1`, with the installed engine's other
settings unchanged. The control engine was `983bf700c3c3...`; this was
not a comparison against stock upstream. The [one-pass probe](measure-rm400-sfnx-onepass.py)
and [comparison tool](compare-rm400-sfnx-onepass.py) reproduce the metric.
No production deployment was made from this result.
