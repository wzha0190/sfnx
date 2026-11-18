# Shorter Q4_K gate/up load groups — RM400

Apply [short-gate-up-stack.patch](short-gate-up-stack.patch) with `git apply`
at upstream `980873394a532ca0f187aae034ed4819bb205921`; build `make lab
bin/sfnx ARCH=70 FNX_NCARD=3`. This aggregate patch replaces the individual
experiment patches. Keep compact snapshots enabled for every profile and
alternate `FNX_RM400_Q4K_SHORT_GROUPS=0/1/1/0` with fresh lab workers. Other
experimental flags were off. Use `FNX_BENCH_CTX=4096`, `FNX_MAX_CTX=262144`,
`FNX_NGRAM=ram`, `FNX_MTP_EXPERTS=q4_0`, and `FNX_PF_ROWS=4096`.
Commands: `bench ref/long64.bin T 200` and
`logits ref/code1.bin ref/lgr/llama_cuda_code1.lgr T OUT.lgr` per width.

The existing kernel loads weights in groups of three and two per lane.
The experiment uses two, two and one, retaining the same weight rows,
dot products and accumulation order. It trades some load overlap for
shorter register live ranges. On SM70 the register-only residency limit
for a 256-thread block rises from two blocks per SM to three at widths
three, seven and eight. Width six stays at three. Widths four and five
no longer need a stack frame. This is a compiler-resource result, not a
measurement of achieved occupancy or throughput.

| Verification rows | Registers/thread, control → short | Stack bytes/thread, control → short |
|---:|---:|---:|
| 3 | 94 → 79 | 0 → 0 |
| 4 | 80 → 79 | 16 → 0 |
| 5 | 80 → 79 | 24 → 0 |
| 6 | 80 → 74 | 0 → 0 |
| 7 | 97 → 76 | 0 → 0 |
| 8 | 99 → 78 | 0 → 0 |

The traced gate/up work was 2.82–2.83 ms per six-row window on the
heavy shards. Shaving 0.2 ms from a 17.5 ms window would take roughly
7% of that gate/up time if it all fell on the critical path. The lab
measured 199 verification windows per profile after graph capture,
using fresh workers and one model holder in an A/B/B/A bracket:

| Verification rows | Control bracket, wall | Short groups bracket, wall | Mean wall reduction |
|---:|---:|---:|---:|
| 3 | 13.470 / 13.477 ms | 13.345 / 13.347 ms | 0.95% |
| 6 | 17.208 / 17.175 ms | 17.160 / 17.120 ms | 0.30% |
| 7 | 18.625 / 18.564 ms | 18.293 / 18.251 ms | 1.73% |
| 8 | 20.227 / 20.273 ms | 19.864 / 19.921 ms | 1.77% |

Top-1 fingerprints matched at each width, and all eight `code1`
teacher-forced logit files were byte-identical. This justifies testing the
combined candidate through the direct API; it does not establish a 3%
serving gain or full acceptance.
