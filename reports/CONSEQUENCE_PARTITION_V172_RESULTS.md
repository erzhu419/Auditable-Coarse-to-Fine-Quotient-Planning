# V172 — learned consequence partitions

V172 learns spatial state partitions from paired forced-first-action terminal consequences, separating deterministic first rewards from teacher continuation vectors. It completes the V171 follow-up learner and fresh action-preservation experiment. Scientific progression is **FAIL (0/2)**. Keep H2; U005 FAIL, U006 unstarted.

| Fresh first-action contrast, risk1 | Mean utility difference | SOURCE-cluster conditional 95% CI |
| --- | ---: | --- |
| PART_LATE − COARSE_LATE (primary) | +0.06988 | [−0.06645, +0.20620] |
| PART_LATE − H2 (progression) | +0.03181 | [−0.16543, +0.22904] |
| PART_LATE − ONE_LATE | +0.04489 | [−0.12543, +0.21521] |
| PART_LATE − PART_EARLY | +0.13719 | [−0.02142, +0.29581] |
| COARSE_LATE − H2 | −0.03807 | [−0.18084, +0.10470] |

All 256 VALID roots are unseen exact canonical boards, drawn from 32 new SOURCE games. Their four paired suffixes and all legal actions supply terminal reward/failure/success labels after the frozen first choices. The four histories each grow from three EARLY leaves on 32 old roots to nine LATE leaves on 96 roots. PART_LATE falls back at 0/256 roots and differs from H2 on 181/256; lack of model use does not explain this result. Late-versus-early improvement remains unconfirmed.

## Learning diagnosis and next main step

Training full-vector pair loss decreases by about 0.319/root (6.3%) versus ONE_LATE. Estimated within-root suffix variation accounts for 75–81% of remaining PART_LATE training loss across histories. On the same 256 fresh roots, reward/failure/success pair MSE is [4.82578, 0.39461, 0.39461] for PART_LATE versus [4.63922, 0.37895, 0.37895] for ONE_LATE. A **posthoc** SOURCE-cluster comparison of their summed three-component errors is +0.21789 [+0.08117, +0.35462], where positive means worse. COARSE_LATE has only 231 supported roots, so its unmatched MSE is not a fair comparison.

The training-to-validation reversal supports noise-fitting during greedy partition selection. Positive training loss reduction alone does not establish useful action distinctions. Next require independent SOURCE-group and paired-suffix evidence of reproducible action-order heterogeneity before accepting a learned split. Preserve exact first rewards, complete vectors and an untouched final validation cohort; freeze this distinct learner before fitting or sampling. Its implementation and experiment are pending.

## Numerical repair and evidence

The original independent audit passes 661/673 checks: all new physical trace replays, cohort/statistical reconstructions and costs pass; 11 model-coordinate comparisons and the frozen-choice payload comparison fail. Floating Laplacian row-sum error lifted a nominal null mode above the solver cutoff, adding a common action offset instead of fixing the promised zero-sum coordinates.

The original failed audit, source snapshot, models and choices remain unchanged. A separate [equivalence audit](controlled_predictive_consequence_partition_v172/equivalence_analysis.json) removes only each connected action component's common offset and compares with the independently centered solver at the original tolerance. It passes 20/20 supplemental checks, restoring 673/673 observable semantic checks with **zero action disagreements across 1,280 choices**, zero added samples and no physical replays. Maximum coordinate offset is 0.22423. The original zero-sum contract failure remains explicitly recorded; the supplemental result does not convert that original audit to PASS.

The active core now imposes an explicit zero-sum constraint per connected component; an actual retained normal-equation witness supplies the regression test. This maintenance occurs after the experiment and its one-time 91/91 source-byte comparison, and does not revise frozen artifacts or reported gains.

## Accounting and verification

TRAIN_SOURCE: 32 games / 30,992 transitions; TRAIN: 3,700 branches / 1,863,025. VALID_SOURCE: 32 games / 30,887; VALID: 3,736 branches / 1,884,434. Total: **7,500 physical games / 3,809,338 new transitions / 7,618,932 RNG draws**. All terminate. Existing 1,880 TRAIN branches, V171 and teacher setup/load costs remain referenced. Model fitting, support/fallback, feature and teacher work are retained; no neural updates or server downloads.

Thirty-five pre-run pure checks pass after one recorded correction to a test's scalar label-read expectation. Post-maintenance core 12, analyzer 15 and supplemental equivalence 2 tests pass, giving 38 distinct passing cases with the unchanged runner tests; tests acquire zero environment samples. Main, original physical audit and supplemental equivalence audit each run once: 272.96 s, 150.85 s and 9.69 s wall time, all stderr 0. The original audit exits 1; the supplemental audit exits 0. Diagnostic interpreter failure and subsequent read-only analysis remain recorded separately; no outcome resampling.

Evidence: [frozen protocol](../specs/CONSEQUENCE_PARTITION_V172.md), [run](controlled_predictive_consequence_partition_v172/run.json), [summary](controlled_predictive_consequence_partition_v172/summary.json), [original failed audit](controlled_predictive_consequence_partition_v172/analysis.json), [stage ledger](v172_runtime_tmp/stage_checks.json), [supplemental ledger](v172_runtime_tmp/equivalence_checks.json), [read-only diagnosis](v172_runtime_tmp/readonly_diagnosis.json), [numerical maintenance](v172_runtime_tmp/numerical_maintenance.json).

## Limitations

Intervals condition on four existing teachers and frozen learned models. Execution here tests a forced first action followed by its own H2, rather than autonomous whole-game control or composable successor dynamics; it does not overturn V171's whole-game failure. The noise diagnosis is posthoc and does not establish that all spatial abstractions fail. General strategic learning and sample-efficiency benefit remain unresolved.

