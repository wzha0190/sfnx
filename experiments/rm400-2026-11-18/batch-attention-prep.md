# Fused batch attention preparation

At six lanes and 4K, the trace sums about 0.83 ms/card for the four
per-lane launches (index prepare/pool, attention prepare, K/V append).
The prototype reuses the solo kernels' fused math and emits two
launches per attention layer instead of 24. It preserves each row's
rotary table and K/V pages, and reads newly pooled keys from the
correct draft segment's projection after the same half conversion.
The 0.83 ms is an upper bound on removable time, not a projected gain:
the fused form still does the math. Estimate 0.2–0.5 ms if most of the
small-launch overhead disappears; measure both one-row and speculative
batch paths. Unlike solo verification, this could improve multi-user
throughput without moving the single-request API needle.

| Workload | Control, first/last | Fused index and K/V preparation |
|---|---:|---:|
| Six lanes, 4K each, one row each | 19.525 / 19.526 ms | 18.731 ms |
| Six lanes, 48K each, one row each | 20.821 / 20.807 ms | 19.963 ms |
| Six-lane adaptive sampled decode, overall | 288.3 / 289.2 tok/s | 300.7 tok/s (different output) |

The solo-step benchmark here is **one row per batch lane**, not
single-request serving. Step latency fell 4.07%/4.09% and both greedy
fingerprints matched. The upstream `batch 16` check matched standalone
greedy tokens across 1/2/3/6 lanes with and without drafts. Its sampled
subtest checks that emitted IDs are in vocabulary, not exact replay.
The longer warmed sampled run changed all six output fingerprints
versus two matching controls. It offered 587 drafts versus 601 in
both controls, so its apparent 4.14% gain is not a matched-output
result.

The pinned `BatchDecoder` incorporates measured graph-capture time
into its adaptive draft plan; that can change random-number consumption.
It does not rule out a numerical difference. The next isolation uses
the upstream `FNX_BATCH_FIXED=1` diagnostic to remove measured capture
cost from the plan, comparing index-only, K/V-only, and fused modes
with fresh controls on the same seed and fixtures. Leave batch fusion
off in production and in the exact decode bundle.

Apply `batch-attention-prep-stack.patch` with `git apply` from clean upstream
`980873394a532ca0f187aae034ed4819bb205921`, then build `ARCH=70 FNX_NCARD=3`.
Full stack SHA-256: `127843bf7ef23844fca7404feb256d9f588fe47bcd4455c253ff92e2c8570513`.
Keep the production flags, stock expert profile and 3 GiB RAM placement.
In fresh workers run `bench_step ref/long164.bin 6 64 C step` for C=4096
and 49152, and `bdecode 6 160 prose2,code1`. Set `FNX_BATCH_DRAFTS=1`,
`FNX_RM400_BATCH_FINGERPRINT=1` and `FNX_RM400_BATCH_ATTN_PREP=0/3/0`.
`batch 16` exercises upstream's standalone greedy checks.
