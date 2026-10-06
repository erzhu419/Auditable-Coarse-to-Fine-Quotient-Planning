# V175 — Frozen-board suffix replication

V174’s follow-up is implemented and complete. **The retrospective TRAIN gain does not replicate on the same boards.** TREE/ONE policies, all 640 boards, source membership and budgets were frozen; every changed root receives 16 new paired suffixes, with the same H2 continuation. This is a diagnostic experiment, with no strategy promotion. Keep H2; U005 FAIL, U006 unstarted.

| Utility contrast | Mean | SOURCE-cluster conditional 95% CI | Fixed-board suffix conditional 95% CI |
| --- | ---: | --- | --- |
| TRAIN NEW: TREE − ONE | −0.04287 | [−0.09246, +0.00672] | [−0.09159, +0.00585] |
| TRAIN NEW − OLD reference | −0.18334 | [−0.28658, −0.08010] | [−0.23206, −0.13462] |
| FRESH NEW: TREE − ONE | −0.02747 | [−0.09844, +0.04351] | [−0.09023, +0.03529] |
| FRESH NEW − TRAIN NEW | +0.01540 | [−0.07118, +0.10198] | [−0.06405, +0.09486] |

Original TRAIN utility was +0.14047 [+0.04957, +0.23137] across SOURCE clusters. All four histories now have negative TRAIN point estimates: [−0.02854, −0.06590, −0.07483, −0.00220]. The significant drop occurs without changing a board or policy. Prior fitting/selection on noisy labels therefore takes priority; neither new cohort establishes positive TREE utility. The fresh-versus-training difference is unresolved, so these results do not establish an additional board-generalization penalty.

FRESH’s old reference was −0.10160; NEW−OLD is +0.07414. Its SOURCE interval includes zero, while its fixed-board interval is positive. Both are retained as secondary results; neither interval is selected after seeing the outcome. All complete reward/failure/success contrasts remain in the summary. OLD is the observed fixed reference, not an error-free estimate of its unknown expectation.

## Execution and accounting

TRAIN: 5,376 terminal branches / 2,640,652 transitions. FRESH: 4,064 / 1,992,104. Total: **9,440 branches / 4,632,756 transitions / 9,265,512 RNG draws**. Outcomes comprise 5,728 WON and 3,712 LOST, with no cutoff. There are 168 changed TRAIN roots and 127 changed FRESH roots; 345 same-action roots retain zero differences and their full statistical weights. All roots are supported. New source games, model fits and native weight updates are zero; inherited paid costs remain referenced.

**33 distinct pure tests**, **275/275 independent checks**, and **101/101 resumed-source byte comparisons** pass. The original failed test and physical attempt are retained. The latter saved four terminal raw branches before the inherited compact writer raised `KeyError: replica`. Recovery repairs the recording interface, reuses all four raw records exactly and executes only unstarted frozen plans. The final physical total counts those 3,015 transitions once; eight additional teacher-bank loads and the failed attempt’s 6.41 s remain charged. All frozen inputs and eight models are unchanged. Recovery main/audit run once: 454.47 s / 259.73 s, exit 0, stderr 0.

Evidence: [protocol](../specs/FIXED_BOARD_REPLICATION_V175.md), [summary](controlled_predictive_fixed_board_replication_v175/summary.json), [independent audit](controlled_predictive_fixed_board_replication_v175/analysis.json), [stage ledger](v175_runtime_tmp/stage_checks.json), [engineering recovery](v175_runtime_tmp/engineering_recovery.json), [original failure](v175_runtime_tmp/failed_attempt1/main.stderr).

## Next step and limitations

Change how consequence evidence is acquired before proposing more state splits. Test probability-weighted sampling over actual first-spawn support against the current sampler at matched physical branch budgets, preserving complete outcome vectors. Quantify both within-board variance and independent policy utility; a variance reduction alone does not establish better learning. If the acquisition probe helps, compare the same frozen learner trained by each acquisition method and evaluate on independent new boards/suffixes. Do not increase tree capacity or adjust the acceptance threshold using V175 outcomes.

Intervals condition on four teachers and use the frozen normal approximation. TRAIN includes the original V171 and V172 root-sampling geometries; FRESH uses V174 geometry. The experiment does not uniquely separate label noise from selection optimism, identify first-spawn variance as dominant, or establish equivalence when an interval includes zero. Failed-attempt per-load telemetry was not saved. Autonomous whole-game benefit, reusable strategic models and continual learning remain unresolved.

