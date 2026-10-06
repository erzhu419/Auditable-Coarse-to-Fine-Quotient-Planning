# V78: decision-driven acquisition and whole-knowledge acceptance

Frozen 2026-09-13 before collecting V78 branch trajectories or evaluation games.
V77 established a persistent learner but partition revision hurt reward-query
games despite its prediction-loss acceptance rule. V78 tests a different rule:
accept an entire candidate only when paired deployment rollouts improve decisions.

## Fixed experience and candidate

Reuse the immutable V77 natural training games for lifecycles 0, 1, 2 and the
common FROZEN model at 15 episodes. Reveal episodes chronologically at 39 and
75; never consume V77 evaluation games. Dynamics, features, continuation
policies, tree parameters and the 32-action planner remain V77's.

At each stage, inspect four evenly spaced observations in each newly completed
training game (indices floor(k*(length-1)/3), k=0..3), in episode/index order.
A root is eligible when the frozen warmup planner and H2_ONLY select different
actions under either of the two unchanged queries, using paired model uniforms.
Keep the first 12 distinct training roots and 8 distinct validation roots;
episode%5==4 defines validation. Fewer available roots are retained as such.
The same procedure selects up to 8 old validation roots from the warmup prefix;
after stage one its new validation roots become stage two's old roots. This
fixed-selector disagreement sampling uses observed states across game progress.

For every training root, run each legal first action, followed by each of
GREEDY, SPACE, SNAKE, with two common random streams. Each branch takes at most
32 actual simulator transitions. Only anchor-zero horizon-30/31 consequences
are added to training, excluding the first action's reward. Terminal events
absorb; incomplete administrative-cutoff windows are omitted. Every method
receives the same cumulative natural and branch training records. These are
generative-environment resets to encountered states, not ordinary single-path
interaction. No full spawn-support teacher is queried.

Fit one common three-policy candidate per stage from cumulative training rows,
using the unchanged V77 tree recipe. FIXED updates only warmup leaf statistics.
FROZEN keeps warmup knowledge. MSE and DECISION each compare the common candidate
against their own entire pre-update incumbent, with no implicit leaf refresh.

## Acceptance and held-out games

MSE accepts if mean joint-vector error on new natural validation rows strictly
improves, while old error is at most incumbent*1.02+1e-12. This is whole-model
acceptance and therefore not an exact replication of V77's per-policy update.

For DECISION, execute candidate and incumbent from each old/new validation root,
for both queries and two paired environment streams, each for at most 32 actions.
Every step uses the deployed depth-two planner, so the acceptance comparison
includes receding-horizon action changes. Scalar utility is observed score/2048
minus 4*failure plus 4*success for risk_goal, or score/2048 for reward. Events
outside the 32-action window are not assigned labels. For each query separately,
new-root mean candidate-minus-incumbent utility must be nonnegative, at least
one query must strictly improve, and both old-root query means must be
nonnegative. All four strata require observations. Reject the whole update
otherwise. This is an empirical acceptance rule, not a confidence certificate.

At checkpoints 39 and 75 run H2_ONLY, FROZEN_PLAN, FIXED_PLAN, MSE_PLAN and
DECISION_PLAN from two new natural-game seeds per lifecycle, under both queries:
7890000 + lifecycle*100 + replica (replica 0,1). These 120 full evaluation games
start with two normal tiles and end WON/LOST or CUTOFF at 2000 actions. They
never affect root selection, fitting or acceptance. Model and environment RNGs
are separate. Seeds are shared across methods and checkpoints. Rotate method
execution order. Primary comparison is final DECISION minus MSE and FIXED by
query and independent lifecycle; report the intermediate checkpoint as well.

Training branch seeds are 7810000000 + lifecycle*10000000 + stage*1000000 +
root*1000 + replica. Acceptance seeds are 8820000000 + lifecycle*10000000 +
stage*1000000 + stratum*100000 + root*100 + replica, with old/new strata 0/1.
Action, policy, query and candidate identity are omitted intentionally for
paired streams. Acceptance model seeds add 1000000000000; evaluation model
seeds add 1000000. Selection seeds are 780000000 + lifecycle*10000000 +
episode*10000 + step*2 + query_index. These main-lifecycle namespaces are disjoint.

## Budget, evidence and interpretation

New training branches use at most 12*4*3*2*32=9216 simulator transitions per
stage/lifecycle. Acceptance uses at most 16*2*2*2*32=4096 more. Across six stages,
the ceiling is 79,872 new branch transitions, excluding whole-game evaluation.
Early true terminals reduce actual counts; report actual samples, not only caps.
Frozen/H2 do not need acquisition. FIXED/MSE use the shared training branches;
DECISION additionally pays its paired acceptance trajectories. Attribute common
fit cost fully to both MSE/DECISION while reporting actual executed cost once.
Record inherited V77 source work separately from newly executed work. A shorter
failed game is not evidence of better efficiency.

Selection uses a common frozen disagreement detector and a prescribed policy
library; V78 does not invent exploration policies. Success coverage and terminal
outcomes must be reported. Local acceptance need not improve distant closed-loop
outcomes, and three lifecycles do not support precise population claims. Keep
rejections and adverse query effects; do not retune after seeing main results.
U005 remains FAIL; U006 remains unstarted.
