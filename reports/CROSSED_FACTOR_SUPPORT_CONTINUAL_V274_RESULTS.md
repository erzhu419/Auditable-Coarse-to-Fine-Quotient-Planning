# V274 continual successor-support results

V274 keeps the V270 factor selector, visible context, query bank, and action
availability fixed. B changes only the support of `RECOVERY_RETRY`: it adds
`DELAYED` with probability `1/5`, scales the old delivery/lost probabilities by
`4/5`, and assigns `DELAYED` a fixed timeout-failure cost of `2`. A_prime
restores the original two-category law.

| phase / prefix | RESET_DYNAMIC | FROZEN_STATIC | CONTINUAL_FACTOR_EXPANDING | LEGACY_COERCE |
|---|---:|---:|---:|---:|
| A / 0 | 7.25 / 5.6845 | 11.00 / 1.08025 | 11.00 / 1.08025 | 11.00 / 1.08025 |
| B / 0 | 9.25 / 1.26055 | 10.00 / 1.25915 | **11.00 / 0.0133** | 11.00 / 0.0133 |
| B / 4 | 9.50 / 1.032225 | 2.75 / 0.003325 + 9 abstains | **11.00 / 0.0133** | 11.00 / 0.0133 |
| B / 48 | 10.00 / 0.0912 | 0 / 0 + 12 abstains | **11.00 / 0.0133** | 11.00 / 0.0133 |
| A_prime / 0 | 11.00 / 0.4275 | 11.00 / 1.08025 | **12.00 / 0** | 12.00 / 0 |
| A_prime / 48 | 11.00 / 0.4275 | 11.00 / 1.08025 | **12.00 / 0** | 12.00 / 0 |

Cells are mean policy-correct queries / mean exact regret over four seeds, four
target corners, and three queries. `FROZEN_STATIC` abstains after observing the
new category: its B prefix-4 and prefix-48 abstention counts are shown instead
of treating missing decisions as ordinary regret. `LEGACY_COERCE` maps every
observed `DELAYED` row to `LOST`; it records the coercions separately and
retains a small B regret, so the support diagnostic cannot be mistaken for a
generic parameter update.

The expanding arm discovers `DELAYED` only after it appears in a fit prefix and
keeps the expanded support through A_prime. It reaches 11/12 at B prefix 0 and
maintains 11/12 through B; after the old law returns it reaches 12/12. RESET
eventually improves with local rows, while the static arm correctly stops using
the old support once it is contradicted. This is evidence for support discovery
and applicability handling, not a claim of lower total acquisition cost or a
complete new world-model learner.

The held-out support-presence check agrees with the fit trace: the expanding
arm contains `DELAYED` in its model support for 3/4 target corners at B prefix
4, 3.75/4 at prefix 8, and 4/4 at prefix 48; static and coercing arms remain
at 0/4. At B prefix 0, 13.5 held-out `DELAYED` rows per seed remain outside
the model support on average. This is a support-presence check, not a complete
category-prediction score.

The source cost is 720 fit plus 240 held-out observations per seed. Each target
phase acquires 576 fit plus 192 held-out observations per seed (1,728 fit and
576 held-out across A, B, and A_prime); all three operators, including B's
expanded retry stream, are acquired. The final metadata run exited 0
with zero-byte stderr; the focused V274 suite passed 6/6.
Raw evidence is in
[`summary_final_v4.json`](publication/v327_snapshot/crossed_factor_support_continual_v274/summary_final_v4.json.gz).

The final receipt supersedes the earlier V274 raw attempts: an audit corrected
RESET to exclude source/history rows, prevented prior audit suffixes from
expanding support, and included committed B coercions in the ledger.

This is an exploratory support-expansion diagnostic, not a rerun of the
original Gate. The Gate remains FAIL and U006 remains unstarted.

Protocol: [`CROSSED_FACTOR_SUPPORT_CONTINUAL_V274.md`](../specs/CROSSED_FACTOR_SUPPORT_CONTINUAL_V274.md).
Implementation: [`crossed_factor_support_continual_v274.py`](../src/acfqp/science/crossed_factor_support_continual_v274.py).
