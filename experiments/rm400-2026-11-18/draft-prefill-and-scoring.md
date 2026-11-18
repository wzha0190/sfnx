# Draft head, prefill chunk, and paired sparse scoring — RM400

This held-model sweep used `FNX_RM400_COMPACT_SNAPSHOTS=1` with the
segmented rollback bundle; see [segmented-rollback.md](segmented-rollback.md).
The draft-head path used `decode 256 6 15 edit1,code1,prose2`;
pre-fill used `read 512 4096 16384` with a warm-up and recorded pass;
sparse scoring used `bench ref/long64.bin 6 200` at 4K and 32K context.
`FNX_RM400_MTP_LAST_ROW`, `FNX_RM400_QSA_PAIRED`, and global
`FNX_PF_ROWS` changes were not selected. No production change.

Projecting only the last MTP draft row preserved emitted token fingerprints
and draft counts throughout a 0/1/1/0 sweep. Gains did not reproduce across
greedy edit, greedy new code or filtered sampled prose; the largest change
of the on/off means was +0.18% on prose. Keep the default.

| Prefill chunk | 512 tokens | 4,096 tokens | 16,384 tokens |
|---|---:|---:|---:|
| 4,096, control bracket | 2,014 / 1,687 tok/s | 3,233 / 3,082 tok/s | 4,005 / 3,981 tok/s |
| 8,192 | 1,683 tok/s | 3,075 tok/s | 4,206 tok/s |
| 2,048 | 1,692 tok/s | 3,494 tok/s | 3,526 tok/s |

These are held-model prompt reads. The larger chunk helped at 16K but
did not match the better control at 4K; the smaller chunk helped at 4K but
lost at 16K. Neither was selected. Paired sparse scoring measured
17.368 → 17.258 ms at a 4K starting context in a single comparison; at 32K
it measured 17.632 / 17.678 ms against 17.681 / 17.636 ms without pairing.
Fingerprints matched, but the bracket did not establish a reliable
long-context speedup. The direct API candidate leaves these toggles off.

