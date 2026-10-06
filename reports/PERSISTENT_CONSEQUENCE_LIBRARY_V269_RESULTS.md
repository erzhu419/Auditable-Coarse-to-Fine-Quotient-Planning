# V269 factorized residual results

V269 kept the V266 action-agreement assignment and tested a fixed hierarchical
estimator. The current context contributes its 48 fit rows as a local
residual. A prior module or global history contributes the frozen doubled-count
baseline `KAPPA=48`, equivalent to 24 categorical pseudo-observations after
normalization; the first context has no baseline and is exactly RESET.
Neither weather nor phase names are visible to the estimator, and the 16-row
audit suffix is never used for fitting.

| arm | policy-correct counts | mean correct | set agreement | mean exact regret |
|---|---:|---:|---:|---:|
| `RESET` | 12, 12, 11, 11 | 11.5/12 | 95.83% | 0.105 |
| `LOCKED_MARGINAL` | 12, 12, 11, 11 | 11.5/12 | 95.83% | 0.105 |
| `GLOBAL_SHRINK` | 11, 12, 10, 10 | 10.75/12 | 89.58% | 0.54425 |
| `FACTORIZED_MODULE` | **12, 12, 11, 11** | **11.5/12** | **95.83%** | **0.105** |

`FACTORIZED_MODULE` is identical to RESET on all four paired streams. Its
module assignments remain the V266 assignments: `A_prime` reuses a prior
module in each stream, while `B` and `C` split locally. The module baseline
therefore supplied no additional decision information at this sample size.
`GLOBAL_SHRINK` is worse, showing that an unconditioned cross-context baseline
can transfer the wrong operator distribution.

This closes the fixed module-conditioned baseline-shrinkage attempt. It does not
prove that hierarchical sharing is impossible: the diagnostic has four phases,
four seeds and only three opaque contexts that can provide a history baseline.
It does show that the current assignment and consequence representation do not
turn this simple shared-baseline rule into a measurable gain. The doubled-count
KAPPA was frozen before scoring and was not tuned after the result.

The next experiment should change the observable task flow or predeclare a
stronger factorization target with an independent long-lived context variable.
Repeatedly adjusting the baseline weight on these same streams is closed.

The run exited 0 with zero-byte stderr; the focused V263--V269 suite passed
25/25 tests. Raw evidence is in
[`summary_final.json`](persistent_consequence_v269/summary_final.json); the
initial run remains in `summary.json`.

V269 is exploratory only. The original Gate remains FAIL and U006 remains
unstarted.

Protocol: [`PERSISTENT_CONSEQUENCE_LIBRARY_V269.md`](../specs/PERSISTENT_CONSEQUENCE_LIBRARY_V269.md).
Implementation: [`persistent_consequence_library_v269.py`](../src/acfqp/science/persistent_consequence_library_v269.py).
