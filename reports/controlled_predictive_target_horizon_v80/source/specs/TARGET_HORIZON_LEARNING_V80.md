# V80: matched-observation short versus terminal consequence learning

Frozen 2026-09-13 before completing training branches or evaluating V80 models.
V79 isolated horizon sensitivity in fixed-model validation rollouts. V80 tests
whether changing the learning target itself improves subsequent natural games.

## Shared chronological experience

Reuse V77's 225 complete natural training games (lifecycles 0/1/2, episodes
0..74) and only V78's training_branches.jsonl.gz files at checkpoints 39/75.
Do not train on V78 acceptance roots, V79 continuations or any evaluation game.
There are 1548 branch prefixes: 1372 CUTOFF, 176 LOST, 47,219 transitions.
Continue each CUTOFF branch from its retained final board and environment stream
under its original GREEDY/SPACE/SNAKE policy to WON/LOST or 2000 total actions.
The forced first action remains in the prefix and is not repeated. Already
terminal prefixes consume no new transitions. Maximum new branch work is
1372*(2000-32)=2,700,096 actual transitions; report actual use and censoring.

Natural-game anchors are 0,4,8,... plus the last action; branch anchors are
only action zero. At each anchor, produce a matched row with two targets:
SHORT is the next at most 30 action rewards /2048 and first failure/success,
starting before the anchor spawn. TERMINAL continues to observed termination.
Both exclude the anchor action reward and bind the whole R/F/S vector to the
same continuation policy. A true terminal closes a short window early. A game
still administratively CUTOFF cannot supply a terminal label and is omitted
from both target arms, while its trace and cost remain retained.

At checkpoints 15/39/75, reveal only the completed natural prefix and branch
batches available by then. Episode%5==4 remains heldout and never fits a tree.
Both arms use exactly the same ordered rows and board features; labels differ.

## Fixed learning and planning

Fit a fresh three-policy multi-output regression tree model at every checkpoint,
with the V77 recipe: max_depth=8, min_samples_leaf=16, random_state=7701. There
is no acceptance filter. Use the existing 37-dimensional features(board,30) in
both arms. Its final column is the identical constant leaf-position context;
TERMINAL model metadata explicitly identifies an observed-terminal target,
not a 30-step prediction. Only the common depth-two deployment is supported.

Keep the V77 algebraic planner: two shared root-spawn samples, enumerate second
actions, then select a complete policy-conditioned R/F/S vector at each leaf.
SHORT supplies 30-step leaf values; TERMINAL supplies learned terminal policy
consequences. The planned depth, known dynamics, features and fit algorithm are
identical. Terminal labels change the assumed continuation, not exact guarantees
for the receding-horizon policy subsequently deployed.

Methods are H2_ONLY, SHORT_PLAN, TERMINAL_PLAN, SHORT_FROZEN, TERMINAL_FROZEN.
The frozen models are copies of the corresponding 15-episode fits and never
update. Evaluate all five at all three checkpoints on two new natural-game
seeds per lifecycle and both fixed queries reward=(1,0,0), risk_goal=(1,4,4).
Environment seed is 8090000 + lifecycle*100 + replica, replica=0/1; model seed
adds 1000000. Share seeds across methods, checkpoints and queries, rotate method
execution order, and stop natural games at WON/LOST or the 2000-action cap.
The 180 evaluation games never affect fitting, row selection or hyperparameters.

## Measurements and interpretation

Primary comparison is final TERMINAL_PLAN minus SHORT_PLAN, separately by query
and independent lifecycle. Report all checkpoint curves, each learner relative
to its own frozen counterpart, terminal outcomes and query response. H2_ONLY
is a shorter-horizon reference, not an equal-horizon learning arm. Compare own
label fit errors only within a target scope; raw SHORT/TERMINAL losses have
different scales and meanings.

Report matched fitting-row counts, censored rows/games, labels by policy and
terminal success coverage. If every observed policy continuation fails, terminal
F=1/S=0 carries no discrimination among those continuations; do not claim risk
learning from reward gains or changed actions alone.

Separate inherited natural and branch prefixes from newly sampled suffixes and
evaluation interactions. Count common data preparation and suffix acquisition
once as actual execution, and attribute the full common data cost to each
updated learner for this matched-acquisition comparison. Frozen models pay only
their warmup data and fit. This does not estimate the minimum acquisition cost
of a standalone short-target method. Record initialization, fitting, export,
evaluation and total wall time; never add shared per-method cost attributions
to obtain actual wall time.

This remains learning from a prescribed policy library and a previously chosen
branch cohort. Three lifecycles are exploratory evidence. Keep failed and capped
games and both positive/negative query effects. Do not change the protocol after
main results. U005 remains FAIL and U006 remains unstarted.
