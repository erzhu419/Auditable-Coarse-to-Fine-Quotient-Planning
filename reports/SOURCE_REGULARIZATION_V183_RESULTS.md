# V183 — SOURCE-selected regularization

**SOURCE-only selection of λ=0.1 improves the fixed TARGET mean.** The V182 representation, complete vectors, masks and fallback remain unchanged; no target labels enter strength selection.

| TARGET comparison | Mean utility difference |
| --- | ---: |
| RIDGE−LAYOUT (V182) | +0.039675 |
| RIDGE−SHARED (V179) | +0.004044 |
| RIDGE−ONE | +0.020874 |

SOURCE held-out group utility increases from 1.001213 at λ=0 to **1.035727** at λ=0.1: six groups improve, one worsens, five tie. The full-SOURCE refit sacrifices interpolation (20 positive-regret roots), while TARGET closes **28.1%** of oracle headroom. TARGET success rises 1.98 percentage points versus LAYOUT and equals ONE; failure falls 0.0000625.

About **99.5%** of the gain over LAYOUT comes from repairing `v69_h3_01`. Against SHARED, two roots improve and six worsen; nine TARGET roots still have positive regret, with mean oracle gap 0.053385. The mean gain is not a broad per-board improvement.

**Next:** freeze λ=0.1, SOURCE vocabulary/coefficients and all baseline policies, then compare on a predeclared new H3 board cohort with the same continuation teacher and complete exact R/F/S labels. Evaluate the whole cohort and gain concentration; keep these new labels outside model selection.

**13 pure tests, 20/20 independent checks, 72/72 source and 6/6 input comparisons pass.** Main/audit run once (2.24 s / 2.63 s), stderr 0. Main uses three SVDs and 13 coefficient filters; audit independently solves all 13 coefficients and verifies final singular-value metadata. The first strict-zero test assertion was changed to numerical tolerance, with both attempts retained. No new features, physical samples, source games or native updates; costs include folds, encoding, choices, tests and inheritance.

[Protocol](../specs/SOURCE_REGULARIZATION_V183.md) · [SOURCE selection](controlled_predictive_source_regularization_v183/selection.json) · [Summary](controlled_predictive_source_regularization_v183/summary.json) · [Audit](controlled_predictive_source_regularization_v183/analysis.json) · [Ledger](v183_runtime_tmp/stage_checks.json)

**Limitations:** Reused finite-H3 roots, exposed TARGET and fixed teacher. SOURCE scores were used to select λ; new-board confirmation remains outstanding. This does not establish general strategic learning. H2 remains; U005 FAIL, U006 unstarted.
