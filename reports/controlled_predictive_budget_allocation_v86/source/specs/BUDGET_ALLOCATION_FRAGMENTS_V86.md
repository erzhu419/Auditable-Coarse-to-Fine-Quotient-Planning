# V86: spend equal new interaction budgets on coverage or repeated estimates

Frozen before any V86 acquisition, model fitting, or evaluation. V85 improved
reward over JOINT on its new streams but did not establish continued-learning or
multi-step benefits. This experiment compares two data allocations, keeping the
V85 residual estimator, features, four candidates, utility rule, and controller.

## Shared starting knowledge and exact acquisition budgets

For each lifecycle 0/1/2 start with V85's checkpoint-12 cumulative V83 rows and
saved centered selector. Keep its V84 anchor fixed in both updated models. Refit
only the centered residual tree, with the existing depth 3, leaf minimum 2 roots,
random_state 8301, and episode%5==4 exclusion. The selector checkpoint remains
12 to identify this fixed anchor; it is not the new source-episode count.

Each allocation receives exactly 120000 new sampled environment transitions per
query and lifecycle: 1440000 training-acquisition transitions overall. Charge
source and branch games together. Pass the remaining budget to each trajectory
as its step ceiling, also respecting the existing 2000-action ceiling. Stop at
zero; do not add unused or padding interactions to manufacture matched counts.
Retain all raw trajectories and costs. A training block supplies labels only if
all five options times eight replicas finish terminal; incomplete/censored blocks
are not fitted. Their work still consumes the budget. No post-outcome replacement
budget. Report complete-block data yield and all excluded work.

- COVERAGE: collect new H2 source games in fixed index order, retain each first
  active board with at most six empty cells, and sample one eight-replica block
  for its four fragments and H2. Source games finish or hit the remaining cap.
  New training episode IDs start at 100, skipping IDs equal to 4 modulo 5.
  Add complete roots to the unchanged old labels. A failed block is retained,
  then the next source index is used if budget remains.
- REPEAT: revisit only the ten original training roots per query. Sort by episode
  and rotate the initial root by (lifecycle+query_index) modulo ten, then cycle
  round-robin without looking at outcomes. Add eight-replica blocks with fresh
  suffixes. Combine a successful block with the root's existing mean weighted by
  its actual replica counts (initially eight); never count a new mean as eight
  new independent roots. No new source game is needed for an existing root.

Training source seed=86000000+life*100000+query_index*10000+source_index.
Branch seed base=86000000000+life*1000000000+query_index*100000000
+allocation_index*10000000+block_index*100, with COVERAGE=0 and REPEAT=1;
add replica 0..7. Source model seeds add 1000000; branch model seeds add
1000000000000. Within a replica all five options use identical environment/model
seeds, and all active controller actions consume four model uniforms.

Both updated models retain the same old heldout rows for existing fit diagnostics.
Neither receives any new validation or evaluation label. Fit and save both models,
their complete training rows, logs, and the unchanged frozen baseline before
collecting the independent validation or natural-game outcomes.

## Independent validation and natural games

Collect four fresh H2 source roots per query/lifecycle, fixed indices 0..3 and
episode IDs 1004+5*index. Source seed=86900000+life*100000+query_index*10000+index.
Sample 16 paired replicas per root with branch seed base=96000000000
+life*1000000000+query_index*100000000+index*100. Keep all results and costs
separate from the matched training budget. A missing trigger or any nonterminal
branch excludes the whole root from all three model comparisons. No replacement
roots. These are independent source games, not a guarantee of unique board values.

Diagnose FROZEN_V85, COVERAGE, and REPEAT on the same complete validation roots:
six candidate-pair and two within-primitive duration orderings, selected observed
utility, negative interventions, residual/full-vector error, and fixed-mean
discrepancy. Compare the first eight and last eight paired replicas to measure
reference-order repeatability. Sixteen-replica means are noisy estimates, not
exact action values; within-root pairs are dependent. Diagnostics cannot tune or
select a model for the following evaluation.

Natural games use H2_ONLY, FROZEN_V85, COVERAGE, REPEAT, with eight replicas per
query/lifecycle: 192 games. Seed=8690000+life*100+replica; model seed adds 1000000.
Pair all methods and queries by seed, rotate method order, and retain full
histories. Use the unchanged first-six-empty-cell trigger, one committed
one/four-step fragment followed permanently by H2, and terminal/2000-step stop.
Three lifecycle workers run concurrently; each worker executes methods serially.

## Comparisons and decision scope

Primary comparison is COVERAGE minus REPEAT, then each updated model minus
FROZEN_V85 and H2. Use one common four-method terminal cohort per query/lifecycle,
retaining cutoff outcomes and costs. Average paired utility/score differences
within each lifecycle, then equally across lifecycles. Report fixed mean/prefix,
commitment, draw alignment, full-history changes, wins/losses, and data yield.
Any broken budget/cohort/controller condition invalidates its comparison.

Count actual new acquisition, validation, fitting, and evaluation separately;
inherit shared V83 acquisition and V84/V85 construction without rerunning them.
Method attributions are not additive wall time. Validation costs are shared
research costs, not training data available to either allocation. Maximum new
work is 1440000 training transitions + 48000 validation-source transitions +
3840000 validation-branch transitions + 384000 evaluation transitions.

This compares two allocations at one new budget on three existing lifecycles.
A favorable allocation is not proof that it is the unique cause of prior errors,
nor evidence for unrestricted strategy learning. No model/threshold/seed tuning
after outcomes. U005 stays FAIL and U006 stays unstarted.
