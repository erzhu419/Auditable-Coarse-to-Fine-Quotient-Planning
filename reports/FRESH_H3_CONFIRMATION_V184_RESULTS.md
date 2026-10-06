# V184 — Fresh H3 confirmation

**V183's regularization advantage does not transfer to this new cohort.** Freeze λ=0.1 and all four SOURCE models, then evaluate 96 new boards in four replicas of 24 using the same exact H3 continuation teacher.

| Fresh cohort comparison | Mean R−F+S difference |
| --- | ---: |
| RIDGE−ONE | +0.116525 |
| RIDGE−LAYOUT | −0.016168 |
| RIDGE−SHARED | −0.052338 |

All four replicas have these same signs. RIDGE closes 44.6% of ONE's oracle headroom; SHARED closes 64.6% and remains the strongest learned comparator. RIDGE has 49 positive-regret roots versus SHARED's 32. Against SHARED, reward falls 0.027005, failure rises 0.014917 and success falls 0.010417. Against ONE, 30 roots improve and 16 worsen; the largest gain contributes 19.9% of positive gains.

**Next:** expand independent SOURCE board/episode consequence coverage with the representation fixed and strength selected only on SOURCE. Use another unopened evaluation cohort; V184 is now exposed and remains a regression record. Additional tuning around the old 24 targets is not justified. Coverage insufficiency is a hypothesis to test, not a cause established by this run.

Fourteen synthetic tests, 211/211 independent checks, 71/71 source and 5/5 input comparisons pass. Main/audit run once (24.71 s / 3.33 s), stderr 0. Main builds 96 kernels/plans, visiting 231426 concrete observations and generating 393140 transition outcomes; independent integration enumerates 57850 outcomes. No new predictors, physical random samples, source games or native updates. Full vectors, fractions, teacher decisions and costs are retained.

[Protocol](../specs/FRESH_H3_CONFIRMATION_V184.md) · [Summary](controlled_predictive_fresh_h3_confirmation_v184/summary.json) · [Audit](controlled_predictive_fresh_h3_confirmation_v184/analysis.json) · [Ledger](v184_runtime_tmp/stage_checks.json)

**Limitations:** Fixed near-full-board generator, finite H3 and frozen continuation teacher; this does not establish general strategic learning, long episodes or sampling efficiency. Keep H2; U005 FAIL, U006 unstarted.
