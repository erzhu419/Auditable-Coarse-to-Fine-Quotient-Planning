# V272 continual query-shift results

V272 keeps V271's dynamics, source selector, factor projections, stream-generation
rule, seeds, and arms fixed. A/B/A_prime use independently seeded streams from
the same generator law. Only the B-phase `risk` query changes from `(1,4,4)` to `(1,1,4)`;
A_prime restores `(1,4,4)`. Thus this tests re-planning under a preference
change without changing the learned consequence law.

| phase / prefix | RESET | FROZEN_FACTOR | CONTINUAL_FACTOR |
|---|---:|---:|---:|
| A / 0 | 6.00 / 16.2145 | 11.00 / 1.08025 | 11.00 / 1.08025 |
| B / 0 | 8.00 / 4.401 | **10.25 / 0.908875** | **11.25 / 0.007125** |
| B / 48 | 11.25 / 0.07125 | **10.25 / 0.908875** | **11.25 / 0.07125** |
| A_prime / 0 | 6.00 / 16.2145 | 11.00 / 1.08025 | **12.00 / 0** |
| A_prime / 48 | 12.00 / 0 | 11.00 / 1.08025 | **12.00 / 0** |

Each cell is mean policy-correct queries / mean exact regret over four seeds,
four target corners, and three queries. The frozen factor model receives no
target rows, yet its B risk action changes with the query bank and its A_prime
bank restores the original action. This is the key result: query adaptation
does not require relearning the consequence representation. Continual updating
starts slightly better on B because it has the completed A fit, but its later
rows do not provide a systematic benefit over the frozen model for this query
only change.

The source selector and source cost are unchanged from V271: 720 fit and 240
held-out observations per seed. Target suffixes are generated and excluded
from fitting, but are not used as a separate validation score. RESET is a local
adaptation control, not a total-cost comparison.

The formal run exited 0 with zero-byte stderr; the focused V272 suite passed
6/6. Raw evidence is in
[`summary.json`](publication/v327_snapshot/crossed_factor_query_continual_v272/summary.json.gz).

This is an exploratory query-adaptation diagnostic, not a rerun of the original
Gate. The Gate remains FAIL and U006 remains unstarted.

Protocol: [`CROSSED_FACTOR_QUERY_CONTINUAL_V272.md`](../specs/CROSSED_FACTOR_QUERY_CONTINUAL_V272.md).
Implementation: [`crossed_factor_query_continual_v272.py`](../src/acfqp/science/crossed_factor_query_continual_v272.py).
