# Corrected rollback and producer-side sums

See [rollback-and-producer.md](rollback-and-producer.md) for the original
reproduction steps. Build the corrected version with `gdn-upstream-fma`
applied. `FNX_RM400_COMPACT_SNAPSHOTS=1` selects compact solo checkpoints;
`FNX_RM400_PRODUCER_SUMS=1` selects the separate Q4_K experiment. Keep
`FNX_RM400_FIRST_SNAPSHOT`, `FNX_RM400_Q4K_TWIN`, and
`FNX_RM400_BATCH_FUSED` off for these results.

The two lab settings were tested on one held model with
`FNX_MAX_CTX=262144`, `FNX_LANES=6`, `FNX_BENCH_CTX=4096`,
`FNX_PF_ROWS=4096`, `FNX_NGRAM=ram`, `FNX_MTP_EXPERTS=q4_0`. The benchmark
is `bench ref/long64.bin 6 200`. Logit comparison uses `logits` with the
standard teacher-forced `code1` prompt/continuation fixtures; the lab
sets `FNX_RM400_LOGITS_KEEP` to 1, 2, 5, or 6 before each run.

Using the observed SM70 rounding order, compact-on/off and Q4_K
producer-sums-on/off produced 16 byte-identical `code1` top-64 logit files
across keep counts 1, 2, 5 and 6. All six-row top-1 fingerprints also
matched within each keep count on the 4K-context verification workload.
The control here already includes the earlier eight-patch bundle.

| Six-row test | Control bracket | Compact only | Producer sums only | Both |
|---|---:|---:|---:|---:|
| Keep one, wall median | 17.398 / 17.390 ms | 17.231 ms | 17.406 ms | 17.219 ms |
| Keep three, wall median | 17.524 / 17.550 ms | 17.375 ms | 17.561 ms | 17.384 ms |
| Keep three, whole loop mean | 17.619 / 17.634 ms | 17.480 ms | 17.659 ms | 17.487 ms |

The loop includes the partial commit/replay and initial graph capture.
Compact rollback is promising for solo decode, but the savings are
about 0.9% against this bundle, not 3% against upstream. These tests do
not cover the six-lane compact state layout, because the prototype keeps
the full snapshots for batched paths. Producer-side sums remove repeated
integer work and one block barrier in gate/up, but did not pay off and
remain disabled. Full serving validation has not been run.

