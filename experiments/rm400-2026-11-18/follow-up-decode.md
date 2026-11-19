# Further decode screens against the deployed RM400 build

Apply [short-gate-up-stack.patch](short-gate-up-stack.patch) to the pinned
upstream base, then apply the relevant patch below with `git apply --recount
--unidiff-zero`. Build `make lab ARCH=70 FNX_NCARD=3`. Keep the three flags
in [production-acceptance.md](production-acceptance.md) enabled in each
profile. Toggle only the experiment under test, in 0/1/1/0 order, with a
fresh worker and the same model holder. Use `bench ref/long64.bin T 200`
with `FNX_BENCH_CTX=4096`, `FNX_MAX_CTX=262144`, and the `code1` forced
logit comparison at each width.

- [FNX_RM400_HC_WARP_OUT](sfnx-hc-warp-output-2026-11-19.patch)
- [FNX_RM400_Q4K_SINGLE_JOB](sfnx-q4k-single-job-2026-11-19.patch)
- [FNX_RM400_Q5_DOWN_UNPACK_ONCE](sfnx-q5-down-unpack-once-2026-11-19.patch)

Three independent prototypes were measured against the deployed optimization
flags, rather than against stock upstream. Each used fresh workers in
A/B/B/A order on one model holder, a 4,096-token starting context, and 199
recorded verification windows after graph capture. Lower time is better.

| Experiment | Rows | Production-control wall medians | Trial wall medians | Result |
|---|---:|---:|---:|---|
| Warp-local hyper-connection output | 6 | 17.145 / 17.118 ms | 17.150 / 17.142 ms | No gain; logits and top-1 changed at 4/6/8 rows |
| Q4_K single-token expert fast path | 6 | 17.138 / 17.122 ms | 17.214 / 17.194 ms | 0.43% slower; exact at 4/6/7/8 rows |
| Q5_1 expert down-projection unpack once | 4 | 14.621 / 14.612 ms | 14.588 / 14.586 ms | 0.20% lower; exact |
| Q5_1 expert down-projection unpack once | 6 | 17.143 / 17.133 ms | 17.063 / 17.059 ms | 0.45% lower; exact |
| Q5_1 expert down-projection unpack once | 8 | 19.904 / 19.870 ms | 19.804 / 19.775 ms | 0.49% lower; exact |

Warp-local output moved four normalization/mixing operations onto one warp per
token and removed two CTA barriers, but did not help even before the correctness
failure. The Q4_K fast path removed the token loop for single-token jobs and
cut six-row register use from 74 to 64, without improving wall time. The
Q5_1 candidate reuses decoded weight nibbles across a job's tokens, without
increasing register allocation or rewriting the weight format. Its six
teacher-forced logit files and the verification fingerprints matched. It
is a candidate for combination, not an API result or a new deployment.

The stronger next diagnostic is a **wide-window and six-lane trace of the
deployed engine** at short and long context. Check whether repeated expert
weight reads or transferring lent experts over PCIe actually dominate each
case before redesigning jobs or expert placement. At the current six-row
17.14 ms lab baseline, a 3% throughput gain needs about 0.50 ms less wall
time. The unpack change saves about 0.08 ms; the next change needs roughly
another 0.42 ms on that workload, and an API bracket still decides promotion.
For placement, use upstream's `FNX_ROUTE_COUNT`, `FNX_ROUTE_TRACE` and
`tools/route_eval.py` on synthetic lab requests; validate on held-out workloads.
If the trace shows few or no lent-expert transfers, changing placement cannot
be the short-context win. No production settings changed.

