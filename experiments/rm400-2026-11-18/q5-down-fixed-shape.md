# Fixed-shape Q5_1 down projection

The Q5_1 down kernel accounted for about 2.22 ms/card at eight 4K
verification rows. The RM400 FF shards always use six or seven 32-value
units; using those as compile-time constants lets the compiler replace
runtime division and unroll the final serial sum in the same order.
The geometry, shared activation quantization and packed weights stay
unchanged. This is narrower than a new packing format or another
work-redistribution experiment. On top of the four-change bundle:

| Workload | Controls, first/last | Fixed shape, first/second | Lower wall time |
|---|---:|---:|---:|
| Four verification rows, 512 | 13.703 / 13.712 ms | 13.579 / 13.584 ms | 0.92% |
| Six verification rows, 4K | 16.830 / 16.811 ms | 16.662 / 16.638 ms | 1.01% |
| Eight verification rows, 16K | 19.592 / 19.639 ms | 19.439 / 19.430 ms | 0.92% |
| Six lanes, 4K each | 19.249 / 19.282 ms | 19.126 / 19.124 ms | 0.73% |

All checked greedy fingerprints and forced `code1` logit files matched.
The 16K candidate saved another 0.181 ms on its bracket mean. Against
the earlier production-flag lab control, the five changes imply about
3.7% more fixed-width windows/s across separate brackets, not a
matched serving result. This justifies a loopback hot API A/B/B/A
against the installed optimized build, with batch fusion and other
experimental changes off. No lab result is a promotion.

Apply `q5-down-fixed-shape-stack.patch` to clean upstream
`980873394a532ca0f187aae034ed4819bb205921` with `git apply`. Full stack
SHA-256: `26185b089d00797624fb3b0749b904747084ec34d7f655fed0532e83c579d275`. Build `ARCH=70 FNX_NCARD=3`.
Leave the [four original bundle flags](exact-decode-bundle.md) on, retain
256 gate threads and leave shared-expert layout and batch attention at 0.
Compare `FNX_RM400_Q5_DOWN_FIXED_SHAPE=0/1/1/0` in fresh workers with the
same benchmark and logit commands as the earlier bundle.
