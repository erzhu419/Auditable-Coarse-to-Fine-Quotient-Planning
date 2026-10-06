# V85: separate candidate ranking from the fixed mean intervention estimate

Frozen before V85 fitting, retained-label diagnosis, or evaluation. V84 removed
forced candidate ties but did not improve reward or establish a learning benefit.
This experiment tests whether fitting relative candidate consequences separately
improves selection. It does not assume that the common H2 reference caused V84's
errors.

## One changed estimator

Reuse the saved V84 cumulative paired_rows.jsonl.gz at each lifecycle 0/1/2 and
checkpoint 6/12, containing the original V83 eight-replica terminal differences.
No new source episodes or training branches. Keep the four options, 36 observed
board features, episode%5==4 heldout split, tree depth 3, minimum leaf 2 complete
roots, and random_state=8301.

For each root and R/F/S component, let d_j be candidate j's retained advantage
against H2. Fit a new 12-output tree to c_j=d_j-mean_k(d_k). The shared H2 term
cancels from c_j, while relative candidate consequences remain. Do not fit to
deployment games or use heldout diagnostics to choose settings.

Load the corresponding V84 joint model without refitting. At inference compute
m=mean_j(V84_j(state)), then predict
dhat_j=m+chat_j-mean_k(chat_k). All four candidates participate in centering even
when the allowed execution set is restricted. Thus every component's candidate
mean is held at its existing V84 value for that checkpoint. H2 remains exactly
zero; selection uses the original weighted R/F/S utility, strict positive
improvement, and fixed option order. Freeze both the anchor and residual trees
from checkpoint 6 for the frozen arm. Saved selectors contain both trees.

This adds a residual partition to an existing anchor partition. It is not an
equal-capacity comparison. The mean is fixed between V85 and V84 at a checkpoint;
both checkpoints still use their respective V84 anchors, so learning-curve changes
can involve both anchor updates and residual updates.

## Fresh paired execution and controls

Use the unchanged V83 FragmentController: the first active board with at most six
empty cells triggers one selection; commit SPACE/SNAKE for one or four actions,
then permanently return to H2. Every active action consumes four model uniforms,
including unused uniforms during deterministic fragments.

Methods: H2_ONLY, CENTERED, CENTERED_ONE_STEP, CENTERED_FROZEN6, JOINT,
FIXED_SPACE4. JOINT loads the corresponding V84 model. CENTERED_ONE_STEP restricts
the same current centered model to H2/SPACE_1/SNAKE_1. All games start from the
normal two tiles. Seeds are 8590000+lifecycle*100+replica, replicas 0..7; model seed
adds 1000000. Share seeds across all six methods, queries, and checkpoints; rotate
method order. Use three independent lifecycle workers, sequential methods within
each worker. Stop at WON/LOST or 2000 actions and retain full action histories.

There are 576 evaluations, at most 1152000 new transitions. Save each checkpoint's
models, data, and fitting logs before its evaluation. No model or setting changes
after viewing outcomes.

## Interpretation and accounting

Primary final comparisons are CENTERED minus JOINT, H2, ONE_STEP, FROZEN6, and
FIXED_SPACE4. Use one common complete six-method terminal cohort per
lifecycle/query/replica. Retain cutoffs and costs but exclude a cutoff replica
from all terminal comparisons. Average paired differences within each lifecycle,
then equally across the three lifecycles. Report checkpoint changes, full-history
agreement with H2, selections, realized commitments, terminal outcomes, and costs.
Verify shared prefixes, commitment lengths, one initiation, aligned model draws,
fixed controls, and first-checkpoint frozen/current equality; a failure invalidates
the affected comparison rather than being treated as scientific evidence.

After execution compare candidate and duration ordering against the retained
means, separately for training/heldout roots. Record fixed-mean discrepancy,
anchor mean error, residual error, observed utility of selections, and ranking
disagreement with JOINT. The previously inspected heldout roots are diagnostic;
their eight-replica labels are noisy and their within-root pairs are dependent.

Count actual new residual fits and evaluation once. Inherit V83 source/branch
work and the V84 joint model's cumulative preparation/fitting/export separately;
exclude V83/V84 evaluation. CENTERED and ONE_STEP share construction attribution;
FROZEN6 pays only checkpoint-6 construction; JOINT pays inherited construction
and its new load/evaluation. Attributions across arms are not additive actual
execution. Report outer parallel wall time separately. Development test sampling
is retained separately from the campaign.

Only four given fragments, one initiation per game, and three small lifecycles
are tested. Preserve negative results. U005 stays FAIL; U006 stays unstarted.
