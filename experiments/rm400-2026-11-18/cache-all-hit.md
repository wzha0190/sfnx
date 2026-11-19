# All-hit expert-cache planner

On the stock 3 GiB placement, the opt-in planner checks up to 64 jobs
with one warp vote. If they are all already resident, it writes the
same final CLOCK reference bits and hand position without the temporary
pins or the miss loop. A miss or a larger job count takes the original
path. A fresh-worker control bracket gave:

| Workload | Control, first/last | All-hit planner |
|---|---:|---:|
| Eight verification rows, 4K | 19.996 / 19.991 ms | 19.872 ms |
| Six lanes, 4K each | 19.482 / 19.509 ms | 19.389 ms |
| Six lanes, 48K each | 20.748 / 20.766 ms | 20.653 ms |

The median fell 0.50–0.61% across the three workloads. The solo and batch
greedy fingerprints and the forced `code1` logits matched. Retain the
planner as a candidate for a combined screen; the flag is off in production.

Apply the patch to the deployed source with `git apply --recount --unidiff-zero`.
Test `FNX_RM400_CACHE_ALL_HIT=0/1/0` in fresh workers on the same model and
expert profile, `FNX_EXPERT_RAM_GIB=3`, `FNX_BENCH_CTX=4096`.
Run `bench ref/long64.bin 8 200` and `bench_step ref/long164.bin 6 64 C step`
for C=4096 and 49152; batch fingerprint export uses the direct-cold-experts
experiment's tool additions (leave direct reads off). Compare both logit
files from `logits ref/code1.bin ref/lgr/llama_cuda_code1.lgr 8 OUTPUT.lgr`.
