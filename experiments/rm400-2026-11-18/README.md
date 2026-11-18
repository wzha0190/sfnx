# RM400 CUDA diagnostics — 2026-11-18

These are isolated experiments, not engine changes enabled by this branch and
not production-ready. The model was held fixed (Huihui UD-Q4_K_XL variant), on
one EPYC 7443 with three PCIe V100 32 GiB cards. The matched controls were
built at `980873394a532ca0f187aae034ed4819bb205921`, `ARCH=70`, `FNX_NCARD=3`.

Apply patches to that upstream revision with `git apply --recount --unidiff-zero`.
Apply `router-compaction`, `hc-live-rows` and `q4k-sum-cache` together to
rebuild the three-patch bundle; add `qsa-warp-prefix` for the four-patch bundle.
The attention empty-split and score-tile patches extend it; results for those
patches are not included below. Down reuse and decode MMA are separate labs.
For down reuse, apply only `tools/kbench.cu` to the matching control.

Verification timing: `FNX_BENCH_CTX=4096` or `32768`,
`FNX_MAX_CTX=FNX_BENCH_CTX+4096`, `FNX_NGRAM=ram`, `FNX_MTP_EXPERTS=q4_0`,
`FNX_PF_ROWS=4096`, `bin/fnx_run "$model" bench ref/long64.bin 6 200`.
One processes each build separately; the first window is excluded. These are
not generated-token throughput or quality acceptance. The promotion target
is 3% for the complete candidate, with no headline regression and passing
correctness, vision, thermal, direct API and routed checks.

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

