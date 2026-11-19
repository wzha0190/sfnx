# Striped hyper-connection reduction

The two-barrier kernel now has an opt-in schedule that spreads its
88 independent eight-row reduction warps over 22 SMs instead of five.
It keeps each warp's lane assignment and floating-point summation
order. The strongest no-code alternative, the upstream one-barrier
mode at `FNX_HC1=8`, recomputes the reduction in every block; it was
slower at all three tested shapes. `FNX_HC1=3` is the pinned source
default and stayed in use for the striped candidate and controls.

| Workload | Control, first/last | Upstream one barrier | Striped reduction |
|---|---:|---:|---:|
| Eight verification rows, 4K | 19.984 / 19.975 ms | 20.444 ms | 19.849 ms |
| Six lanes, 4K each | 19.499 / 19.477 ms | 19.972 ms | 19.366 ms |
| Six lanes, 48K each | 20.775 / 20.761 ms | 21.224 ms | 20.616 ms |

The striped reduction saved 0.65–0.73% against the bracket means.
Both alternatives matched the forced `code1` logit files and solo
and batch greedy fingerprints. Retain the striped version as a
candidate, not a deployment. Its gain and the all-hit planner's
cannot be assumed additive; a combined serving gate needs a fresh
combined screen first.

Apply `hc-striped-reduce-stack.patch` with `git apply` from a clean upstream
`980873394a532ca0f187aae034ed4819bb205921` checkout, then build `ARCH=70`
with `FNX_NCARD=3`. Full patch SHA-256: `c667b28f8157e8118ad72ff6bcfa4ea0248bc30b7e6df72f53d8fc1a37061a5f`.
Use the same model and placement as in [the all-hit screen](cache-all-hit.md).
Run `bench ref/long64.bin 8 200` at `FNX_BENCH_CTX=4096` and
`bench_step ref/long164.bin 6 64 C step` for C=4096 and 49152. Use a fresh
worker for each profile: `(FNX_HC1, FNX_RM400_HC_STRIPED_REDUCE)` of
`(3,0)`, `(8,0)`, `(3,1)`, `(3,0)`. Leave other prototype flags off.
