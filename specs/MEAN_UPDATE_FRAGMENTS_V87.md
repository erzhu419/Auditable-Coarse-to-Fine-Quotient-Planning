# V87: update the mean intervention value while fixing candidate differences

Frozen before V87 fits, retained-label diagnostics, or new natural games. V86's
two budget allocations improved some prediction errors but did not beat H2.
This tests the previously frozen common mean using both allocation datasets.

## Mean-only learning

For each lifecycle 0/1/2 and allocation COVERAGE/REPEAT, load V86's saved centered
selector and its complete training_rows.jsonl.gz. Keep its residual trees and
the original non-H2 option ranking fixed. Fit one new three-output mean R/F/S
tree per query to the within-root average of the four candidate targets. Use
the same 36 board features, depth 3, minimum leaf size 2 roots, random_state 8301,
and episode%5==4 exclusion. Each root supplies one mean target vector; repeated
root means retain V86's weighted combination and do not become extra roots.
The checkpoint value 12 identifies the source model, not new acquisition.

At inference compute all four source predictions, their common component mean,
and the new mean. Add the same vector shift to every candidate. Choose the best
allowed non-H2 candidate using the original source utility order and original
tie priority, then execute it only if its shifted utility is strictly positive.
This explicitly preserves ranking even if floating-point addition collapses a
small score difference. H2 remains exactly zero. Keep source ranking values in
the prediction record; actual reported values use the shifted R/F/S vectors.
All four candidates participate in centering before any allowed-set restriction.

Only the mean trees are newly fitted. Saved models contain the original selector
and the new mean trees. Count original-selector traversals and the additional
mean-tree traversal. The mean-only fit has the same depth/leaf limits as the
original joint fit, but a different target and partition objective; it is not a
test of data age alone. Save all models, rows, and fitting logs before evaluation.

## New paired deployment, retained diagnostics

Methods: H2_ONLY, COVERAGE_OLD, COVERAGE_MEAN, REPEAT_OLD, REPEAT_MEAN. OLD loads
the corresponding unmodified V86 selector. Use eight natural games per query and
lifecycle, totaling 240 games. Seed=8790000+life*100+replica, replica=0..7; model
seed adds 1000000. Pair all methods and queries by seeds and rotate method order.
Keep the original V83 controller, first active board with at most six empty
cells, one committed one/four-step fragment followed permanently by H2, four
model draws per active action, and terminal/2000-action stop. Run three lifecycle
workers concurrently with serial methods inside each worker.

Primary contrasts are each MEAN minus its OLD model and minus H2. Use one common
five-method terminal cohort per query/lifecycle, retaining cutoffs and costs.
Average differences within lifecycle, then equally across lifecycles.

At the common trigger classify each OLD/MEAN pair as enabled (H2 to fragment),
disabled (fragment to H2), both_h2, or same_fragment. Verify that every MEAN
intervention uses the original best non-H2 candidate. Both unchanged-choice
categories must have identical complete histories. Report category frequencies,
conditional effects, and contributions divided by the full common cohort size,
so contributions sum to the overall MEAN-minus-OLD effect. Disabled benefits
are H2 recovery; an enabled intervention's MEAN-minus-H2 effect measures its
additional strategy contribution. Do not call more abstention a new strategy.

Reuse V86's 24 retained validation roots and sixteen-replica means for diagnostic
mean error, unchanged residual differences/ranking, gate changes, and selected
observed utility. These roots have already been inspected and informed the
hypothesis; they are not new independent validation. Do not refit or tune from
them. Only the fresh natural games supply new deployment evidence.

## Costs and scope

New source/branch acquisition is zero. Count twelve new mean trees and actual
evaluation work (at most 480000 transitions). Reuse V83 acquisition, V84/V85
construction, and each V86 allocation's acquisition/fitting separately. Exclude
past validation/evaluation from model construction; copied retained diagnostic
data are not newly sampled. Shared method attributions are not additive actual
wall time. Retain development-test costs separately.

This isolates an intervention-value update in one-initiation supplied fragments,
on three lifecycles. Candidate ranking cannot improve by construction. Preserve
negative outcomes and do not change means, thresholds, candidates, or seeds after
seeing outcomes. U005 stays FAIL; U006 stays unstarted.
