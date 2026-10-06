# V131: target-query TD along the learner's own games

V130 fitted sparse fixed-parent action gaps but lost held-out accuracy and
complete-game utility. Test dense, continual afterstate TD under the current
policy, with the spatial representation and learning rule fixed. This is an
exploratory adaptation experiment; U005 remains FAIL and U006 unstarted.

## Fixed models and update

Use four V120 final4096 histories. Target risk1=(1,1,1) starts from source
reward=(1,0,0); risk8=(1,8,8) from risk_goal=(1,4,4). PARENT is exactly the
V130 frozen single-source CONSTANT readout with V127 final1024 global event
frequency. Its weights stay read-only. V130 residuals, labels and evaluation
outcomes do not enter the learner.

PRIOR copies the original source table into its own writable n-tuple table W.
For a non-winning action its value is computed in the parent's operation order:

    Q = (score/2048 + W(afterstate)) + (f_source-f_target)
        + ((f_target+g_target)-(f_source+g_source))*constant.

Call the fixed two correction terms together b. SCRATCH uses a zero table
and b=0, sharing only the identified dynamics and spatial feature scheme.
Both give winning actions exact score/2048+g_target. Zero-training PRIOR
must reproduce every parent action value and tie decision exactly.

Use the V120 multiplicity-aware update, alpha=.0025, discount1, greedy action
selection and lexicographic ties. At the next observed decision, select the
actual next action before updating the preceding pending afterstate. Update
W(pending) toward Q(next action)-b, then execute that selected action. At an
actual loss, update the final pending afterstate toward -f_target-b. Winning
afterstates are analytic and never fitted. At the real2000-step episode cap,
retain CUTOFF and omit the unresolved final update. No replay, minibatches,
clipping, learning-rate search, residual fitting or extra simulated samples.

## Exact new-data budget and checkpoints

Four lives, two target queries, PRIOR and SCRATCH; each learner acquires exactly
524,288 actual transitions, totaling8,388,608. Checkpoints are fixed at
0/32,768/131,072/524,288; the final checkpoint is primary. The environment
uses p4=.1, goal rank11 and the same initial two spawns and winning-step spawn
as V115. Initial spawns and their random draws are separately charged.

At a checkpoint stop after the executed transition and terminal processing.
An active game retains its board, environment RNG, episode index and pending
afterstate. Continue that same game when the budget resumes. Do not sample a
future transition to settle the pending target, reset the game, or label the
budget boundary as a terminal outcome. At the final budget retain the active
prefix explicitly. No sampling at zero budget. In total:

    TD updates = transitions - wins - real cutoffs - int(final pending exists).

Record all compact episode segments, chosen pre-update values, TD targets and
errors, pending state, actual counts, checkpoint saves and initialization work.
Snapshots are frozen before any external evaluation. No results select a
checkpoint or extend the budget.

BASE=131*100000000. Training seed=BASE+10000000+life*1000000+
query_index*500000+episode, paired across learning methods at equal episode
index. Evaluation seed=BASE+90000000+life*100000+replica, paired across
methods, queries and checkpoints. Evaluation streams never feed training.

## Full-game comparison and costs

At each checkpoint evaluate16 fresh games per life/query/model, maximum2000
steps, with all weights frozen. Evaluate PARENT once (128 actual games) and
reuse those histories across checkpoints and as exact PRIOR@0. SCRATCH@0 has
128 actual games. Both learners at the three nonzero checkpoints add768:
1,024 physical games,1,536 logical rows including parent aliases. All aliases
retain their shared provenance and cost only the actual physical game.

Primary comparisons: final PRIOR-PARENT and PRIOR-SCRATCH in target utility,
paired by evaluation seed, first within each life then equally across four
lives. Report all checkpoints, each life, wins, cutoffs and training costs.
Cutoffs suppress affected full-return comparisons without removing costs.
This tests equal added target-transition budgets: PRIOR/PARENT also inherit
source value and constant learning, whereas SCRATCH requires only dynamics.
Keep historical experimental work separate from each learner's necessary
inputs, and retain actual new setup/load/copy/prediction/update/save costs.

Tests cover exact zero-training equivalence, offset subtraction, causal target
order, terminal semantics and pause/resume invariance. Independent analysis
checks segment continuity, seeds, budgets, update/terminal counts, target
arithmetic, frozen evaluations and paired summaries. No full8-million-step
retraining is required to verify a completed run. Code/protocol are copied
before one main run; all artifacts remain under this research worktree.

## Limitations

Four source histories and two separately trained target queries do not prove
general strategic learning or zero-shot query transfer. Equal transition
budgets can have different episode counts and initial-spawn costs. Greedy TD
can change its own data distribution and is not guaranteed to improve a
strong parent. Source acquisition is additional prior work, not free data.
