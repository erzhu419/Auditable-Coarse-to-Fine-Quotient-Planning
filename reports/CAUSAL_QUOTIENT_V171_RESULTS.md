# V171 — causal quotient planning results

V171 implements empirical action-to-successor models, teacher-specific continuation vectors and bounded Bellman composition. The same data support depth 1 and depth 3 planning; same-history learning and three-source transfer are separate arms. All models freeze before VALID/EVAL. Execution is correct; scientific progression is **FAIL (0/2)**. Keep H2; U005 FAIL, U006 unstarted.

| Fresh whole-game contrast, risk1 | Mean utility difference | Conditional 95% CI |
| --- | ---: | --- |
| SAME_D3 − SAME_D1 (primary) | −0.04771 | [−0.14125, +0.04582] |
| SAME_D3 − H2 (progression) | −9.17606 | [−9.59934, −8.75277] |
| XFER_D3 − XFER_D1 | +0.02808 | [−0.06423, +0.12039] |
| XFER_D3 − H2 | −9.57645 | [−10.00163, −9.15127] |
| XFER_D3 − SAME_D3 | −0.40039 | [−0.51874, −0.28204] |

Each arm has 128 complete games, paired on 32 ordinary initial seeds per existing history. H2 wins 70/128; each of the four model arms wins 0/128. SAME_D3 increases failure by 54.69 percentage points [45.97, 63.40] against H2. SAME_D3 and XFER_D3 choose model actions in 92.05% and 96.78% of decisions, respectively.

## What this resolves

The model construction, whole-vector composition, primitive-action transport and persistent replanning work as frozen. Each history has 55–58 observed action rows and 15 observed ACTIVE states from the fixed 18-key grammar. This supplies an executable model-planning baseline; it does not establish useful strategic abstraction.

VALID has 519,172/519,220 transition predictions and 519,210 jointly supported D1/D3 decisions. Only 3,826 (0.737%) of those decisions change direction with depth. Branch/history-averaged transition Brier is 0.28150; H2-tail component MSE is [2.84795, 0.22926, 0.22926]. High observational coverage does not ensure decision preservation.

A retained SOURCE witness has key `A:0:2:1` and canonical RIGHT at steps 1 and 4 of `SOURCE:0:risk1:0`, with actual rewards 4 and 8. Exact reward homogeneity therefore fails. More structurally, only 1,880/1,048,102 fitted transitions (0.1794%) are forced first actions; the rest are H2-selected actions. Aggregating these hidden-board mixtures can change action-conditional transitions when the controller changes. H2 boundary values likewise describe H2 continuations.

## Accounting and verification

TRAIN: 1,880 complete branches / 1,031,811 new transitions. VALID: 940 / 519,220. EVAL: 640 / 216,703. Total: **3,460 physical games / 1,767,734 new transitions / 3,538,028 RNG draws**. Reused SOURCE contributes 16 games / 16,291 inherited transitions, not new acquisition; V170 and teacher costs remain referenced. Ground legality, model fitting/compilation, feature work, teacher loads and fallback work are retained in the raw records.

All 32 focused tests pass on their first attempts; four finite-game fixtures add 16 transitions / 44 draws separately. Independent replay/reconstruction passes 481/481 checks with `valid=true`; 90/90 frozen-source byte comparisons pass. Main and audit each run once: 345.70 s and 588.23 s wall time, both stderr 0. Read-only diagnosis adds no environment draws or oracle swipes; its initial import failure and successful five-step SOURCE read are retained separately.

Evidence: [frozen protocol](../specs/CAUSAL_QUOTIENT_PLANNING_V171.md), [run](controlled_predictive_causal_quotient_v171/run.json), [summary](controlled_predictive_causal_quotient_v171/summary.json), [independent audit](controlled_predictive_causal_quotient_v171/analysis.json), [VALID diagnostics](controlled_predictive_causal_quotient_v171/prediction_diagnostics.json), [test/stage ledger](v171_runtime_tmp/stage_checks.json), [retained diagnosis](v171_runtime_tmp/representation_diagnosis.json).

## Next main step and limitations

Learn state partitions from **paired forced-first-action consequences within current blocks**, with H2 continuation labels kept separate. Freeze the learner, partition and controls before fresh heldout labels; test action-choice preservation before autonomous whole-game control. More depth, support-count tuning or manually adding one feature does not resolve the identified mixture problem. This next learner is not implemented or launched.

Intervals condition on four existing teachers and frozen training/representation choices. XFER uses three source histories, so XFER-minus-SAME is not a pure transfer or sample-efficiency effect. The reward witness does not isolate action-ranking errors or quantify the contribution of aliasing, observational action selection and boundary/deployment shift to the whole-game loss. The fixed state grammar itself is not learned, and no exact Markov abstraction or efficiency claim is established.
