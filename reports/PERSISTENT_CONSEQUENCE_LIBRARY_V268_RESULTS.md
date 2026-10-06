# V268 paired two-step consequence results

V268 changed the consequence representation and its finite-sample posterior.
Each fit prefix paired
`DETOUR_PASS[i]` with `RECOVERY_RETRY[i]` and learned four joint fragment
categories. The `LOCKED_COMPOSED` arm used exactly the V266 marginal
action-agreement module IDs and assignment reasons; this keeps the allocator
fixed while testing the representation. RESET and the 48-fit/16-audit budget
were unchanged.

| arm | policy-correct counts | mean correct | set agreement | mean exact regret |
|---|---:|---:|---:|---:|
| `RESET_MARGINAL` | 12, 12, 11, 11 | 11.5/12 | 95.83% | 0.105 |
| `RESET_COMPOSED` | 10, 11, 10, 10 | 10.25/12 | 85.42% | 0.491625 |
| `LOCKED_MARGINAL` | 12, 12, 11, 11 | 11.5/12 | 95.83% | 0.105 |
| `LOCKED_COMPOSED` | 11, 10, 10, 10 | 10.25/12 | 85.42% | 0.474875 |

The composed arm loses 1.25 correct query decisions per seed and increases
mean exact regret by about 0.37 while keeping every module assignment exactly
equal to the marginal arm. The four pair categories conserve all 48 fit and
16 audit indices per operator. Assignment is held fixed, but the comparison is
not estimator-neutral: the four-category Dirichlet prior differs from the
marginal priors, and retry observations on non-recovery indices do not enter
the joint table.

This negative result has a structural explanation. V205 generates
`DETOUR_PASS` and `RECOVERY_RETRY` from independent categorical laws under the
same weather context. The paired representation has no additional transferable
signal; it only spreads the finite evidence over a four-category joint table
and raises variance. The fixed-index pairing is a declared diagnostic and is
not a claim of conditional sampling.

The joint-outcome route is closed. A future factorization experiment must
predeclare which context factors are shared and which vary; the current weather
laws do not establish a stable shared operator law. Further pair-index choices
or joint-prior tuning would not address the bottleneck.

The run exited 0 with zero-byte stderr; the focused V263--V268 suite passed
21/21 tests. Raw evidence is in
[`summary_final.json`](persistent_consequence_v268/summary_final.json); the
initial run remains in `summary.json`.

V268 is exploratory only. The original Gate remains FAIL and U006 remains
unstarted.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V268.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V268.md).
Implementation: [`persistent_consequence_library_v268.py`](../src/acfqp/science/persistent_consequence_library_v268.py).
