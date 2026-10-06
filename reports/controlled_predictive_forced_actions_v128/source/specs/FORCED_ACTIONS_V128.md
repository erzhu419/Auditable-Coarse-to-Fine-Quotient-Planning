# V128: paired forced actions at retained first divergences

V127 preserved source-query behavior and improved source-path Brier error,
but unseen-query action corrections degraded control. Diagnose the exact
policy-conditioned action comparisons before changing the learner again.
U005 remains FAIL; U006 stays unstarted.

## Fixed cases, predictions and sampling

Take all64 final-prefix V127 pairs: four lives, queries risk1/risk8, eight
replicas, LEARNED_risk_goal versus CONSTANT_risk_goal at1,024 source games.
For each pair recover its first unequal action after the identical retained
prefix. Keep no-divergence cases in the roster; do not impute measured gaps.
No screening by predicted advantage, observed outcome or board difficulty.

Group divergent cases by exact (life, board). For each root take the union
of its cases' two selected actions, ordered lexicographically. Repeated
cases/queries share the same physical action samples. Assign root IDs in
first encounter order (life, query risk1 then risk8, original replica).
Before drawing any new samples, save every case, root, prediction and budget.

Load the two fixed V120 final4096 scalar policies and their final V127 event
counts for each life. Retain each root/action's original scalar Q, predicted
success, immediate score and afterstate for both continuation policies.
Reproduce the retained learned and constant choices on every divergent root.
Models remain unchanged and read-only. No new fitting or GPI execution occurs.

For each unique root/action and each of the two source continuation policies,
run16 fresh terminal continuation attempts from that root. Force the specified
first action; from the next state onward use that source policy under its own
original query. Source continuation order is reward,risk_goal. Root suffix
seed=128*100000000+90000000+root_id*1000+replica; the seed is shared across
actions/policies and differs across roots/replicas. Spawn location/rank draws
are paired uniform draws, p4=.1, including after the forced swipe. There are
no initial spawns. Stop at the first goal/loss or2,000 total swipes including
the forced one. Charge all actual transitions, even in cutoff branches.
Maximum4,096 physical attempts; exact count follows the frozen deduplicated
roster. No outcome-dependent extensions or replacement draws.

## Error decomposition

For each case let delta mean learned-selected action minus constant-selected
action, with continuation policy fixed at risk_goal. Source penalty/bonus are
4,4 and reward weight1. Let k=(new_failure+new_goal)-8. Then

    true delta Unew = true delta Usource + k * true delta S
    predicted delta Unew = delta Qsource + k * predicted delta S
    prediction error = (delta Qsource - true delta Usource)
                       + k*(predicted delta S - true delta S).

Scores include the forced action exactly once; success/failure count the
first terminal event. Estimate both terms from paired suffix outcomes, not
from independent maxima of incompatible policies. Retain continuous margins
including tiny or zero predicted differences; do not select a replacement
root when its first disagreement is nearly tied.

Also compare both policies on each SAME root/action: original scalar error
against that policy's actual source-query continuation utility, success
prediction error, and anchored new-query policy differences against actual
new-query differences. This distinguishes source-value offsets from success
corrections; it does not assume the policies' approximate values are comparable.

Report case-level paired differences and their Monte Carlo standard errors,
then equally weighted case means within life/query and four-life means.
For aggregate Monte Carlo error, aggregate each paired replica across the
fixed cases first so repeated-root aliases remain correlated. No population
confidence or new-policy full-game effect is inferred from this selected panel.
Any cutoff suppresses the affected full-return comparison, with cost retained.

## Verification and costs

Test prefix reconstruction, forced-first semantics, terminal/cutoff accounting,
paired RNG use, immutable model loading, exact error decomposition and shared
sample aliases. Independently verify roster/predictions, branch seeds and
traces, unchanged source updates, exact physical counts and paired summaries.
Do not repeat millions of native weight updates or continuations for auditing.
Retain source/protocol/code before the single preparation and sampling run.

Separate inherited V120 learning, V126 acquisition/fitting and V127 processing
from new preparation (prefix replay, model loads and predictions) and new
continuation acquisition. Model-generated samples and training updates are0.
All outputs, tests and build files remain inside the research worktree.

## Limitations

The roots were selected by earlier action disagreement, not a new population
of games. Each branch follows a frozen source policy after its forced action;
it does not evaluate continued V127 adaptive control. Sixteen paired suffixes
can leave small action differences unresolved. Approximate anchors and local
success features may both be wrong, even when source-path average error falls.
