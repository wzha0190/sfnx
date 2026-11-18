# Segmented rollback and matched upstream comparison

Apply `gdn-compact-batch` after the corrected compact solo implementation.
Fork-only experimental patches remain off unless explicitly selected.
The upstream `tools/lab.sh cmd` was used with one model shared by both
workers, `FNX_MAX_CTX=262144`, `FNX_NGRAM=ram`, `FNX_MTP_EXPERTS=q4_0`,
`FNX_PF_ROWS=4096`, and `FNX_BENCH_CTX=4096` for `bench`. The quality
gate used `batch 96`; `bdecode 6 256 prose2,code1` and
`decode 192 6 15 edit1,code1,prose2` provided the lab generation targets.

### Ring launch size and dense tiling (2026-11-18)

With compact solo rollback on and producer-side sums off, the default
256-thread decode ring bracket was **17.249 / 17.203 ms**. The 128- and
64-thread variants measured 17.194 and 17.209 ms, respectively.
Selecting a two-output-row tile for mid-sized Q8_0 projections (2,048
rows and up, verification width 3–8) measured 17.233, 17.215 and
17.223 ms with the 256-, 128- and 64-thread rings. All top-1 fingerprints
matched. The best alternative beat the faster control by only 0.009 ms;
neither toggle showed a gain worth counting or enabling.

The 4K prefill path borrows the recurrent snapshot allocation. On a
224-channel shard its FFN scratch alone is about 536.25 MiB against
the 540 MiB checkpoint allocation, before alignment. Shrinking the
checkpoint block alone would therefore not recover that VRAM at the
current prefill chunk. The segmented compact prototype keeps the
allocation, placing each segment's update vectors in its existing
slots. All 14,892 positive-width layouts through 16 rows and six
lanes passed [the CPU bounds check](check-sfnx-gdn-compact-layout.py);
GPU correctness is a separate gate.


### Segmented compact rollback against upstream (2026-11-18)

The compact implementation was extended to each lane's accepted prefix.
Upstream's `batch 96` gate reported identical per-lane greedy tokens
with and without drafts. In the same held-model session, workers at
`980873394a53` and the candidate used the original model and 262,144
context cap; the order was upstream, bundle with compact off, bundle
with compact on, upstream. Rates below compare against the mean of the
two upstream controls. Each decode test used upstream's warm-up or
fixed sampled seeds. No public API or LiteLLM performance is inferred.

| Workload | Upstream bracket | Full snapshot bundle | Compact bundle | Change vs upstream |
|---|---:|---:|---:|---:|
| Six-row verify, wall latency | 17.510 / 17.505 ms | 17.382 ms | 17.215 ms | −1.67% |
| Greedy edit, 192 generated | 388.0 / 388.1 tok/s | 393.9 tok/s | 397.2 tok/s | +2.36% |
| Greedy new code, 192 generated | 203.3 / 203.3 tok/s | 206.5 tok/s | 207.5 tok/s | +2.07% |
| Sampled prose, 5 × 192 generated | 142.0 / 141.5 tok/s | 144.2 tok/s | 145.0 tok/s | +2.29% |
| Sampled six lanes, 1,536 generated | 310.9 / 310.1 tok/s | 312.8 tok/s | 314.5 tok/s | +1.29% |

Solo round and draft counts matched. The sampled six-lane planner offered
897 drafts with compact snapshots versus 919 in both controls; the two
paths did not run the identical plan. The greedy lane gate and the
teacher-forced solo logit gate passed, not complete production acceptance.
No workload in this measured sweep reached 3%.

The ring-size result above has a [method correction](lab-worker-flags.md):
its function-static flag could have stayed fixed across all nominal
variants. The segmented compact comparison is not affected because its
flag is read at engine construction.
