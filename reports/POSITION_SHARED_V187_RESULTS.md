# V187 — Position-shared rank relations

Fixed SOURCE143/36 groups and the complete-consequence objective; removed absolute positions from cell and ordered horizontal/vertical rank-pair tokens, accumulating repeated occurrences. Vocabulary shrinks **2,777→285**, columns **2,783→291**. SOURCE-only selection again chooses λ=0.1; held-out group utility is **1.216261**, below RIDGE's **1.232649**.

On 96 unopened H3 boards, POOL utility is **1.045860**, RIDGE **1.060617**, OLD_SHARED **1.049503**. POOL−RIDGE is **−0.014757**: three replicas improve slightly, one loses −0.076522; 8 roots improve, 11 worsen. POOL−OLD_SHARED is **−0.003643**, with two positive/two negative replicas, 9 improved/16 worsened roots and 39 versus 34 regret roots. POOL failure is **2.745%**, versus RIDGE **2.091%**. POOL−ONE is +0.150482 in all four replicas. This representation is not adopted.

All **14,200 target token occurrences are known**. An additional posthoc comparison finds no equal-feature/equal-first-reward action pairs among 759 SOURCE and 499 TARGET pairs; it does not establish an unavoidable representation alias. Coverage completion did not eliminate the learning gap.

**15 tests, 216/216 independent checks, 80/80 source and 6/6 input comparisons pass**; main/audit each once, 35.70 s/7.21 s, stderr 0. Three main SVDs and 13 predictors, independently certified by 2 minimum-norm and 11 regularized solves; old models are reused. Retained acquisition costs: 96 exact kernels/plans, 210,175 concrete observations, 349,692 successor entries. No physical random samples or native updates.

**Next:** test low-dimensional interactions among the six shared mechanism features, especially vacancies, merge relations and goal relations; retain SOURCE-group selection, complete R/F/S and OLD_SHARED.

**Limitations:** Finite H3, a fixed teacher and root-action evaluation. The alias comparison is posthoc; results do not identify a unique cause or establish general strategic learning. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/POSITION_SHARED_V187.md) · [Summary](controlled_predictive_position_shared_v187/summary.json) · [Audit](controlled_predictive_position_shared_v187/analysis.json) · [Posthoc](controlled_predictive_position_shared_v187/posthoc_feature_aliases.json) · [Ledger](v187_runtime_tmp/stage_checks.json)
