# Four-change exact decode bundle

The striped hyper-connection, all-hit cache, Q5_1 unpack-once and fused
Q8 two-row kernels were tested together in a fresh-worker A/B/B/A
bracket. Experimental CPU lookup and fused batch attention were off,
and the stock 3 GiB expert placement was unchanged.

| Workload | Controls, first/last | Bundle, first/second | Lower wall time |
|---|---:|---:|---:|
| Four verification rows, 512 | 13.937 / 13.938 ms | 13.706 / 13.706 ms | 1.66% |
| Six verification rows, 4K | 17.181 / 17.194 ms | 16.842 / 16.810 ms | 2.10% |
| Eight verification rows, 16K | 20.158 / 20.164 ms | 19.677 / 19.644 ms | 2.48% |
| Six lanes, 4K each, one row each | 19.545 / 19.556 ms | 19.268 / 19.279 ms | 1.42% |

All greedy fingerprints and the forced `code1` logit files matched.
The 16K result is equivalent to 2.55% more fixed-width windows per
second, not a hot API token-rate result. Additional request overhead
could dilute it; the tested widths do not cover the serving distribution.
Retain the exact bundle but do not take the service offline for a full
API bracket until there is evidence for another incremental gain.

The measured source is identical to [`batch-attention-prep-stack.patch`](batch-attention-prep-stack.patch)
(SHA-256 `127843bf7ef23844fca7404feb256d9f588fe47bcd4455c253ff92e2c8570513`), but batch attention is off.
Build from clean upstream `980873394a532ca0f187aae034ed4819bb205921`
with `ARCH=70 FNX_NCARD=3`. Use deployed default flags and placement,
`FNX_HC1=3`, and toggle these four flags together in fresh workers:
`FNX_RM400_CACHE_ALL_HIT`, `FNX_RM400_HC_STRIPED_REDUCE`,
`FNX_RM400_Q5_DOWN_UNPACK_ONCE`, `FNX_RM400_Q8S_AB_TILE2`.
Use `bench ref/long64.bin T 200` for the three widths and contexts in
order, then `bench_step ref/long164.bin 6 64 4096 step`.
