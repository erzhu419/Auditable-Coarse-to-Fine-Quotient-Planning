# V188 — Low-dimensional mechanism interactions

Fixed SOURCE143/36 groups and the complete R/F/S consequence objective. Compared the original six shared features (LINEAR) with 20 fixed, physically scaled quadratic products (INTERACT, 26 columns), using the same SOURCE-only grouped selection. LINEAR chooses λ=0, INTERACT λ=0.01; held-out utilities are **1.233063 vs 1.223853**. INTERACT lowers training loss from 0.239016 to 0.227358.

On 96 unopened H3 boards, INTERACT utility is **1.169216**, LINEAR **1.174695**, RIDGE **1.117379**, OLD_SHARED **1.160326**. INTERACT−LINEAR is **−0.005479**, negative in three of four replicas: 2 roots improve, 4 worsen, 7 actions change; both models have 44 regret roots. One root supplies 97.8% of the positive gains. Failure increases from 2.855% to 2.907%; success is unchanged. **The added interactions are not adopted.**

INTERACT−RIDGE is +0.051837 in all four replicas, but LINEAR also exceeds RIDGE on this cohort. INTERACT−OLD_SHARED is +0.008890 with two positive/two negative replicas. These comparisons do not establish an interaction benefit over the matched linear control.

**15 tests, 216/216 independent checks, 81/81 source and 6/6 input comparisons pass**; main/audit each once, 23.92 s/4.01 s, stderr 0. Six main SVDs and 26 predictors; independently certified by 5 minimum-norm and 21 regularized solves. Acquired 96 exact kernels/plans, 248,490 concrete observations and 442,266 successor entries. No physical random samples or native updates.

**Next:** fix all 96 retained roots and explain the 44 LINEAR errors. With exact first rewards preserved, compute within-root limits imposed by identical six-feature actions, then test cross-root ordering constraints for a shared g(features). Explicit conflicts identify information limits; a strict feasible witness is needed to rule them out on this cohort. Use SOURCE coverage to identify interpolation versus extrapolation. Reuse labels and keep this diagnosis separate from future validation.

**Limitations:** Fixed teacher, finite H3 and root-action evaluation. General strategic learning remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/MECHANISM_INTERACTIONS_V188.md) · [Summary](controlled_predictive_mechanism_interactions_v188/summary.json) · [Audit](controlled_predictive_mechanism_interactions_v188/analysis.json) · [Ledger](v188_runtime_tmp/stage_checks.json)
