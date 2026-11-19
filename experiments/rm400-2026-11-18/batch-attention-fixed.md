# Fixed-plan batch attention and forced logits

This isolates the [earlier adaptive mismatch](batch-attention-prep.md).

The pinned `BatchDecoder` incorporates measured graph-capture time into its adaptive draft plan, which can change random-number
consumption. With the upstream `FNX_BATCH_FIXED=1` diagnostic to remove
that timing input, all modes matched the six per-lane sampled
fingerprints and accepted 426 of 528 drafts. Each mode also matched
all 384 whole-vocabulary logit fingerprints on forced 512 and 4K
fixtures with ragged layouts, rotated lane order and partial commits.

| Fixed-plan sampled six-lane metric | Control, first/last | Index only | K/V only | Both fused |
|---|---:|---:|---:|---:|
| Overall throughput | 334.8 / 335.9 tok/s | 339.8 tok/s | 340.3 tok/s | 344.4 tok/s |
| Throughput with all lanes active | 339.9 / 340.9 tok/s | 345.1 tok/s | 345.4 tok/s | 349.8 tok/s |

The matched-output gains were 2.70% overall and 2.76% with six lanes
active. Results support adaptive scheduling, not detected numerical
drift, as the explanation for the earlier sample divergence on these
fixtures. They do not establish general equivalence or clear the solo
API gate. Leave batch fusion off in production. Retain the fused
candidate for mixed text/image and longer production-path batch
checks without changing the drafting policy.

Apply the `batch-attention-fixed-stack.patch` to clean upstream
`980873394a532ca0f187aae034ed4819bb205921` with `git apply`, then build
`ARCH=70 FNX_NCARD=3`. Full stack SHA-256: `7c51589806014107ec4490ec7c40757f6916cef9d72ece7437f27a53fd83f95f`.
Selected flag profiles for `FNX_RM400_BATCH_ATTN_PREP` were `0/1/2/3/0`,
with `FNX_BATCH_DRAFTS=1`, `FNX_BATCH_FIXED=1`, `FNX_RM400_BATCH_FINGERPRINT=1`,
and production settings and 3 GiB placement. Restart the lab worker per
profile. Run `bdecode 6 160 prose2,code1` and
`fixed_batch_logits ref/long164.bin 16 C` at `C=512/4096`.
