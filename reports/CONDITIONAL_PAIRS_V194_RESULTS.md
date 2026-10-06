# V194 — Rank-conditioned pair transfer helps its matched control

**CONDITIONAL improves over PAIR98, but remains below the strong baselines and is not adopted.** Both use nonnegative local mixtures of complete same-board SOURCE action-pair tail R/F/S differences, followed by a consistent action-score projection. PAIR98 keeps the old 98 features; CONDITIONAL uses 224 goal-relative rank-stratified relation moments.

SOURCE143/36-group held-out actual utility selects CONDITIONAL k=8, temperature=1 and PAIR98 k=32, temperature=1. Their validation utilities are **1.197011 / 1.172752**. All choices freeze before labels on four new 24-board H3 replicas.

| Fresh TARGET96 comparator | Utility | Regret roots | CONDITIONAL minus comparator | Positive replicas |
|---|---:|---:|---:|---:|
| CONDITIONAL | 1.006348 | 41 | — | — |
| PAIR98 | 0.972888 | 61 | **+0.033460** | **4/4** |
| LINEAR | 1.032555 | 54 | **−0.026208** | 1/4 |
| NONLINEAR (V192) | 1.023135 | 44 | **−0.016787** | 1/4 |
| OLD_SHARED | 1.035854 | 51 | **−0.029507** | 1/4 |

Against PAIR98, CONDITIONAL resolves 26 errors and adds six. Against LINEAR, it resolves 23 and adds ten, yet positive utility gains total only **2.243318**, versus losses of **−4.759245**. The largest loss is **−1.750531** at `v194_target_r03_00`. Lower error frequency does not produce better mean utility. The LINEAR contrast decomposes into R/F/S changes **[−0.020242, −0.005927, −0.011892]**: lower failure probability is outweighed by reward and success losses.

TARGET projection changes the sign of 56/492 CONDITIONAL tail-utility pairs. Retained replay of two high-loss roots localizes a failure already present before projection. At `r03_00`, RIGHT−oracle LEFT has true tail utility **−1.750531**, versus raw/projected **+0.005042**; immediate rewards tie and projection residual is zero. The true success difference is **−1**, versus prediction zero. At `r02_05`, LEFT−oracle UP has true tail utility **−1.620440**, versus raw **+0.117617** and projected **+0.132378**. The first-reward advantage +0.560547 still leaves actual regret 1.059893. Both raw estimates already rank the pair incorrectly.

**Next:** learn transfer applicability that distinguishes goal-reaching continuation structure, retaining complete R/F/S and SOURCE-group actual-utility selection. Preserve these two failures as diagnostics; test a frozen learner on fresh targets. Projection optimization cannot repair their pre-existing raw ranking errors.

**Verification and cost:** 20/20 synthetic tests; **229/229 independent audit, 89/89 source, 9/9 input** comparisons pass. Main/audit each once, **44.68/27.29 s**, stderr 0. Six prototype libraries, 38 configuration instances, zero parameter solves; 96 new exact kernels/plans/labels, zero new SOURCE games, physical random samples or native updates. SOURCE projection costs 0.21 s, selections 6.01/3.22 s, SOURCE diagnostics 4.71/2.71 s, all-arm TARGET choices 6.54 s, labels 18.07 s. Full cost history remains in the ledger.

**Limitations:** This is one descriptive fresh cohort, with designed rank bins and finite H3/fixed-teacher labels. Nonnegative convexity applies before projection; relative F/S scores are not calibrated probabilities. Sign-flip counts alone do not establish the cause of errors. Self-prototype SOURCE scores are not transfer evidence. General strategy remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/CONDITIONAL_PAIRS_V194.md) · [Summary](publication/v327_snapshot/controlled_predictive_conditional_pairs_v194/summary.json.gz) · [SOURCE selection](controlled_predictive_conditional_pairs_v194/selection.json) · [Choices](controlled_predictive_conditional_pairs_v194/choices.json) · [Audit](publication/v327_snapshot/controlled_predictive_conditional_pairs_v194/analysis.json.gz) · [Ledger](v194_runtime_tmp/stage_checks.json)
