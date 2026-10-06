# V186 — Optimal-action ranking

Fixed SOURCE143, V185 layout vocabulary/support and λ=0.1; changed only the fitting objective to one-sided optimal-versus-strictly-suboptimal utility gaps. The scalar model preserves exact first rewards and is evaluated with complete R/F/S on 96 unopened H3 boards.

RANK utility is **1.078180**, versus RIDGE **1.085317** and OLD_SHARED **1.137132**. RANK−RIDGE is **−0.007137** (5 improved, 6 worsened; replicas +0.004121/−0.045266/−0.008391/+0.020985). RANK−OLD_SHARED is **−0.058952** (8 improved, 13 worsened; 3/4 replicas negative). Against OLD_SHARED, reward changes −0.025428, failure +0.017551 and success −0.015972; regret roots are 44 versus 40. RANK−ONE is +0.140931 in all four replicas.

The optimizer converges: 369 constraints, 21 iterations, 24 paid loss/gradient calls, gradient_inf=1.14e−9. The independent nonnegative dual certifies the solution; its gap is −2.22e−16 from rounding. A gradient-based coefficient-distance bound was fixed and tested before real data to handle this cancellation. No optimizer or parameter retries.

**15 tests, 218/218 audit, 79/79 source and 6/6 input comparisons pass**; main/audit each once, 45.41 s/2.93 s, stderr 0. Costs retain one new predictor, one independent dual solve, 96 exact kernels/plans, 243,858 concrete observations and 413,754 successor entries. Physical random samples and native rule updates are zero.

**Next:** test position-shared rank/adjacency relations with held-out SOURCE groups and OLD_SHARED as the strong control. This experiment does not support adopting the ranking objective.

**Limitations:** One fixed strength and teacher on a finite synthetic H3 cohort. Objective change alone did not resolve generalization; these results do not identify representation as its unique cause. General strategic learning remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/ACTION_RANKING_V186.md) · [Summary](controlled_predictive_action_ranking_v186/summary.json) · [Audit](controlled_predictive_action_ranking_v186/analysis.json) · [Ledger](v186_runtime_tmp/stage_checks.json)
