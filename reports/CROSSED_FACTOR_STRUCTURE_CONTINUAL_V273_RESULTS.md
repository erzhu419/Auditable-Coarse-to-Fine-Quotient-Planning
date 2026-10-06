# V273 continual action-support structure results

V273 keeps the V270 generator law, query weights, visible factors, source
selector, and stream-generation rule fixed. In A and A_prime, recovery allows
`RETURN` and `RETRY`; B exposes only `RETURN`. Because RETRY is unavailable in
B, its hypothetical outcome rows are not acquired or fitted.

| phase / prefix | RESET_AWARE | FROZEN_FACTOR_AWARE | CONTINUAL_FACTOR_AWARE | LEGACY_UNMASKED invalid |
|---|---:|---:|---:|---:|
| A / 0 | 6.00 / 16.2145 | 11.00 / 1.08025 | 11.00 / 1.08025 | 0.00 |
| B / 0 | 6.00 / 15.16 | 10.50 / 1.655 | **12.00 / 0** | **3.75** |
| B / 48 | 11.75 / 0.1625 | 10.50 / 1.655 | **12.00 / 0** | **3.75** |
| A_prime / 0 | 6.00 / 16.2145 | 11.00 / 1.08025 | **12.00 / 0** | 0.00 |
| A_prime / 48 | 12.00 / 0 | 11.00 / 1.08025 | **12.00 / 0** | 0.00 |

Cells are mean policy-correct queries / mean exact regret over four seeds, four
target corners, and three queries. The final column is mean invalid actions per
seed across the 12 query decisions; invalid rows are excluded from ordinary
regret. The aware arms always emit legal actions. The legacy arm continues to
select RETRY in B for some queries, producing 3.75 invalid decisions per seed.

The result is a structural applicability result: the action mask prevents an
old plan from executing an unavailable branch, and the old support is restored
in A_prime. Continual updating is perfect here because completed A observations
support the legal B decision; this is not evidence of learning a new successor
category or of lower total acquisition cost. B acquires only two operators per
prefix, while A and A_prime acquire all three.

The final metadata run exited 0 with zero-byte stderr; the focused V273 suite
passed 6/6. Raw evidence is in
[`summary_final.json`](publication/v327_snapshot/crossed_factor_structure_continual_v273/summary_final.json.gz).

This is an exploratory structure diagnostic, not a rerun of the original Gate.
The Gate remains FAIL and U006 remains unstarted.

Protocol: [`CROSSED_FACTOR_STRUCTURE_CONTINUAL_V273.md`](../specs/CROSSED_FACTOR_STRUCTURE_CONTINUAL_V273.md).
Implementation: [`crossed_factor_structure_continual_v273.py`](../src/acfqp/science/crossed_factor_structure_continual_v273.py).
