# Shared-expert scheduling alternatives

The existing Q4_K path recomputes the complete shared-expert SwiGLU
inside each of roughly 320 fused output CTAs per layer. The screen
kept the 256-thread geometry and compared keeping
that path, moving only shared SwiGLU and down to the second stream,
and moving all shared-expert work there. Both alternatives reuse the
pinned engine's existing `swiglu_stacked_q8_1` and `q8s_gemv` with the
same half scales, weights and join before reduction. They do not add
runtime buffers. The first mode retains the router's shared gate/up
work while preparing its down activations once.

| Workload | Fused controls, first/last | Shared down on second stream | All shared work on second stream |
|---|---:|---:|---:|
| Four verification rows, 512 | 13.707 / 13.697 ms | 14.113 ms | 14.110 ms |
| Six verification rows, 4K | 16.825 / 16.815 ms | 17.099 ms | 17.131 ms |
| Eight verification rows, 16K | 19.655 / 19.611 ms | 19.864 ms | 19.847 ms |
| Six lanes, 4K each | 19.269 / 19.283 ms | 19.520 ms | 19.540 ms |

Forced `code1` logits and greedy fingerprints matched. Both alternatives
were slower at every shape; the 16K regressions were 1.18% and 1.09%.
This confirms the fused path for the current bundle. The test does not
separately measure stream-event overhead or redundant SwiGLU work.

Apply `shared-expert-layout-stack.patch` to clean upstream
`980873394a532ca0f187aae034ed4819bb205921` with `git apply`. Full stack
SHA-256: `0e5d0de9d104e60c0815f1ba9cbb86e95eedf0c4f4575714ae02bb0893186e09`.
Build at `ARCH=70 FNX_NCARD=3` and leave all four
[exact-bundle flags](exact-decode-bundle.md) on. Compare
`FNX_RM400_SHARED_EXPERT_LAYOUT=0/1/2/0` with fresh workers, and use
the same benchmark and logit commands as the bundle.
