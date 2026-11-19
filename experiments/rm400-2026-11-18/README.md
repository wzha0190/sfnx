# RM400 CUDA diagnostics — 2026-11-18

These are isolated experiments, not enabled engine changes or production
recommendations. The model was held fixed (Huihui UD-Q4_K_XL variant), on one
EPYC 7443 with three PCIe V100 32 GiB cards. Matched controls were built at
`980873394a532ca0f187aae034ed4819bb205921`, `ARCH=70`, `FNX_NCARD=3`.

Rebuild on that upstream revision using `git apply --recount --unidiff-zero`:

1. Apply `router-compaction`, `hc-live-rows` and `q4k-sum-cache` to make the
   three-patch bundle. Add `qsa-warp-prefix` for the selector bundle.
2. Add `attention-empty-splits` and `qsa-empty-score-tiles`, then
   `ring-local-pairs` and `hc-balanced-groups` for the best measured bundle.
3. Opt-in diagnostic branches: add `q4k-activation-twin` to test the original
   `FNX_RM400_Q4K_TWIN=1` experiment, then `q4k-vector-components` to remove
   its temporary arrays. `batch-fused-projections` can be added independently
   (`FNX_RM400_BATCH_FUSED=1`). Leave both flags off for the measured best
   bundle. The `gdn-snapshot-ceiling` patch applies only to the benchmark
   (`FNX_RM400_FIRST_SNAPSHOT=1`) and is not a production optimization.

`moe-down-reuse` and `moe-decode-mma` are separate labs. For down reuse, apply
only the `tools/kbench.cu` edits to the matching control.

Verification timing: set `FNX_BENCH_CTX=4096` (or `32768` where noted),
`FNX_MAX_CTX` as specified below, `FNX_NGRAM=ram`, `FNX_MTP_EXPERTS=q4_0`,
`FNX_PF_ROWS=4096`; run `bin/fnx_run "$model" bench ref/long64.bin 6 200`.
Exclude the first verification window. `tools/lab.sh cmd` can also run the
same benchmark without reloading the model between flags. For flags
cached in function-local statics, set the flag, stop only the worker with
`tools/lab.sh stop`, then start it with the next `cmd`. The loader can keep
the engine library mapped after `dlclose`; changing the flag in the same
worker does not prove the new variant ran. See [lab-worker-flags.md](lab-worker-flags.md).
These timings
are not generated-token throughput or quality acceptance. The current operator-set promotion target (2026-11-19) is a
0.5% hot API gain for the complete candidate against the currently deployed
build, with no headline regressions and passing correctness, batch, vision,
thermal, direct API and routed checks. The earlier 3% threshold still applies
when interpreting historical gate reports from before the change.

### Routed-expert gate/up prototype (2026-11-18)

The isolated `sm_70` build reused exact integer activation sums across Q4_K
weight rows; model files, weights, and output rounding expressions were
unchanged. Upstream `kbench` on its default 192-channel synthetic workload
measured 26.6 → 25.6 µs at three rows, 38.9 → 38.9 µs at five, and
76.8 → 72.7 µs at 16. The real-model six-row verification test without CUPTI
measured **17.493 → 17.470 ms** median wall time (0.13% less time), with the
first graph capture excluded. This diagnostic does not qualify for the
headline tally and the prototype was not promoted. No correctness
acceptance is claimed for the rejected prototype.


### Wider-shard decode candidates (2026-11-18)

Earlier SwiGLU prequantization on the two 224-channel shards lowered the
synthetic down-projection time from 37.9 to 36.9 µs at six rows and from
49.2 to 46.1 µs at eight rows. On the real model, matched builds measured
**17.459 → 17.462 ms** median wall time for 199 six-row verification windows
after the first graph capture. No improvement and no promotion.

A separate synthetic diagnostic compared the real decode integer kernels
against the existing prefill tensor-core kernels, on a 224-channel shard,
with five experts shared among the rows and 24 MiB of L2 displacement before
each measured launch. Times are the sum of isolated gate/up, SwiGLU (where
separate), and down medians; they do not include graph integration costs.

| Decode rows | Integer path | Existing prefill tensor-core path |
|---:|---:|---:|
| 1 | 34 µs | 81 µs |
| 3 | 60 µs | 105 µs |
| 6 | 97 µs | 146 µs |
| 11 | 166 µs | 254 µs |
| 16 | 234 µs | 327 µs |

This rules out reusing the prefill kernel as-is, not a purpose-built decode
tensor-core kernel. The kernel tested works in 16-token tiles per expert;
at six verification rows the synthetic routing produced 34 jobs from 60
pairs, just 1.76 useful tokens per job on average. Any decode rewrite needs
to make small expert jobs cheaper, not just increase nominal arithmetic
throughput. These are diagnostics, not accepted hot one-pass scores.


### Combined exact-arithmetic prototypes (2026-11-18)

Router job compaction uses warp ballots and prefix counts while preserving
the first-pick job order. It measured **17.462 → 17.432 ms** on matched
six-row diagnostic binaries. The combined build also reused the Q4_K
activation sums and skipped whole warps of dummy down rows in hyper-connection
mixes. Its matched control and candidate medians were **17.510 → 17.386 ms**
(0.71% less wall time), and GPU medians were 17.453 → 17.331 ms. Isolated
hyper-connection timing did not improve. These are single comparisons;
attribution and reproducibility are not established. Full correctness and
hot one-pass acceptance were not run; production was not changed.


### Sparse-attention selection (2026-11-18)

The three-patch bundle was retested against upstream and against the same
bundle with warp-prefix counts in the sparse-attention selector. The selector
reduces block-wide barriers without changing the threshold or the ordering of
tied and selected blocks. In 199 measured verification windows of six rows
each, the wall medians were:

| Starting context | Upstream | Three patches | With selector patch | Change from upstream |
|---:|---:|---:|---:|---:|
| 4,096 | 17.475 ms | 17.393 ms | 17.382 ms | −0.53% |
| 32,768 | 17.772 ms | 17.728 ms | 17.665 ms | −0.60% |

The first window in each run captured the graph and was excluded. The order was
control, three patches, then selector, once per context; the selector's isolated
contribution has not been reproduced. The tests used an allocation cap 4,096
tokens above each starting context, not the configured production cap of
262,144. These are lab diagnostics, not hot API scores or a promotion result.


### Empty attention work at the production context cap (2026-11-18)

With a 4,096-token starting context and the production 262,144-token
allocation cap, matched six-row verification medians were 17.567 ms upstream,
17.461 ms with the four-patch selector bundle and **17.447 ms** when empty
attention splits and invisible QSA score tiles exited before setup. The
last two changes together saved 0.014 ms versus the previous bundle; the
complete candidate was 0.68% below the upstream median. Run order was
candidate, control, then previous bundle. This does not establish a hot API
gain or support a more complex QSA grid scheduler at typical contexts.


### Decode critical-path budget (2026-11-18)

On the six-row CUDA trace, each heavy shard averaged 3.29 ms of
hyper-connection kernels, 2.82–2.83 ms of Q4_K gate/up, 2.03 ms of expert
down-projection, 1.73–1.79 ms of ring sums, and 0.97 ms of recurrent-core
kernels per traced verification window. These are summed kernel times,
not independent improvements; the ring time includes waits and work can
overlap across cards. `summarize-sfnx-topology-trace.py --kernel-budget 8`
counts graph completions rather than relying on idle gaps and excludes the
first graph.

At approximately 17.5 ms, a 3% reduction is about 0.52 ms. After the
empty-attention bundle's 0.12 ms diagnostic gain, about 0.4 ms remained:
roughly 12% of hyper-connection time or 14% of Q4_K gate/up time if a
single subsequent change carried the rest. That is a derived scale check,
not a latency prediction. Ring changes must be measured across all three
cards; speeding up the first arrival does not establish a wall-time gain.

### Paired ring loads and balanced hyper-connections (2026-11-18)

At a 4,096-token starting context and 262,144-token allocation cap, the
matched six-row verification run measured the following wall/GPU medians
in run order. Each row adds the named change to the previous bundle.

| Build or added change | Wall | GPU |
|---|---:|---:|
| Upstream control | 17.524 ms | 17.456 ms |
| Empty-attention bundle | 17.424 ms | 17.366 ms |
| Paired loads and local accumulation before ring waits | 17.329 ms | 17.275 ms |
| Balanced 84/84/84/72 hyper-connection down groups | **17.283 ms** | **17.227 ms** |
| Opt-in Q4_K reads from the aligned activation twin | 18.000 ms | 17.942 ms |

The best bundle reduced diagnostic wall latency by **1.38%**. Pairing ring
loads and moving arithmetic earlier keeps the wire format and addition order
unchanged. The hyper-connection change still launches 80 CTAs and retains
row-indexed reductions. Neither optimization has complete correctness and
serving acceptance. The twin was 4.15% slower than the best bundle in this
sweep and stays off. No headline score or production change.


### Batched projection fusion (2026-11-18)

The six-lane paths were modified to opt into the projection kernels already
used for single-lane windows. The upstream model-holder lab kept the same
loaded model and alternated the flag in 0/1/1/0 order. With a 4,096-token
prompt per lane, 262,144-token allocation cap and 199 recorded steps of
one row per lane, wall medians were **19.496 / 19.461 / 19.462 / 19.479 ms**.
The two on runs averaged 0.13% less wall time than the two off runs; this is
not a meaningful gain or a measurement of speculative serving throughput.
No batched change was enabled in production.

In the earlier six-lane speculative decode lab, the default planner
captured only 4 graphs in 267 full-batch windows, at 10.82 ms each. Even
eliminating those captures would save approximately 0.16 ms per 33.04 ms
window (0.49%), excluding initial capture costs in other workloads. A
larger graph cache would need evidence from more variable lane workloads
before it justifies the extra device memory and complexity.


### Spill-free Q4_K twin retest (2026-11-18)

The `sm_70` six-row pointer-based twin had a 24-byte stack and 16 local
load/store instructions in its kernel body; its twin-off control had
neither. Explicit vector members removed the stack, but raised register
allocation from 80 to 96 per thread. With 256 threads per block, the
register-only limit on the V100 falls from three resident blocks per SM
to two. This is one plausible counterweight to the fewer activation loads.

The held-model 0/1/1/0 test at the same 4K prompt and 262,144 cap measured
**17.320 / 17.250 / 17.354 / 17.293 ms**. The on/off means were 17.302 and
17.307 ms; there is no reproducible gain. The six-row teacher-forced
`code1` top-64 logit files were byte-identical for the two settings. This
does not establish full model or vision acceptance. The twin stays off.

