# RM400 matched direct API comparison — 2026-11-19

Candidate: the experiment stack through segmented compact rollback with
`FNX_RM400_COMPACT_SNAPSHOTS=1`. Other experiment flags were disabled.
Upstream was `980873394a532ca0f187aae034ed4819bb205921`. Both used the same
three PCIe V100 32 GiB cards, one EPYC 7443, model, tokenizer and frontend
checkout. The printed headline below is not a production deployment.

Two temporary loopback front ends ran the same production model and
configuration, apart from the test executable and compact-snapshot flag.
The candidate used segmented compact rollback and left the MTP, producer
sums, launch geometry, paired scoring and prefill chunk experiments off.
Each profile warmed up once and recorded one pass using the same
synthetic prompt texts and 128 greedy output tokens without reuse.

| Actual prompt | Decode upstream → candidate | Prefill upstream → candidate | Client TTFT upstream → candidate |
|---:|---:|---:|---:|
| 512 | 177.4 → 180.9 tok/s (+1.97%) | 1,173.2 → 1,169.5 tok/s | 0.448410 → 0.449854 s |
| 4,090 | 150.4 → 153.8 tok/s (+2.26%) | 2,977.4 → 2,974.5 tok/s | 1.388723 → 1.389939 s |
| 16,376 | 162.5 → 167.2 tok/s (+2.89%) | 3,919.9 → 3,921.5 tok/s | 4.201428 → 4.199865 s |

All three recorded responses had exactly matching output hashes. The
fastest decode gain did not reach 3%, and the shorter cases' prefill and
TTFT did not improve. Treat the small differences as observed values from
one matched pass, not proof of a sustained regression or of zero
regression. This was an isolated matched diagnostic; it does not
replace the current accepted production row or establish a routed gain.

To reproduce the exact source, apply [matched-api-stack.patch](matched-api-stack.patch)
with `git apply` at the upstream revision above, then `make bin/sfnx`
with `ARCH=70 FNX_NCARD=3`. Build the upstream control independently.
Use `FNX_RM400_COMPACT_SNAPSHOTS=1` for the patched binary with all
other experiment flags absent, and apply the same production options and
workload to both. [Probe](measure-rm400-sfnx-onepass.py),
[upstream JSON](matched-api-upstream-results.json),
[candidate JSON](matched-api-candidate-results.json) and
[gate calculator](compare-rm400-sfnx-onepass.py).
