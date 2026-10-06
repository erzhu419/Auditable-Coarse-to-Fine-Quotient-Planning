# V91: share H2 continuation consequences across terminating fragments

Frozen before V91 fitting or evaluation. V90 did not establish either stable
benefit or a uniform within-leaf transfer failure. This exploratory method test
changes the estimated learning target, retaining the same candidate selector.

## Learning algorithm and shared history

Use only the original V83 branch trajectories, separately for lives 0, 1 and 2.
At checkpoints 6 and 12 accumulate the corresponding original episode batches.
Episode modulo 5 equal to 4 remains excluded from every fit. No V89 additional
sampling, confirmation, natural evaluation, or V90 trajectories enter training.
Both learners receive identical complete roots and the same historical acquisition
cost. Old V83 source collection is also inherited acquisition cost; old selector
fits are not new work. There is no new training acquisition in this comparison.

MC uses complete eight-replica paired R/F/S means. DECOMPOSED uses, for each arm,
the first four active actions' direct R/F/S plus a learned H2 continuation vector
at the boundary. One-action fragments execute H2 for the next three actions;
four-action fragments finish their commitment. The reference executes four H2
actions. Terminal boundaries contribute their event once and have zero tail.
All four candidate advantages subtract the same reconstructed H2 outcome.

Learn H2 tails from complete branch games at step indices 4,20,36,... plus the
last active step when not already included. Targets are remaining score/2048
and eventual LOST/WON, jointly. At these states every option has returned to H2.
Each trajectory's tail-row weights sum to one. Correlated rows are supervised
examples, not independent episodes. A censored root supplies neither learner
with labels or tail supervision, while all of its acquisition cost remains.

One tail tree per query shares 36 observed-board features across options:
DecisionTreeRegressor(max_depth=8,min_samples_leaf=16,random_state=9101), weighted
by the above trajectory weights. Query conditioning preserves the corresponding
H2 continuation policy. At each checkpoint, fit a full training-data model and
two models excluding respectively episode%2 == 0 or 1. Historical training-root
labels use the model excluding their entire episode's fold, including both
queries, all options and replicas. Internal heldout labels use the full model
for diagnostics only. No rows from an episode beyond the checkpoint enter.
This is batch historical relabeling at each checkpoint, not within-episode TD.

Fit MC and DECOMPOSED with the unchanged V84 JointSelector: one joint 36-to-12
tree per query, depth 3, min leaf 2 roots, random_state 8301, four fixed options
and exact zero H2 reference. Only the label source changes. Save both selectors,
all three tail models, reconstructed labels, fit episode rosters, work and time.
The initial checkpoint-6 selectors remain frozen for longitudinal controls.
No fitted tail model executes during deployment, so selector inference uses
the same representation and candidate mechanism for both methods.

## New games and independent outcome reference

At checkpoint 6 compare H2_ONLY, MC and DECOMPOSED. At checkpoint 12 additionally
compare MC_FROZEN_6 and DECOMPOSED_FROZEN_6. Per life/query/checkpoint use 16
natural replicas, fixed 2000-action cutoff: 768 planned games. Environment seed
is 9190000+checkpoint*10000+life*100+replica; execution model seed adds 1000000.
Methods share streams, rotate execution order, preserve pretrigger histories,
execute the selected commitment once, and use four execution model draws per
active action. Retain all raw games, selections, statuses and computation.

Before seeing their outcomes the reference-root rule is fixed: checkpoint 12's
first two natural H2 replicas per life/query, at the original observable trigger
(at most six empty cells). Save all twelve planned roots, including a missing
trigger if one occurs; do not replace roots. For each present root execute all
five options at exactly sixteen new paired replicas, terminal/2000 actions,
using V83 sample_root with life argument 91000+life and episode=natural replica.
Thus environment seed is 8310000000+(91000+life)*10000000+query_index*100000+
episode*100+replica; the model seed adds 1000000000000. Planned reference
trajectories=960. Their complete outcomes never update any model.

On these roots compare each final selector's four predicted advantages and
chosen option against the full sixteen-replica outcome means. Also reconstruct
direct-plus-tail outcomes from their first four observed steps, using the frozen
full tail model, to expose approximation error before selector fitting. Report
paired reconstruction residuals, reference uncertainty and residual means;
variance reduction alone is not success. Reconstruction variance conditions on
the fitted tail model and omits its training uncertainty; the sixteen-replica
terminal reference is also a finite-sample estimate. Shared H2 and correlated
candidate observations are not independent replication units.

## Interpretation and cost

Primary behavior comparisons: DECOMPOSED minus MC, each versus H2, and checkpoint
12 updates versus their own frozen-6 models on the same fresh streams. Average
life-level query effects equally; report each life. Separate newly enabled,
disabled, changed-fragment, same-fragment and both-H2 decisions. Improved return
through cancelled interventions alone is not new useful knowledge.

All planned games are attempted; no outcome-dependent stopping or replacement.
Incomplete root outcomes remain unlabeled. Retain costs and missing counts;
full-cohort primary interpretation requires all planned terminal outcomes.
Internal heldout observations were examined in prior versions and are not new
sealed validation. New reference boards/streams supply this version's independent
comparison. The fixed three histories are an exploratory longitudinal test, not
proof of general continual learning or savings in acquisition. Count preprocessing,
tail fits, head fits, natural evaluation and independent reference sampling
separately; charge the shared historical trajectory acquisition to both methods.
Freeze all parameters without selection on V91 outcomes. U005 FAIL; U006 unstarted.
