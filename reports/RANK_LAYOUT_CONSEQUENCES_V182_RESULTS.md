# V182 — Rank/layout-conditioned complete consequences

**The richer representation fits SOURCE perfectly but does not transfer its benefit.** LAYOUT retains the six aggregates and adds position-specific cell ranks and horizontal/vertical rank pairs. Its SOURCE-only vocabulary has 2,058 tokens; one weighted minimum-norm fit predicts complete continuation differences.

| Primary weighting | LAYOUT−ONE utility | LAYOUT−SHARED utility | Oracle−LAYOUT |
| --- | ---: | ---: | ---: |
| SOURCE, design-group mean | +0.172675 | +0.082185 | 0 |
| TARGET, root mean | −0.018801 | −0.035632 | +0.093060 |

All 47 SOURCE roots choose an optimal action; pair-vector loss falls from SHARED's 11.487603 to 1.61e−28. The 2,064-column design has rank **122 = 169 legal actions − 47 roots**, spanning every independent same-root contrast. This establishes interpolation capacity, rather than transferable strategy.

TARGET has nine positive-regret roots versus SHARED's six: four newly wrong and one resolved. Against ONE, eight roots improve, three worsen and thirteen retain equal value; mean utility is still negative. LAYOUT−ONE has reward +0.000991, failure unchanged and success **−0.019792**. LAYOUT−SHARED has reward −0.035569, failure +0.000063 and success unchanged. Fallback is zero. TARGET observes 441/3,640 tokens absent from SOURCE (12.1%); every target root has at least one.

**Next:** keep this representation and full-vector objective fixed, and select regularization by held-out SOURCE design-group action utility. Each fit uses only its SOURCE fitting groups; freeze the resulting full-SOURCE model before the unchanged target diagnostic. This tests whether capacity control improves generalization without choosing parameters from TARGET.

**15 pure tests, 24/24 independent checks, 69/69 source and 8/8 input comparisons pass.** Main/audit run once (1.36 s / 0.95 s), stderr 0. One new predictor fit and one independent SVD; old models, choices and labels remain fixed. No new physical samples, source games or native updates. New feature, vocabulary, matrix, inference, test and inherited costs are retained.

[Protocol](../specs/RANK_LAYOUT_CONSEQUENCES_V182.md) · [Models](controlled_predictive_rank_layout_consequences_v182/models.json) · [Summary](controlled_predictive_rank_layout_consequences_v182/summary.json) · [Audit](controlled_predictive_rank_layout_consequences_v182/analysis.json) · [Ledger](v182_runtime_tmp/stage_checks.json)

**Limitations:** Reused finite-H3 roots and an exposed target under a fixed teacher. The training/target gap supports a generalization problem; it does not isolate unseen tokens as its cause or prove that richer models cannot transfer. V182 is not promoted. V179's prior mean gain remains; H2 stays, U005 FAIL, U006 unstarted.
