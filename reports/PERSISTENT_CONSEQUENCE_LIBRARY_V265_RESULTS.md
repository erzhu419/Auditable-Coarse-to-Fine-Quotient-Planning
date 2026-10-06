# V265 fair-prefix applicability results

V263/V264 comparisons were found invalid: their GLOBAL arms received 64
observations per operator while RESET received 48, and their LIBRARY arms
committed the validation suffix. V265 reimplemented fair controls: every arm
gets the same first 48 observations per operator and the final 16 remain
audit-only.

| arm | policy-correct counts across four lifecycles | mean correct | mean exact regret |
|---|---:|---:|---:|
| `RESET` | 12, 12, 11, 11 | 11.5/12 | 0.105 |
| `GLOBAL` | 10, 10, 9, 9 | 9.5/12 | 1.9885 |
| `LEGACY_LIBRARY` | 12, 10, 11, 11 | 11.0/12 | 0.350875 |
| `GUARDED_LIBRARY` | **12, 12, 11, 11** | **11.5/12** | **0.105** |

The guarded arm preserves the reset result while retaining useful structure:
it abstains and creates a local module when applicability is uncertain, reuses
the prior normal module at every `A_prime`, and avoids the legacy library's
wrong forced transfers. It does not yet improve over rebuilding; the main
bottleneck is now identifying when a consequence module is safe to reuse, not
representing query-dependent consequences once the correct module is known.

The run used four fixed fresh seeds and 3,072 local categorical draws. It
exited 0 with zero-byte stderr. The focused V263/V265 regression suite passed
7/7 tests. V263/V264 outputs and the first V264 serializer failure remain
retained; their unfair comparison is explicitly marked in their reports and
specifications.

The next method change should replace the Brier threshold with a frozen
query-action agreement rule: reuse a module only when all declared queries
select the same actions as the current local model; otherwise abstain. This
will test applicability in the decision space directly, without adding
sampling or tuning the current threshold. V265 itself is development evidence,
not a scientific Gate, confidence certificate, or U006 authorization.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V265.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V265.md).
Machine-readable output: [`summary.json`](persistent_consequence_v265/summary.json).
