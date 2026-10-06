# V137: terminal supervision on matched frozen-teacher trajectories

V136 joint one-step learning degraded old-query control and held-out reward
prediction. This experiment isolates replacing its bootstrap targets by full
terminal outcomes. Keep all four histories, SINGLE/CAPACITY, and each fixed
risk1/risk8 H2 teacher. No new query, representation, rate, policy selector,
training environment sampling, or source-parameter changes.

## Matched training

Reference the V136 training traces in place. They contain 8,582 complete
episodes, no 2,000-action cutoff, and 16 final ACTIVE prefixes. Exclude the
ACTIVE prefixes from BOTH learners. Retain every complete episode in its
original chronological order; one pass, no shuffling, repetitions or model
selection. Reconstruct recorded afterstates with recorded actions and spawns,
without drawing randomness. Charge deterministic reconstruction separately.

Instantiate TD and TERMINAL from the same V134 teacher leaf using unchanged
V136 PolicyComponents: reward source initialization, S=.5, complementary
failure, same32 feature occurrences, alpha=.0025 and two parameter heads.
Use identical eligible afterstates and numbers of joint updates. TD reads
both next-afterstate heads before updating the previous afterstate, exactly
as V136. Numerically compare all retained pre-values, predictions and targets
against the complete V136 prefix; any mismatch is an implementation failure.

TERMINAL uses R_i=sum of action rewards strictly AFTER afterstate i, divided
by2048, and S_i=1 if WON else0. The winning action's reward belongs to earlier
afterstate targets; the winning afterstate itself is analytic and never fit.
The final losing afterstate targets(0,0). Apply eligible updates in the same
chronological order as TD. This is delayed episode-end consolidation, not a
causal online decision update. Goal states remain outside the table domain.

Read each source episode once for both arms. Retain compact numerical
prediction/update records, counters, source references and excluded-prefix
counts. Save only each arm's final model; initialization is reconstructed
exactly from its source. Match updates, but report actual target construction,
prediction, lookup, reconstruction, memory and runtime costs independently:
equal updates do not imply equal total compute.

## Frozen evaluation

All16 teacher pairs finish training and freeze before any evaluation. Only
the teacher's own original query is evaluated. Methods are TEACHER,
INITIAL_H2, TD and TERMINAL. INITIAL_H2 aliases TEACHER only after exact
all-legal-root-Q and chosen-action equality on every teacher decision.

Use16 fresh paired replicas per history/representation/teacher/method.
BASE=137*100000000; evaluation seed=BASE+90000000+life*100000+replica.
Actual environment p4=.1, two initial spawns, goal rank11, max2000 actions.
Keep each history's frozen estimated spawn law for all H2 planning, including
the actual spawn after a winning action. No replacement of cutoffs.

This is768 physical games (256 each TEACHER,TD,TERMINAL),1024 logical records.
Primary old-query utility comparisons are TERMINAL-minus-TD and each arm
minus TEACHER; pair seed, mean within history, then equally over four histories.
Keep all16 source identities, no best-teacher choice. A cutoff censors its
affected terminal-return comparison while retaining all work.

On each of the256 newly evaluated teacher trajectories, predict INITIAL_H2,
TD and TERMINAL R/S on every non-goal afterstate, after training is frozen.
Compare reward MSE, success Brier and old-query recomposed MSE against the
observed reward suffix and terminal label. Average within game, then within
history, then equally across histories. This diagnostic uses no extra real
samples. Its predictions are separately charged and never fitted.

## Interpretation

Terminal supervision improving held-out predictions and old-query control
would support an obstacle in one-step target propagation under this optimizer.
Prediction-only improvement is not control success. A negative result does
not identify representation capacity alone: terminal-target variance,
optimization, shared features and generalization remain possible causes.
V133 used a fixed32-step bootstrapped tail under different evolving policies;
it is not this same-data, fixed-policy terminal comparison.

Preserve inherited V136 acquisition/teacher costs, all failures, validation
attempts and actual new evaluation work. Tests use finite fixtures, no pilot
games. U005 remains FAIL and U006 remains unstarted.
