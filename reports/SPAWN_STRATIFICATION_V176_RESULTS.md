# V176 — Probability-weighted first-spawn sampling

The V175 follow-up is complete. **First-spawn stratification does not establish a variance or cost benefit.** The frozen variance-reduction condition is not met; no extra blocks, fitting, tree growth or strategy promotion follow. Keep V135 H2; U005 FAIL, U006 unstarted.

| Sampler | Physical branches | Actual transitions | Utility mean on eight fixed boards | Utility block-estimate variance |
| --- | ---: | ---: | ---: | ---: |
| IID | 7,040 | 3,662,734 | +0.08662 | 0.0106718 |
| STRAT | 7,040 | 3,655,716 | +0.09219 | 0.0296386 |

STRAT/IID utility variance ratio is **2.77729**. The paired variance difference is **+0.0189668**, with the frozen eight-block jackknife normal 95% interval **[−0.0345057, +0.0724394]**. The interval does not establish either lower variance or significantly worse variance. The variance × mean block-transition-cost ratio is **2.77197**, descriptive only. Six of eight root variance ratios exceed one; two history ratios fall below one, so the response is heterogeneous.

Eight boards are selected by median first-spawn support size within each V175 TRAIN/FRESH history, without looking at outcomes. The 12–18 joint strata preserve both actions’ true spawn marginals and common rank. Probability-only allocation retains at least two samples per stratum and exactly 4S paired draws per block. STRAT reconstructs the full expectation from probability-weighted stratum means; IID uses arithmetic paired means. Independent first-spawn and continuation RNGs preserve common tails across methods/actions. Policies and targets are identical.

## Accounting and verification

**14,080 terminal branches / 7,318,450 transitions / 14,622,820 physical RNG draws**, with 7,040 conditioned first-spawn assignments. Outcomes: 8,955 WON and 5,125 LOST; no cutoff. New source games, fits and native weight updates are zero. Teacher loading, source geometry, all H2 decisions, tests and inherited costs remain referenced; old tapes are not replayed. Geometry preflight and formal extraction are separately charged. A Python 3.10 import error was corrected before any input reading or sampling; its record is retained.

**25 distinct pure tests**, **131/131 independent checks** and **103/103 frozen-source byte comparisons** pass. Main/audit each execute once: 713.67 s / 372.88 s, exit 0, stderr 0. Independent replay verifies all new trajectories, probability weights, paired block statistics and method costs; it performs 58,525,860 ground swipes.

Evidence: [protocol](../specs/SPAWN_STRATIFICATION_V176.md), [summary](controlled_predictive_spawn_stratification_v176/summary.json), [audit](controlled_predictive_spawn_stratification_v176/analysis.json), [selected boards](controlled_predictive_spawn_stratification_v176/selected_roots.json), [stage ledger](v176_runtime_tmp/stage_checks.json), [preflight ledger](v176_runtime_tmp/preflight_checks.json).

## Next step and limitations

Stop this sampling branch. Use the stored V68 RAW kernel on 47 H3 source roots (V177 verifies one additional H2 root in the original 48-root roster and excludes it) and the 24 V69 H3 roots for an exact-label learning diagnostic. Adapt the same partition learner to expected complete outcome vectors, without pretending that exact expectations are four random suffixes. Keep the one exact teacher and provenance design groups explicit. First retain exact oracle actions/vectors and calibrate oracle−ONE headroom; if ONE is already optimal, the dataset cannot diagnose a learning failure. Then test whether the learner closes that gap. H4 remains a separate horizon-transfer diagnostic.

The eight selected boards are a geometry subset; their positive mean contrasts do not supersede V175’s all-root result or establish general policy benefit. The interval is an eight-block conditional approximation, not an equivalence test. This experiment does not identify the dominant noise source or disprove other sampling schemes. V68/V69 are reused diagnostics, not fresh confirmation; short-horizon success would still leave long-episode strategic and continual learning unresolved.

