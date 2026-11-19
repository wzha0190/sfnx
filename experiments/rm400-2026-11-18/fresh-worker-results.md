# Fresh-worker router and prefill comparison (2026-11-19)

One model holder (three PCIe V100s, EPYC 7443) with a fresh worker per
profile. Compact snapshots enabled in each worker; 4,096 rows allocated.
Only the profile's flag was enabled: `FNX_RM400_ROUTER_FAST_WINNER`,
`FNX_RM400_PF_MID_CHUNKS`, or `FNX_RM400_PF_HOST_PARALLEL`. For host
measurements set `FNX_RM400_PF_HOST_TIMING=1` throughout. Use
`bench ref/long64.bin 6 200` (first window excluded) and two passes of
`read 512 4096 16384` per tested prefill profile. For the 4K exactness
screen, use a 4,096-token prefix of `ref/long64.bin` and its next 192
forced tokens in the LGR prompt/continuation format, `FNX_PREFILL=1`, and
a width of six. The resulting LGRs are compared against the control.

All five workers had different PIDs and their startup flags were checked
in `/proc`. The model holder stayed up throughout.

| Profile | 512-token read | 4,096-token read | 16,384-token read |
|---|---:|---:|---:|
| Controls (first / last) | 251 / 252 ms | 1,265 / 1,265 ms | 4,080 / 4,085 ms |
| Mid-only 2,048-row dispatch | 250 ms | 1,130 ms | 4,076 ms |
| Four host workers | 249 ms | 1,249 ms | 4,027 ms |

- **Fast router:** Six-row verification was 17.240 ms versus 17.240 and
  17.241 ms for the controls. `code1` logits and top-1 fingerprints matched;
  no speed gain.
- **Mid-only dispatch:** The 4K read took 10.7% less time, but only 171 of
  192 forced-continuation top-1 predictions matched. Rejected on exactness.
- **Host workers:** First-pass preparation at 512/4K/16K fell from control
  means of 3.24/22.97/86.89 ms to 1.26/6.96/26.67 ms. Total lab-read time
  fell by 1.0%/1.3%/1.4%. The 4K forced-continuation logits were byte
  identical. This is a modest prefill gain, not a decode improvement or
  full model acceptance. No feature was enabled in production.

Apply [fresh-worker-stack.patch](fresh-worker-stack.patch) with `git apply`
on upstream `980873394a532ca0f187aae034ed4819bb205921` and use `make lab`
with `ARCH=70 FNX_NCARD=3`. The aggregate patch replaces applying the
individual patches; do not apply both. The held-worker runs predate the
short gate/up experiment.
