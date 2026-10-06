# V264 fresh-stream replication results

V264 kept the V263 algorithm, Brier threshold `1/2`, phase order, queries and
64/48 fit/validation split fixed, and ran four new lifecycle seeds. This was a
stability check for the persistent consequence-library idea; it was not a
threshold or seed search.

| arm | policy-correct counts by lifecycle | mean correct queries | mean exact regret |
|---|---:|---:|---:|
| `RESET` | 11, 11, 10, 12 | 11.00/12 | 0.14475 |
| `GLOBAL` | 10, 11, 10, 11 | 10.50/12 | 0.29825 |
| `LIBRARY` | 11, 11, 10, 12 | 11.00/12 | 0.19325 |

The library therefore matches the reset arm on policy count and is worse on
the exact-regret measure. Its assignment behavior is also unstable: in the
four fresh streams it splits at `B` in two lifecycles, reuses one global module
through `B` in two, and splits at `C` in three. The one V263 lifecycle that
reached 12/12 is retained as a positive development example, but V264 shows
that it is not a stable effect. The current bottleneck is module applicability
under sparse, noisy consequence evidence, not the ability to serialize or
replan a module.

The final V264 run used 3,072 local categorical draws, exited 0, and produced
zero-byte stderr. A first attempt completed the calculations but failed while
serializing `Fraction` values; its 1,820-byte stderr and partial output are
retained as `summary.failed_serialization.json` and the runtime logs. The
serializer was repaired and the same frozen streams were rerun once.

**Post-run accounting correction:** this replication inherited the V263
comparison bug. `GLOBAL` had the full 64-observation phase available before
scoring, and `LIBRARY` committed validation observations; RESET did not. The
counts above are retained as a negative diagnostic of the implementation, but
they are not a fair arm comparison. V265 re-runs the question with a shared
48-observation scoring prefix and an untouched 16-observation audit suffix.

V264 therefore closes only the claim that the *uncorrected* split runner has a
demonstrated cross-episode gain. The corrected method must make applicability
uncertainty explicit rather than force a noisy module assignment.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V264.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V264.md).
Machine-readable output: [`summary.json`](persistent_consequence_v264/summary.json).
