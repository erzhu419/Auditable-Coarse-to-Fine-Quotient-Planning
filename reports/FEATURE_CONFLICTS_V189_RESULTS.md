# V189 — Six-feature information conflicts

Under `first_reward + g(six_features)`, **20 of LINEAR's 44 regret roots have unavoidable alias loss**: mean **0.022345**, or **37.66%** of total regret 0.059332. Remaining regret is 0.036987.

At `v188_target_r01_20`, DOWN and LEFT share **(0,3,1,0,0,0)**. First rewards **1/128 vs 1/512** force DOWN above LEFT for any shared g. Their full R/F/S are **(0.093791,0,0) vs (0.676786,0,2/3)**. The best accessible representative gives utility 0.096011 versus oracle 1.343453.

An exact five-root certificate gives common margin **≤−17/160**: arbitrary shared g cannot attain all representative-optimal rankings. Among 44 errors, SOURCE covers every tuple on **34**, every directed pair on **19**, every reward threshold on **9**.

**Next:** retain tile ranks, row/column order and merge blockers in a shared relation representation. Use TARGET counterexamples for development; train on SOURCE, freeze, then test a fresh cohort. Avoid another exact rank/position dictionary.

**12 tests, 27/27 audit, 39/39 source and 5/5 input checks pass**; main/audit once, 0.79 s/0.13 s, stderr 0. One LP and exact balance; zero new fits, labels or samples.

**Limitations:** Exposed H3 roots, fixed teacher. The cycle does not quantify minimum mean loss; remaining errors are not established as learnable. General strategy remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/FEATURE_CONFLICTS_V189.md) · [Summary and certificate explanation](controlled_predictive_feature_conflicts_v189/summary.json) · [Diagnostics](publication/v327_snapshot/controlled_predictive_feature_conflicts_v189/diagnostics.json.gz) · [Audit](controlled_predictive_feature_conflicts_v189/analysis.json) · [Ledger](v189_runtime_tmp/stage_checks.json)
