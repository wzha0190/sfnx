# Validating lab worker flags — 2026-11-19

The upstream lab reloads `build/libfnx_lab.so` after an environment change.
`readelf -Ws` confirmed GNU-unique symbols in the SM70 library. glibc can
retain such a library across `dlclose`, retaining any initialized function
static. That invalidates attribution for an in-process A/B of the fast
router, mid-prefill dispatcher, paired sparse scoring, alternate ring
launch sizes, the Q4_K twin, and batched projection fusion. Earlier tests
with separate processes and the matched API comparison are unaffected.

Retest with the same model holder: `tools/lab.sh cmd "set VAR=value"`,
`tools/lab.sh stop`, then `tools/lab.sh cmd reload`. Verify the new
`fnx-lab.service` main PID and its `VAR=value` entry in `/proc/PID/environ`
before measuring. Keep only the recorded pass after the warm-up.
