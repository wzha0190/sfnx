# Combined candidate hot API result — RM400

Use [short-gate-up-stack.patch](short-gate-up-stack.patch) at
`980873394a532ca0f187aae034ed4819bb205921`, `make bin/sfnx ARCH=70 FNX_NCARD=3`.
Set `FNX_RM400_COMPACT_SNAPSHOTS=1`, `FNX_RM400_Q4K_SHORT_GROUPS=1`, and
`FNX_RM400_PF_HOST_PARALLEL=1`. Keep all other experimental flags unset and
use the same model, tokenizer, six lanes, native 262,144 context, and
production draft settings for the candidate and upstream matched control.
Use [the probe](measure-rm400-sfnx-onepass.py) and [comparator](compare-rm400-sfnx-onepass.py)
for each pair; supply `--upstream-repeat` and `--candidate-repeat`
for the bracket. Use `--case 16K --metric decode_tok_s`.

The combined candidate uses segmented compact rollback, shorter Q4_K
gate/up load groups and four CPU workers for first-pass RAM preparation.
Prompt chunk allocation stayed at 4,096 rows. Fast router, mid-only
dispatch, MTP last-row and paired sparse scoring stayed off. Each start
got a full warm-up before one recorded pass; the order was upstream,
candidate, candidate, upstream. The results below summarize the two hot
passes per build, not a replacement one-pass production row.

| Actual prompt | Decode upstream → candidate | Prefill upstream → candidate | Client TTFT upstream → candidate |
|---:|---:|---:|---:|
| 512 | 177.50 → 182.85 tok/s (+3.01%) | 1,171.10 → 1,172.60 tok/s | 0.449229 → 0.448441 s |
| 4,090 | 150.30 → 156.75 tok/s (+4.29%) | 2,974.65 → 2,998.65 tok/s | 1.390016 → 1.378993 s |
| 16,376 | 162.25 → 169.60 tok/s (+4.53%) | 3,922.95 → 3,960.75 tok/s | 4.198325 → 4.158519 s |

The 16K target improved by 4.50% and 4.56% in the individual pairs, with
no headline regression in either pair. Response hashes matched for all
recorded and warm-up requests, with 128 output tokens and no reused
prompt tokens. This passes the performance screen; serving still
requires the separate correctness, batch, vision, thermal and routed
checks.
