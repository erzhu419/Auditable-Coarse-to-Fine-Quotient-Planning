# V126: fixed-policy consequences for unseen queries

V125 completes context protection without consistent policy benefits. Freeze
that branch. Test the MD's next central requirement: reuse experienced
consequences under new query weights. U005 remains FAIL; U006 stays unstarted.

## Fixed learner and source

Use the four retained V120 final4096 source histories. Each supplies its
reward policy and risk_goal policy, unchanged, plus the identified swipe
program. Keep dynamics fixed at p4=.1, goal rank11 and natural terminal games.
No V121--V125 learned weights, training trajectories or evaluation outcomes
enter this experiment. Inherited V120 training22,124,667 transitions and the
deterministic-program acquisition remain separately charged.

Each frozen policy gets a new, initially zero, three-component afterstate
n-tuple learner: future score/2048, first failure, first success. Use the V120
four six-cell patterns, eight symmetries, float64, alpha=.0025 and repeated
feature multiplicity. After a complete game, update each eligible afterstate
once in chronological order against its actual future return vector. Exclude
the current action's score from its target. A winning afterstate is analytic
[0,0,1] and receives no update. A cutoff game contributes acquisition cost
but no fitted targets. There is no bootstrap, clipping, reshuffling, tuning
or query-specific retraining. All three heads refer to the same frozen
continuation policy; never combine separately optimal components.

Monte Carlo labels deliberately isolate consequence representation, coverage
and variance from sparse-terminal TD propagation. They are correlated within
games and may have high variance. This is a policy-evaluation branch, not a
claim that MC is generally preferable to TD.

## Frozen experiment and readout

Four lives x two source policies x1024 attempted training games; max2000
transitions/game. Evaluate at256 and1024 games; no replacement of cutoffs,
no extension. Realized transitions, successful labels and all costs are
reported. Training seed =126*100000000+1000000+life*100000+
policy_index*10000+episode, with fixed policy order reward,risk_goal.

Queries (reward_weight, failure_penalty, goal_bonus) are reward=(1,0,0),
risk_goal=(1,4,4), risk1=(1,1,1), risk8=(1,8,8). Last two are unseen weights.
For each legal swipe, score the whole policy-conditioned vector as
rw*(immediate_score/2048+future_reward)-fp*failure+gb*success.
POLICY_reward and POLICY_risk_goal each use one consequence model; GPI
maximizes this scalar over the two whole vectors, then over legal actions.
Ties use lexicographic action order then source policy order. Goal tails are
analytic. All readouts reuse the identified deterministic one-step program;
no sampled model rollout, outer learning or clipping is allowed.

At each checkpoint, evaluate these three readouts on eight fresh natural
games per query/life. Evaluate each original frozen policy once per life,
then reuse those game results across query weights and checkpoints. Outer
seed=126*100000000+90000000+life*100000+replica; same seeds pair all actors,
queries and checkpoints, with zero training overlap. Total832 physical games,
with reused baseline utilities derived from their retained score/status.

On the retained fresh frozen-policy games, predict the matching policy's
afterstate vectors at both ages. Retain every prediction and compare against
actual suffix targets, zero and a constant fitted only from the corresponding
training prefix. Report per-life component MSE, probability range violations
and F+W consistency. These source-path diagnostics do not establish accuracy
on actions or states induced by GPI.

## Decision and accounting

Report each query separately, average eight replicas within each life then
the four lives equally. Primary comparisons at1024: GPI versus each frozen
policy and each single-policy readout; report per-life signs, utilities and
wins. Also compare256 to1024 for every readout. No selection of the best
outer baseline for deployment, checkpoint or hyperparameters. Any outer
cutoff prevents a complete full-game primary claim; retain it unchanged.

Freeze this protocol, sources, code and tests before one formal run. Tests
must detect wrong suffix/terminal targets, impossible component mixing,
feature-update multiplicity and evaluation mutation. Independently reconcile
training seeds, labels, model metadata, outer cohort, trace summaries and
prediction errors. Charge source model loading, native setup, acquisition,
MC component updates, model predictions, checkpoint scans/writes, wall time
and peak weight memory; no extra native replay of every training update.
All temporary and retained artifacts stay inside the research worktree.

## Limitations

Complete games have F+W=1, so these queries cover a single reward/success
tradeoff: risk1 interpolates and risk8 extrapolates the two source preferences.
This is not a hard-risk-constraint test. Four pretraining histories are reused,
source-policy coverage is narrow, and new-policy state distribution may differ.
World-model abstraction and composition remain outside this bounded first
query-reuse experiment.
