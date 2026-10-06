# V155 — episode-grouped holdout of advantage repair

Freeze this protocol, all 64 inherited root identities and all 32 folds
before fitting. This is an exploratory diagnostic using V153 data already
inspected in V153/V154, not a fresh full-game confirmation.

For each of four histories and two queries, group the H2 and LEARN8
source roots with the same replica (0,4,8,12) and source seed. Hold both
roots out together; the other six roots form the training set. Use all
four folds, preserving the original root order. A root is evaluated out
of sample once per repair arm.

Use only V154's audited compact three-component means and its eight
unchanged OLD checkpoints. For each fold fit REPAIR_H2 and REPAIR_GATE
independently from the same OLD state: unchanged root features plus bias,
normalized LMS, alpha=0.1, 32 passes over six roots. This keeps the V154
per-root update schedule, yielding 192 updates per fit, 64 fits and
12,288 new updates. Do not use the heldout targets or older V151 labels
in fitting; do not initialize from a V154 repaired checkpoint.

Freeze all 64 repairs before evaluation. Predict OLD once on each of
64 roots, and each repair on its six training and two heldout roots:
512 repair predictions, 576 total. Retain all 512 rows, marking the split,
original source, fold, targets and old/new predictions. The gate remains
strictly positive predicted query utility.

Primary descriptive outcomes on heldout roots are own-target MSE change
(new minus OLD, negative is better) and local utility change
(new_accept minus old_accept) times the GATE target utility.
Also report both arms against the same GATE target, the H2 target,
old/new acceptance and disagreement counts, and training diagnostics.
The GATE local comparison changes only the current module decision and
then resumes OLD; it does not measure the repaired policy's full game.

Include zero-disagreement roots. Within each query and split, average
roots equally within a history, then the four histories equally. Retain
all four folds, all histories, and ALL/H2/LEARN8 source strata for both
arms. Training roots recur in three folds and are diagnostics only.
Do not treat overlapping fold fits as independent observations or give
a naive cross-validation confidence interval. No seed/arm/fold selection.

Record source reads, fits, predictions, model copies and independent
numerical verification separately. Link the already completed V154
label and source audit; do not reread or replay its 4,096 source branches.
Both repair budget views include all 2,017,530 retained training
transitions; physical acquisition is counted once. New environment and
native planner calls are zero.

Keep H2 operational, U005 FAIL and U006 unstarted. If heldout prediction
or local gain does not improve, diagnose learning transfer before buying
more suffixes. If both improve while V154 full-game gain does not, the
next targeted test concerns coverage of states actually visited by the
changed policy. Neither pattern alone establishes the cause of V154's
full-game result.

