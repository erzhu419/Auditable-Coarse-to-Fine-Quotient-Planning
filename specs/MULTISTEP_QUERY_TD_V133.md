# V133: fixed multistep target-query TD

V132 reproduced the risk8 checkpoint change exactly. Winning-boundary and
bootstrap updates propagated through shared features with opposing contributions;
their directions differed between histories. Compare one fixed longer return
target with the original one-step learner. This is an exploratory method test.
U005 remains FAIL; U006 stays unstarted.

## Fixed comparison

Use all four original V120 final4096 source histories and V127 final1024
global constants. risk1=(1,1,1) starts from reward=(1,0,0); risk8=(1,8,8)
from risk_goal=(1,4,4). PARENT is the V130 single-source CONSTANT readout.
SINGLE and MULTI each initialize a private QueryTD PRIOR copy of this parent.
V131 trained parameters and V132 evaluation outcomes are not learning inputs.
The identified dynamics, representation, query conversion, alpha=.0025,
discount1, greedy selection and original lexicographic ties stay fixed.

SINGLE uses the unchanged V131 TDStream. MULTI uses horizon H=32, chosen
before this experiment. No horizon, learning-rate, clipping or checkpoint search.
At an active action decision t, choose the action once before any update.
A queued non-goal afterstate from action i stores its cumulative integer score
S_i, including action i. Once t-i=H, update the oldest item toward

    target = (S_(t-1)-S_i)/2048 + Q_t(chosen action).

The first score belongs to action i+1; the tail Q includes action t's score.
QueryTD subtracts its fixed query offset once from this complete target.
Do this mature update before executing the already chosen action. If that
choice is known to win, its Q is the analytic score/2048+goal bonus.

Execute the action and its actual spawn. Queue its afterstate and cumulative
score unless it is a goal afterstate. At a real terminal outcome, settle all
remaining entries oldest-first with their actual remaining score plus goal
bonus for WON or minus failure penalty for LOST. A mature bootstrap update
already made before a loss is not replaced or repeated. Goal afterstates are
analytic and never trained. H=1 must exactly reproduce the original stream's
actions, targets and final parameters in finite tests.

## Budgets, pending work and frozen evaluation

Four histories, two queries and two learners each acquire exactly524288
actual transitions:8388608 in total. Checkpoints are0/32768/131072/524288;
524288 is the primary comparison. Keep p4=.1, goal rank11 and the real
2000-step cap. Initial two spawns and the winning-step spawn follow V115.

At an active checkpoint, keep the same board, RNG, episode and entire queue;
resume the same game. No future sample or extra prediction settles the budget.
At the final budget retain the unresolved queue. A real CUTOFF instead drops
its unresolved entries with an explicit count. Each non-goal afterstate is
updated once, except censored or unresolved entries:

    updates = transitions - wins - cutoff_dropped_entries - final_queue_length.

SINGLE uses its original one-item pending equivalent. Record every retained
episode segment, chosen pre-update values, updates, queue boundaries, integer
reward sums, terminal/censored status and actual work. Delay and fewer settled
targets at a budget boundary are part of this method, not hidden extra data.

BASE=133*100000000. Training seed=BASE+10000000+life*1000000+
query_index*500000+episode, paired across learners at the same episode index.
Evaluation seed=BASE+90000000+life*100000+replica, paired across all methods,
queries and checkpoints. These namespaces are distinct from V131.

Freeze all training before external evaluation. Each life/query/method/age
has16 evaluation games. Run PARENT once per life/query/replica and verify both
saved zero-training learners against every parent decision and legal action
value before aliasing them. The two learners at three nonzero checkpoints
add768 games to128 parent games:896 physical games,1536 logical rows.

Primary comparisons are final MULTI-SINGLE and MULTI-PARENT utility for
risk8, with risk1 also reported as the other fixed query. Pair seeds within
each history and then weight all four histories equally. Report every life,
checkpoint, win/loss and cutoff. A cutoff retains all costs and makes the
affected terminal-return comparison unavailable. No observed result changes
the roster, budget or primary checkpoint.

## Validation and accounting

Finite tests cover score indexing, one-time offset subtraction, choose-before-
update, H=1 equivalence, mature updates before terminal flushing, queue ordering,
pause/resume and real cutoff handling. Independent analysis checks retained
target arithmetic, continuity, one-update-per-entry accounting, exact budgets,
frozen evaluations and all aliases without retraining the models.

Keep all source acquisition and historical V131/V132 work separately. Charge
new environment transitions, initial spawns, random draws, model predictions,
TD updates, queue/target work, private copies, model loads and checkpoint saves.
No model-generated samples. Retain code/protocol before one main run, all
traces and attempts inside this research worktree.

## Limitations

Longer returns change propagation delay and variance as well as bootstrap
dependence; each learner changes its own subsequent data distribution. This
comparison does not isolate an individual V132 update category's causal effect.
Two separately trained scalar query values do not establish reusable
policy-conditioned consequence models, old-task retention, planning benefit
or general strategic learning. Shared-feature representation can still limit
either method, and four source histories bound the empirical claim.
