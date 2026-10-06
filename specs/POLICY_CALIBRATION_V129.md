# V129: source-only policy-value calibration

V128 found different scalar-anchor biases across source policies. Test a
single learned offset per source while preserving each source's proposed
action. U005 remains FAIL; U006 stays unstarted.

## Frozen learner and policy interface

Use the four V120 final4096 source histories and final V127 success counts.
For each life/policy replay all1024 original V126 fixed-policy training games.
For every non-goal afterstate, pair the original source Q (current swipe score
plus frozen afterstate value) with the actual source-query suffix return,
including the current swipe exactly once. Fit

    b_policy = sum(suffix_utility - Q_source) / eligible_afterstates.

All eligible occurrences receive equal weight. Goal afterstates have known
returns and are excluded. A cutoff excludes its whole episode from fitting,
with read/replay work retained. No shrinkage, clipping, fitted slope, query-
specific offset or held-out tuning. Weights and event counts stay read-only.
Retain episode sufficient statistics and freeze all eight offsets before any
new environment acquisition. V128 outcomes do not enter fitting or selection.

At each decision, each source first proposes exactly its V127 single-policy
candidate under LEARNED or CONSTANT success prediction, with the original
lexicographic tie rule. Compare only these two candidates, using original
candidate value plus that source's offset. An immediately winning candidate
keeps its exact score/2048+query goal bonus. Tie order remains comparison
value, action name, source index. UNCAL uses zero offsets. Calibration never
reorders actions inside a source. This is calibration of the cross-policy
candidate comparison, not a new maximization over all shifted action values.

## Fixed fresh evaluation and budgets

Queries risk1=(reward1,failure1,goal1) and risk8=(1,8,8); policies reward=(1,0,0)
and risk_goal=(1,4,4); four lives; p4=.1; goal rank11; maximum2000 swipes/game.
All streams use BASE=129*100000000 and have disjoint namespaces:

- Root acquisition:2 source games per life/policy, seed=BASE+10000000+
  life*100000+replica, paired across source policies.16 actual games.
  Take the pre-action boards at zero-based indices128 and512. Keep all32
  case slots; an unavailable board is missing, without replacement/imputation.
- Deduplicate available roots by exact (life,board), ID in first-encounter
  life/policy/replica/index order. The action set is the sorted union of the
  two policies' original candidate actions over both queries and both modes.
  Store all legal-action Q/S/afterstate/score predictions. Save the complete
  roster and exact budget before any forced continuation.
- For each root/action/source policy acquire8 forced-first continuations,
  then follow that source under its original query. Seed=BASE+50000000+
  root_id*1000+replica, paired across actions/policies. No initial spawns;
  spawn after each swipe, including a winning one. Maximum2048 attempts.
- Full control:8 replicas/life/query for UNCAL_LEARNED, CAL_LEARNED,
  UNCAL_CONSTANT and CAL_CONSTANT, plus8 original-policy games/life/policy
  reused as both-query source baselines.320 actual games. Seed=BASE+
  90000000+life*100000+replica, paired across methods, policies and queries.

No outcome-dependent extension or replacement. Costs include root acquisition,
forced continuations, full control, replay, fitting, loading and setup. Old
V120/V126/V127/V128 costs remain separately inherited; model samples are0.

## Comparisons and completion

On the fresh fixed panel compare UNCAL/CAL policy-conditioned source-anchor
errors and same-action cross-policy gap errors. Also compare actual paired
query returns of each method's two-policy selected candidate, using its
corresponding forced-action/fixed-policy branch. These diagnostic selections
use predictions only, never the sampled return. Aggregate paired replica
values over available cases within life, then four lives equally; repeated
root aliases retain covariance. Report Monte Carlo standard errors, without
population confidence claims. Missing/cutoff branches suppress affected
full-return comparisons and retain their costs.

Full-game primary comparison is CAL minus UNCAL within each mode/query,
first within life then equally over four lives. Also compare each mode's
calibrated readout to the two frozen source baselines. Preserve all histories
and cutoffs. Record source selections and original/shifted candidate scores;
independently verify offsets, fixed candidate comparison, rosters, seeds,
immutable sources and actual accounting. Tests cover suffix arithmetic,
analytic goals, unchanged source proposals, zero-offset equivalence, paired
summaries and alias handling. Freeze code/protocol before the one main run.

## Limitations

One global offset may not transfer across game stages or action distributions.
Correcting cross-policy bias does not fix within-policy success-difference
errors. Forced source continuations and repeated adaptive control measure
different effects. Four source histories and eight suffix/control replicas
cannot establish general strategic learning or resolve every small effect.
