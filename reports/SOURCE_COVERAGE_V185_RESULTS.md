# V185 — SOURCE consequence coverage

**Coverage improves, but transfer gains remain unstable.** SOURCE grows from 47 to 143 roots in 36 design groups; the unchanged SOURCE-only procedure again selects λ=0.1. Evaluate all old/new models on another 96 unopened H3 boards.

| Same learner, expanded−original SOURCE | Mean utility difference |
| --- | ---: |
| RIDGE | +0.019789 |
| LAYOUT | −0.030059 |
| SHARED | −0.013105 |

RIDGE improves in two replicas and worsens in two; one root contributes 78.9% of positive gains. Unknown target tokens fall from 12.45% to 1.62%, yet unregularized LAYOUT still interpolates training labels (loss 9.89e−28) and degrades transfer. Expanded RIDGE exceeds expanded SHARED by 0.007859, with three replicas negative; it remains 0.005246 below OLD_SHARED, the strongest learned comparator. Fifty RIDGE target regret roots remain.

**Next:** fix the 143-root SOURCE, representation and λ=0.1; test optimal-versus-suboptimal action ranking with a one-sided squared hinge loss and the exact utility gap as its margin. Preserve full R/F/S evaluation on another unopened cohort. Scalar utility least squares alone would produce the present ridge utility coefficients. Further coverage expansion is not supported as a sufficient solution.

Thirteen synthetic tests and 408/408 independent checks pass; 76/76 source and 5/5 input comparisons match. Main/audit run once (49.02 s / 7.47 s), stderr 0. There are 192 new exact kernels/plans, 492224 concrete observations and 868684 transition outcomes; 3 main SVDs, 14 coefficient filters and 1 six-column solve produce 15 predictors. Audit independently solves 14 ridge systems and 1 SHARED system, reusing the settled physics backend. Two pre-run test collection failures from a missing closing parenthesis are retained; corrected analyzer tests pass before any real data generation.

[Protocol](../specs/SOURCE_COVERAGE_V185.md) · [Summary](controlled_predictive_source_coverage_v185/summary.json) · [Audit](publication/v327_snapshot/controlled_predictive_source_coverage_v185/analysis.json.gz) · [Ledger](v185_runtime_tmp/stage_checks.json)

**Limitations:** SOURCE size and composition both change; finite synthetic H3 roots with a fixed teacher do not establish general strategic learning, full episodes or sampling efficiency. Keep H2; U005 FAIL, U006 unstarted.
