# V173 — independently confirmed partitions

V173 separates DISCOVERY proposals, fresh CONFIRM split selection and fresh VALID performance. The independent confirmation and pruning mechanism works; scientific progression is **FAIL (0/2)**, with **zero retained splits**. Keep H2; U005 FAIL, U006 unstarted.

| Fresh first-action contrast, risk1 | Mean utility difference | SOURCE-cluster conditional 95% CI |
| --- | ---: | --- |
| PART_CONFIRMED − PART_UNPRUNED (primary) | +0.08002 | [−0.04239, +0.20244] |
| PART_CONFIRMED − H2 (progression) | −0.04197 | [−0.19627, +0.11234] |
| PART_CONFIRMED − ONE_LATE | 0.00000 | [0.00000, 0.00000] |
| PART_CONFIRMED − COARSE_LATE | −0.02581 | [−0.16613, +0.11452] |
| PART_UNPRUNED − H2 | −0.12199 | [−0.28082, +0.03684] |

DISCOVERY uses only the 384 existing TRAIN roots and their 5,580 compact forced-first-action outcomes: 96 roots/history. The same greedy grammar proposes nine leaves/history; every collapsed parent/direct-child estimator freezes before CONFIRM. Confirmation uses 256 unseen roots from 32 new SOURCE games, four paired suffixes and all legal actions. It only selects keep/collapse, without fitting coefficients or adding candidates.

All 32 candidates are recorded: 26 satisfy coverage/support eligibility and none pass the frozen adjusted utility bound. Five others lack two SOURCE groups with supported model changes; one lacks child coverage. Every root split is eligible, with eight SOURCE groups on each side and 8/8/8/7 groups with supported action changes. Their confirmation utility means are −0.16098, −0.05068, +0.08862 and −0.09219; all adjusted intervals cross zero. There is no locally passing descendant hidden by ancestor rejection. Each final tree therefore has one leaf and equals ONE_LATE.

A retained retrospective comparison of each fixed root's direct-child policy against its parent on DISCOVERY gives utility means [−0.01978, +0.10837, +0.02361, +0.06200], using 12 SOURCE groups/history. All 384 roots have complete parent/child model support. Thus the first history supplies an actual counterexample: positive full-vector SSE split gain can reduce even training policy utility. Histories 1 and 3 additionally reverse from positive training estimates to negative confirmation estimates. These training estimates are descriptive, without new CIs; the frozen decisions stay unchanged.

All 256 final VALID roots are unseen against learning data; all 1,280 choices freeze before labels. PART_CONFIRMED has no fallback and differs from H2 on 146/256 roots. Its reward/failure/success pair MSE is [4.38460, 0.40107, 0.40107], versus [4.63820, 0.41452, 0.41452] for unpruned proposals, on the same roots. These lower descriptive prediction errors do not establish utility improvement or successful state learning.

## Accounting and verification

CONFIRM_SOURCE: 32 games / 31,504 transitions; CONFIRM: 3,704 branches / 1,845,493. VALID_SOURCE: 32 games / 31,632; VALID: 3,708 branches / 1,840,826. Total: **7,476 complete physical games / 3,749,455 new transitions / 7,499,166 RNG draws**. Inherited V171/V172 and teacher costs remain referenced. Twelve discovery models are fitted once, with node reconstruction separately counted; four confirmed models reuse fixed coefficients.

All 40 distinct pure tests pass after one retained correction of a test's condition-count assertion; tests acquire zero environment samples. Independent audit passes **544/544 checks**, with `valid=true`; the one-time frozen-source comparison passes **95/95**. Main and audit each run once, 301.52 s and 154.98 s wall time, both exit 0 and stderr 0. There are no new neural updates or server downloads.

Evidence: [protocol](../specs/CONFIRMED_PARTITION_V173.md), [run](controlled_predictive_confirmed_partition_v173/run.json), [summary](controlled_predictive_confirmed_partition_v173/summary.json), [independent audit](controlled_predictive_confirmed_partition_v173/analysis.json), [pruning records](controlled_predictive_confirmed_partition_v173/pruning_records.json), [stage ledger](v173_runtime_tmp/stage_checks.json), [confirmation diagnosis](v173_runtime_tmp/confirmation_diagnosis.json).

## Next main step and limitations

Generate candidate state splits using actual action utility on heldout SOURCE groups, keeping complete outcome vectors and exact first rewards. The candidate-learning objective must preserve action value before independent confirmation can produce useful rules. Maintain a fresh final validation cohort; independent same-board suffix replication can then distinguish label noise from persistent signal. This new learner and experiment are pending.

Intervals condition on four fixed teachers. The eight-SOURCE normal confirmation bounds are a model-selection rule, not a formal whole-tree certificate. Zero accepted splits does not prove that all useful distinctions are absent or that sampling power is sufficient. This stage tests a first action followed by H2; general strategic learning and autonomous whole-game improvement remain unresolved.

