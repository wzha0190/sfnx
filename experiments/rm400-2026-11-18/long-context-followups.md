# RM400 long-context follow-up screens

These results are lab wall times, not hot API promotion measurements. Use
the deployed settings in each lab stack, `ARCH=70 FNX_NCARD=3`, and
[restart the worker for every flag profile](lab-worker-flags.md).

### Long-context sparse selection and expert copy (2026-11-19)

The short and long traces isolated two long-context costs. Switching the
selector to four padded integer histograms to spread inter-warp atomic
contention gave no material gain. Fresh workers also retested paired sparse
scoring independently; unlike the earlier held-worker result, the startup
flags were verified. Each variant matched the 48K verification fingerprint
and the `long64` 200-step teacher-forced output byte-for-byte.

| Workload | First/last control | Striped histogram | Paired sparse scores |
|---|---:|---:|---:|
| Eight verification rows, 48K | 20.483 / 20.504 ms | 20.502 ms | 20.452 ms |
| Six lanes, 48K each | 20.711 / 20.695 ms | 20.705 ms | 20.673 ms |

Changing only decode cache-copy launch size from 160 blocks to 80 or 320
also did not help. All profiles used the same allocation and lent
991/991/1,156 slots/card at 48K × six lanes. Short `code1` logits matched;
this is not a dedicated correctness test under lending.

| Six-lane workload | 160-block control, first/last | 80 blocks | 320 blocks |
|---|---:|---:|---:|
| 4K per lane | 19.476 / 19.488 ms | 19.464 ms | 19.499 ms |
| 48K per lane | 20.720 / 20.715 ms | 20.734 ms | 20.766 ms |

These rule out the tested geometry changes, not better placement or a
copy-path redesign. Both sparse flags and the copy override remain off.
The fused dense tile and Q5_1 unpack-once represent the positive, exact
increment seen so far; that gain is still too small for a cutover.


### Direct expert reads and held-out expert placement (2026-11-19)

Reading cold experts directly from their pinned host copies, instead of
staging them in GPU memory, cut the six-lane 4K step from a 19.576/19.600
ms bracket to 19.261 ms. At 48K it went the other way: 21.588 ms versus
20.775/20.829 ms. Eight-row solo verification also regressed. Greedy
fingerprints matched across configurations. The experiment is rejected;
an unconditional direct-read flag would trade away the long workload.

The two small exact candidates (Q5_1 unpack-once and the fused dense
tile) together measured 17.061 ms versus 17.180/17.178 at six rows,
19.615 ms versus 19.871/19.872 at eight rows, and 19.468/20.735 ms
at six 4K/48K lanes. This does not meet the 3% target.

The placement experiment blended 75% stock prior with 25% from two
equal-weight synthetic training tallies (`long64`, `long2`), separately
normalizing prompt and decode. The 4K and 48K six-lane evaluation used
`long164` starting at token 80,000, with matching greedy sequences:

| Held-out case | First/last control | Blended ranking |
|---|---:|---:|
| Six lanes, 4K each | 19.153 / 19.181 ms | 19.129 ms |
| Six lanes, 48K each | 20.421 / 20.436 ms | 20.358 ms |

The 0.20%/0.35% reductions did not justify changing the production
profile. Placement affects only which expert pages are resident, not
the model's routing. Next, test reducing work on the many layers with
no cache misses before making a larger change to the device or CPU
staging path; keep the measured short/long trade-off as the counterexample.


### Expert residency and short-context headroom (2026-11-19)

The pinned loader defaults to the arena and 3 GiB of cold experts in
host RAM; `FNX_EXPERT_RAM_GIB=0` asks for full residency but does not
guarantee it. The lab still put 303 of 24,576 experts (0.9 GiB) in RAM
because VRAM was short. Its initial K/V pool fell from 211,008 to 96,960
positions. Against the 3 GiB bracket, the zero-GiB setting also slowed
eight-row verification. All solo and six-lane greedy fingerprints matched.

| Workload | 3 GiB control, first/last | Zero GiB requested | Zero GiB plus Q5_1 and fused Q8 |
|---|---:|---:|---:|
| Six verification rows, 4K | 17.173 / 17.185 ms | 17.099 ms | 16.945 ms |
| Eight verification rows, 4K | 19.878 / 19.882 ms | 19.933 ms | 19.642 ms |
| Six lanes, 4K each | 19.605 / 19.577 ms | 19.465 ms | 19.378 ms |
| Six lanes, 48K each | 20.840 / 20.833 ms | 20.773 ms | 20.685 ms |

The combined settings reduced the six-row median by 1.36%, less than
the promotion threshold, while sacrificing initial K/V capacity. Leave
production at the pinned defaults. See the separate [all-hit planner experiment](cache-all-hit.md),
which kept the 3 GiB placement policy.


### CPU speculative-lookup scan (2026-11-19)

An optional AVX2 scan on the EPYC 7443 finds the same latest matching
three-token suffix as the scalar search. It preserves the rule that a
draft-token mismatch at that occurrence does not fall back to an older
one. Both settings passed 23,040 comparisons per process, including
separate latest-match and image-token cutoff checks.

At 16K, 48K and 256K tokens, a worst-case miss fell from about
8.22/24.66/131.76 µs to 1.32/3.93/21.39 µs. Nearby matches and the
4K test were unchanged within measurement noise; 4K remains below the
SIMD dispatch cutoff. Even the longest tested miss saves about 0.11 ms
of CPU work per lookup, not a measured end-to-end gain. This alone does
not justify a production interruption; keep it as a long-context
candidate. No CUDA or service stop was needed for the CPU screen.

## Reproduction

Keep the three production RM400 flags on. Use the stock expert ranking and
3 GiB of cold experts in RAM unless testing placement or residency.
The patches apply with `git apply --recount --unidiff-zero`.

- Sparse scoring and selection: apply the striped-histogram patch; test
  `FNX_RM400_QSA_STRIPED_HIST=1` and `FNX_RM400_QSA_PAIRED=1` separately
  (the paired-scores patch must be included). Run `bench ref/long64.bin 8 128`
  at `FNX_BENCH_CTX=49152` and `bench_step ref/long64.bin 6 64 49152 step`.
- Copy grid: apply the copy-grid patch and compare
  `FNX_RM400_EXPERT_COPY_GRID=160/80/320/160`. Run `bench_step` at
  4096 and 49152 tokens on six lanes. Only the decode copy grid changes.
- Direct read: apply the direct-cold-experts patch and compare
  `FNX_RM400_DIRECT_COLD_EXPERTS=0/1`; use
  `FNX_RM400_BATCH_FINGERPRINT=1` for greedy batch fingerprints. Retain
  the stock placement and compare both 4K and 48K six-lane steps.
- Placement: apply shifted-prompts and export-expert-tallies after the
  direct-read patch (leave direct reads off). Generate distinct tally
  files with `FNX_ROUTE_COUNT=1` and `FNX_ROUTE_FILE` from 8192-token
  six-lane steps on `long64` and `long2`. Blend with the stock table using
  `merge-rm400-sfnx-route-tallies.py`; turn off tallying, set
  `FNX_RM400_BENCH_TOKEN_OFFSET=80000`, and compare the two tables using
  `FNX_EXPERT_PROFILE` on `long164` at 4096 and 49152 tokens per lane.
- Residency: compare `FNX_EXPERT_RAM_GIB=3/0/0/3`; on the second zero-GiB
  run enable `FNX_RM400_Q5_DOWN_UNPACK_ONCE=1` and `FNX_RM400_Q8S_AB_TILE2=1`
  with their patches. Measure `bench ref/long64.bin T 200` at 4K for T=6/8,
  and `bench_step ref/long164.bin 6 64 C step` at C=4096/49152.
- Lookup: apply the AVX2 patch and run
  `python3 experiments/rm400-2026-11-18/check-sfnx-lookup-avx2.py < src/session.cpp`
  on an AVX2-capable CPU. No model, CUDA context or service interruption needed.

## Exact per-run lab source and timings

For a clean reproduction, check out upstream
`980873394a532ca0f187aae034ed4819bb205921`, then `git apply` the one full
stack below for the chosen run. Do not stack the files in this table.
Match the flag profile above and the recorded fixtures; the patches live
in the experiment directory, not in the default build. They include
prior dormant prototypes that were present in the measured binary.

| Lab run | Full source SHA-256 | Extracted timing lines |
|---|---|---|
| [long-qsa-stack.patch](long-qsa-stack.patch) | `6f6fa36dac0ec1e782997dd593dcfe547e145fa59346c0218889ed4324e5a5aa` | [long-qsa-results.txt](long-qsa-results.txt) |
| [decode-copy-grid-stack.patch](decode-copy-grid-stack.patch) | `76433740167bf21dc80cb01d52e7fb00046b1a289ff37ae8049187efd2163e2e` | [decode-copy-grid-results.txt](decode-copy-grid-results.txt) |
| [cold-expert-read-stack.patch](cold-expert-read-stack.patch) | `6149321087ff4e0f15c4a2fceb203eaf7d53c0c130d448ddad22fda2024b4260` | [cold-expert-read-results.txt](cold-expert-read-results.txt) |
| [expert-placement-stack.patch](expert-placement-stack.patch) | `6a27236d70246e1dc3f5b9e7ee19e220163a2bf20676c85664f950d5b567da00` | [expert-placement-results.txt](expert-placement-results.txt) |
| [cache-residency-stack.patch](cache-residency-stack.patch) | `6a27236d70246e1dc3f5b9e7ee19e220163a2bf20676c85664f950d5b567da00` | [cache-residency-results.txt](cache-residency-results.txt) |
