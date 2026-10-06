# V271 continual crossed-factor results

V270 established early transfer when the source covered the two visible factors.
V271 keeps that source selector frozen and sends each unseen target corner through
`A → B → A_prime`. `B` changes only `RECOVERY_RETRY.DELIVERY` from its A value
to `1/20`; `A_prime` restores the A law exactly. The phase marker is evaluator
metadata and is never a learner feature.

The source uses five L-shaped contexts, 48 fit rows and 16 held-out suffix rows
per operator/context, with four fixed seeds. Each target phase has 48 fit rows
and 16 held-out suffix rows per operator. The source selector is run once per
seed, then each target corner is evaluated against the same immutable source
snapshot. `RESET` uses only
the current phase prefix, `FROZEN_FACTOR` keeps the source posterior unchanged,
and `CONTINUAL_FACTOR` adds completed phase fit rows in chronological order.

| phase / prefix | RESET | FROZEN_FACTOR | CONTINUAL_FACTOR |
|---|---:|---:|---:|
| A / 0 | 6.00 / 16.2145 | 11.00 / 1.08025 | 11.00 / 1.08025 |
| A / 4 | 11.00 / 0.972375 | 11.00 / 1.08025 | **12.00 / 0** |
| B / 0 | 6.00 / 15.16 | 8.00 / 2.75175 | **9.00 / 1.1495** |
| B / 48 | 11.75 / 0.1625 | 8.00 / 2.75175 | **9.75 / 0.501125** |
| A_prime / 0 | 6.00 / 16.2145 | 11.00 / 1.08025 | **11.25 / 0.320625** |
| A_prime / 32 | 11.75 / 0.030875 | 11.00 / 1.08025 | **12.00 / 0** |

Each cell is mean policy-correct queries / mean exact regret over four seeds,
four target corners, and three fixed queries. Continual updating lowers B
regret relative to the frozen source from `2.75175` to `0.501125` by prefix 48.
After the law is restored, it starts with lower regret than the frozen source
(`0.320625` versus `1.08025`) and reaches zero by prefix 32. This is evidence
for both adaptation and retention on this synthetic crossed flow. RESET catches
up after enough local rows, so the result is an amortized transfer diagnostic,
not a total-observation or deployment-cost claim.

The learned source selector chose the intended factor for all three operators
in three seeds; seed `270404` selected both fields for `SHORT_PASS`, as in V270.
The selection was not corrected after seeing B or A_prime. Source cost is 720
fit plus 240 held-out observations per seed; target costs are reported
separately. The held-out suffixes are generated and excluded from fitting, but
this run does not use them as a separate validation score.

The run exited 0 with zero-byte stderr; the focused V271 suite passed 10/10.
Raw evidence is in
[`summary.json`](publication/v327_snapshot/crossed_factor_continual_v271/summary.json.gz).

This is a development diagnostic, not a rerun of the original Gate. The Gate
remains FAIL and U006 remains unstarted.

Protocol: [`CROSSED_FACTOR_CONTINUAL_V271.md`](../specs/CROSSED_FACTOR_CONTINUAL_V271.md).
Implementation: [`crossed_factor_continual_v271.py`](../src/acfqp/science/crossed_factor_continual_v271.py).
