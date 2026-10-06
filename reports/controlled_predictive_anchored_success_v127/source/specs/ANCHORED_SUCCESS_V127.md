# V127: preserve source value and learn query differences

V126 failed own-query control and source-path probability prediction. Preserve
that result; retain U005 FAIL and U006 unstarted. V127 tests an anchored
decomposition and a bounded empirical event learner, rather than fitting a
new unconstrained three-component value from zero.

## Fixed representation and readout

Each of four lives inherits its two V120 final4096 scalar policies and the
identified swipe program. Source weights remain read-only. For reward weight1,
source penalties/bonuses fs,gs and new f,g, a nonwinning afterstate uses

    Qnew = Qsource + fs - f + [(f+g)-(fs+gs)] * S_policy(afterstate).

Qsource includes the immediate swipe score once. Complete games have F=1-S.
Winning tails use S=1 and the new analytic goal bonus. For the original query,
return the original source action values without arithmetic reconstruction;
single-policy actions and complete histories must match the source exactly.
Other reward weights are outside this experiment. The source scalar is an
approximation; the identity preserves its action values, not exact true returns.

Learn S separately per fixed source policy using V120's four six-cell patterns
and eight symmetries. Each eligible observed afterstate adds one visit and its
terminal success indicator to each UNIQUE feature address. Duplicate symmetry
occurrences within an afterstate are not extra trials. Prediction averages all
32 feature occurrences of (feature_wins + prefix_global_rate)/(feature_visits+1).
The global rate is successful eligible afterstates / all eligible afterstates
for that policy's training prefix (default .5 when empty). This is a bounded
smoothed frequency estimate, not a claim of independent Bernoulli evidence.
Analytic winning afterstates receive no fit; entire cutoff games receive no fit.
No clipping, bootstrap, weight tuning, model selection or additional replay epochs.

## Data and frozen experiment

Reuse all8,192 V126 training attempts, in their original order, at prefixes256
and1,024 games per policy/life. Reconstruct afterstates from recorded actions
and spawns through the identified swipe program, checking scores and final
boards. This is processing retained data, not new environment acquisition.
Record replay and feature-update costs. Keep V126 acquisition and original fit
costs, plus V120 training22,124,667 transitions, as inherited costs; no refund.
V126 fitted models and outer games are not inputs to V127 fitting/evaluation.

Readouts are LEARNED_reward, LEARNED_risk_goal and LEARNED_GPI, with matched
CONSTANT_reward, CONSTANT_risk_goal and CONSTANT_GPI controls using the same
training-prefix global rate. GPI maximizes complete policy-conditioned scalar
values; ties use lexicographic action then policy order reward,risk_goal.
All six are evaluated at both prefixes on reward=(1,0,0), risk_goal=(1,4,4),
risk1=(1,1,1) and risk8=(1,8,8). The last two weights remain unseen in fitting.

Use8 fresh natural games per life/query/method/prefix, p4=.1, goalrank11,
max2000 steps. Outer seed=127*100000000+90000000+life*100000+replica, pairing
all methods/queries/prefixes; no V126 seed reuse. Evaluate each frozen source
policy once per life, under its own original query, then reweight its retained
score/status for the other query comparisons. All own-query anchored games
are actually executed, to test complete action-history equality. Total1,600
physical outer games /2,048 logical comparison entries. All evaluation is
read-only. Do not replace cutoffs or extend sampling after outcomes.

On these fresh frozen-policy paths, retain S predictions at both prefixes and
compare Brier error with the corresponding training-prefix constant. This
diagnosis uses the matching continuation policy and excludes analytic goals.
No evaluation outcome may update source weights or event counts.

## Outcomes and verification

Primary final contrasts, separately per query: each LEARNED readout against
its matching CONSTANT readout; LEARNED_GPI against both frozen sources and
both single-policy learned readouts. Also show256-to1,024 change. Average
replicas within life, then lives equally; report all four effects and wins.
Source-history recovery is an engineering identity, not transfer evidence.
Any outer cutoff leaves the full-game primary result incomplete.

Before one formal run, freeze protocol/code and test exact same-query values,
joint-policy GPI, recorded-transition reconstruction, unique-feature counts,
bounded probabilities, terminal handling and readonly evaluation. Independent
analysis reconciles retained labels/prefixes, sparse count snapshots, native
work, source immutability, own-query histories, physical/logical rosters and
heldout prediction error. Do not repeat all native training updates merely
for verification. All artifacts remain inside this research worktree.

## Limitations

These queries vary one reward/success preference under fixed dynamics. V126
training and four V120 source histories are reused, while outer games are new.
Feature counts share correlated outcomes within games and average partial
patterns; boundedness alone cannot establish calibration. Anchor values remain
approximate, and GPI can amplify cross-policy estimation error. No hard-risk
constraint or general world-model composition claim follows from this test.
