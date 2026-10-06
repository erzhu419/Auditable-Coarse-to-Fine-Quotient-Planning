# V84: preserve each candidate's consequence vector in a joint output

Frozen before V84 fitting, diagnostics or new evaluation. V83's trees all ignored
duration; the fixed tie order then made four-step choices impossible. V84 changes
the learned representation of the candidates while reusing the complete V83
acquisition and the unchanged terminating-fragment controller.

## Matched data and fitting

For each lifecycle 0/1/2 and checkpoints 6/12 load the corresponding cumulative
V83 new_rows.jsonl.gz files. Every retained root has all four non-H2 candidate
vectors (SPACE_1, SNAKE_1, SPACE_4, SNAKE_4). These remain the original eight-replica
terminal differences against H2. No source or branch trajectory is sampled again;
V83 evaluation data do not enter fitting. Episode%5==4 is heldout as before.

Group the four candidate vectors at a query/episode/board into one row. Inputs are
the 36 V77 observed-board features. Outputs are all four separate R/F/S vectors,
flattened in the frozen candidate order to 12 values. Fit one multi-output tree
per query, max_depth=3, random_state=8301, min_samples_leaf=2 complete roots.
Two complete roots supply eight candidate vectors, matching the information count
of V83's eight option-row leaf minimum. The grouping and available partitions
change; this is not a claim of identical capacity or identical search space.

The joint model must preserve the four output slots even when they share a leaf.
Selection uses the same query-weighted complete vector, exact zero H2 reference,
strictly positive improvement rule, and original tie order. No post-result change
to thresholds or choice order. Save the checkpoint-6 joint model as a frozen arm.
Retain the original V83 checkpoint selectors without refitting as OLD_CONDITIONED.

Before evaluating, save all candidate models, data snapshots and fit logs for that
checkpoint. Retained-data diagnostics compare predictions, selected observed
advantages and the six pairwise candidate orderings within a root, separately on
training and heldout roots. Eight-replica outcomes are noisy references, not exact
values. Diagnostics do not accept, reject or tune either model.

## Identical controller, fresh paired natural games

Use the V83 controller without changes: first active observation with at most six
empty cells triggers one choice; execute SPACE/SNAKE for one or four active actions,
then permanently return to H2. Every active decision consumes four model uniforms,
including the recorded unused draws during deterministic fragments.

Methods: H2_ONLY, JOINT, JOINT_ONE_STEP, JOINT_FROZEN6, OLD_CONDITIONED,
FIXED_SPACE4. JOINT_ONE_STEP restricts the same current joint model to H2 and the
two one-step options. OLD_CONDITIONED loads the original corresponding V83
checkpoint. Other fixed arms use H2, the joint checkpoint-6 model, and fixed
SPACE_4 respectively. All start natural games from the normal two initial tiles.

At each checkpoint evaluate eight new replicas per query and lifecycle, totaling
576 games. Environment seed=8490000+lifecycle*100+replica, replica=0..7; model seed
adds 1000000. Share seeds across methods, queries and checkpoints, and rotate method
order. Each game stops at WON/LOST or 2000 actions. Evaluation never affects data,
fitting or selector choice. Three independent lifecycle workers run concurrently;
methods within a worker run sequentially. Retain complete action histories.

## Comparisons, costs and scope

Primary final JOINT-minus-H2/ONE_STEP/FROZEN6/OLD/FIXED effects use the common complete
six-method cohort within each replica/query/lifecycle. If any method is CUTOFF,
exclude that replica from every terminal comparison, retaining all work/outcomes.
Average paired effects within lifecycle then equally across three lifecycles.
Report changes from checkpoint 6 to 12, chosen primitives/durations, actual
histories equal to H2, success/failure, and fixed-control/prefix/commitment checks.
Selecting a four-step option is representational progress, not reward evidence.

New acquisition count is zero; the maximum new evaluation cost is 1,152,000
transitions. Count actual evaluation and fitting once. Inherit V83 source and
branch construction by checkpoint (excluding old evaluation and old model fit for
new joint models); OLD_CONDITIONED also inherits its own existing fit/export.
JOINT/ONE_STEP pay cumulative new joint fitting, while JOINT_FROZEN6 pays only the
first joint fit and first-batch inherited acquisition. Joint source data are shared
method attributions, not additive execution costs. Report outer parallel wall time
separately. No standalone timing superiority is claimed.

Only two given primitives, two fixed durations, one initiation per game, small
source cohorts and three lifecycles are tested. The heldout roots were previously
inspected; the new evaluation streams provide the new deployment evidence. Preserve
all negative results. V83 is not promoted; U005 stays FAIL and U006 stays unstarted.
