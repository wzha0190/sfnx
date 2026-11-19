# Q4_K gate/up CTA size

Gate/up accounts for roughly 3.2 ms/card in the eight-row 4K trace,
and its 16K-window cost has not yet been measured in isolation. The
screen changed 256 threads to 128 or 192 on top of the exact
bundle, leaving the eight-lane row math, accumulation order and
shared-expert fusion intact. Less work per block can improve scheduling
granularity; more blocks and repeated activation preparation can also
make it slower. CPU checks verified that each geometry covers all
routed and shared output rows exactly once on the 192/224-channel shards.

| Workload | 256-thread controls, first/last | 128 threads | 192 threads |
|---|---:|---:|---:|
| Four verification rows, 512 | 13.711 / 13.702 ms | 13.756 ms | 13.719 ms |
| Six verification rows, 4K | 16.824 / 16.826 ms | 16.949 ms | 16.823 ms |
| Eight verification rows, 16K | 19.635 / 19.619 ms | 19.827 ms | 19.681 ms |
| Six lanes, 4K each | 19.234 / 19.282 ms | 19.386 ms | 19.275 ms |

The 128-thread build dropped eight-row register allocation from
78 to 72 without a stack, but both geometries lost at 16K. All
fingerprints and the forced logits matched. Keep the 256-thread
geometry. Instead of splitting the same work over more blocks,
test reducing repeated activation preparation without changing
the quantization or reductions.

Apply `q4k-gate-blocks-stack.patch` to clean upstream
`980873394a532ca0f187aae034ed4819bb205921` with `git apply`. Full stack
SHA-256: `8a3b09504cd49795d4408926aa1c26bf33be0743ce87f0458846ece23310343b`.
Build at `ARCH=70 FNX_NCARD=3` and leave the four
[exact-bundle flags](exact-decode-bundle.md) on for all profiles.
Compare `FNX_RM400_Q4K_GATE_THREADS=256/128/192/256` with fresh workers
and the same benchmark and logit commands as the bundle.
