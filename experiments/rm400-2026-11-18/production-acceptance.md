# RM400 optimized engine accepted — 2026-11-19

The combined build was promoted on RM400 at 03:18:43 AEDT. It uses the same
model, quantization, context, six lanes, GPU vision, and LiteLLM route as
the control. No changes were merged or submitted upstream.

- [Exact source patch](short-gate-up-stack.patch), SHA-256
  `dfc256cc21da291c8024759e217a1ee807188310e84edf267908a45eaa68ec96`.
  Apply to `980873394a532ca0f187aae034ed4819bb205921` and build with
  `make bin/sfnx bin/fnx_run ARCH=70 FNX_NCARD=3`. RM400 used CUDA 12.9.86,
  GCC 14.2.0, NVIDIA 580.178.04 and the pinned llama.cpp submodule.
- Enable `FNX_RM400_COMPACT_SNAPSHOTS=1`, `FNX_RM400_Q4K_SHORT_GROUPS=1`,
  and `FNX_RM400_PF_HOST_PARALLEL=1`; leave the other experiments off.
  Keep `FNX_PF_ROWS=4096`. Set `FNX_EXPERT_PROFILE` to the unmodified
  `data/expert-routes.bin` in the serving tree if installing the binary
  outside its build checkout.
- Production engine SHA-256:
  `983bf700c3c3bae70ccf186908f7ba4542faca9858fd50134e24b7de1af35ad5`.
  The Makefile embeds the checkout path, so a build at a different
  path need not have the same binary hash.

## Acceptance

A fully warmed [API bracket](combined-api-bracket.md) improved decode at
512/4K/16K by 3.01%/4.29%/4.53%, with matching text output hashes and no
headline regressions. On the active service the hot rates were
**183.0/156.8/169.7 tok/s**. The corresponding first matched upstream pass
measured **177.5/150.1/162.3 tok/s**. See [raw production pass](production-hot-onepass.json).

A newly generated llama.cpp picture reference used the published F16
projector, SHA-256 `1f7b7f0b984cf065c604360c29c8098362ed61b290db0ff12c6f360bb1a8a980`.
Against the fresh upstream sFNX base, all four teacher-forced logit outputs
matched byte for byte on two repeats; the picture measured 199/200 top-1
and KL mean 4.44e-3 versus llama.cpp. Cross-width checks passed for code and
edit. `batch 96` matched standalone tokens with and without drafts; `cache2`
matched both reuse targets and 16/16 tokens in both cases. The upstream API
and image tests passed 10/10 and 6/6 on the loopback candidate.

Mixed thermal acceptance alternated six concurrent generation requests and
uncached 30,000-word prompt reads for 16 cycles/605 samples per GPU. Core
and HBM peaked at 67/69/71 C, with zero delta in software and hardware
thermal slowdown counters. The production transaction committed only after
direct loaded health, hardware vision, and scoped LiteLLM discovery, text,
and image completions passed. The original engine and config were retained
in a checked, root-only rollback archive.
