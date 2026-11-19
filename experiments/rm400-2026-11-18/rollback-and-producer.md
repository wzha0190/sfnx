# Compact rollback and producer-side Q4_K sums

Start with the experiment stack in [README.md](README.md). To reproduce
this branch of the lab, also apply `batch-fused-projections`,
`q4k-activation-twin`, `q4k-vector-components`, `gdn-snapshot-ceiling`,
then `gdn-compact-rollback`. Leave the batch, twin, and ceiling flags off.
`FNX_RM400_COMPACT_SNAPSHOTS=1` enables the solo compact rollback prototype;
`FNX_RM400_BENCH_KEEP` and `FNX_RM400_LOGITS_KEEP` select the accepted prefix.
`gdn-upstream-fma` corrects explicit rounding order for the SM70 CUDA
12.9 build; `q4k-producer-sums` adds `FNX_RM400_PRODUCER_SUMS=1`. Do not
serve these experiments; results for the corrected variant are pending.

### Recurrent snapshot write ceiling (2026-11-18)

The upstream benchmark commits exactly one row of every verification
window. The diagnostic retained that row's recurrent snapshot and
skipped all later full-state snapshots without dropping the recurrence
math or changing the history snapshots. A guard rejects any partial
commit other than one row in this benchmark mode. On 36 recurrent
layers with 16 value heads per card, one full saved state per layer is
1 MiB/card. The diagnostic skips 144 MiB/card at six rows or 324 MiB/card
at eleven rows. These are requested write bytes, not measured HBM traffic.

| Rows | Full snapshots A/B controls | Row-0-only diagnostic | Mean wall saving |
|---:|---:|---:|---:|
| 6 | 17.316 / 17.338 ms | 17.149 / 17.169 ms | 0.168 ms (0.97%) |
| 11 | 25.276 / 25.404 ms | 24.987 / 25.005 ms | 0.344 ms (1.36%) |

The same model stayed loaded for the 0/1/1/0 passes at a 4,096-token
starting context and 262,144-token cap. This measures a ceiling for the
row-0 checkpoint strategy before saving compact update records or paying
replay costs. It is not usable for serving. A compact format also needs
to restore any accepted prefix, not just one row.


### Compact rollback prototype and exactness failure (2026-11-18)

The first implementation retained recurrent row 0 and saved subsequent
FP32 decay, key and delta vectors instead of full states. On a partial
commit it replayed the accepted prefix in the existing copy job. At six
verification rows, the held-model A/B/A comparisons cut 0.146 ms from
the keep-one verification median and 0.173 ms from keep-three, based on
the mean of the two medians per flag. These timings did not qualify:
top-1 fingerprints differed, and teacher-forced `code1` top-64 logit files
differed for keep counts 1, 2, 5 and 6. The error on full commits ruled out
replay itself as the only source of drift.

SM70 disassembly showed that the original recurrence first rounds
`key * delta`, then fuses `decay * prior` with that product. The first
compact helper did the reverse. The prototype was rejected; a follow-up
matches the observed rounding order before repeating the exactness and
timing checks. This does not change the production engine.

