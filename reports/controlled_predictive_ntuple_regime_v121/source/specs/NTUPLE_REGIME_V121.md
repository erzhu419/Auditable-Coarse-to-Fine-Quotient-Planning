# V121: fixed TD learner under an unannounced A -> B -> A return

V120 established a bounded benefit from accumulated experience in a fixed
environment. Advance GPT_MultiEpisode section 7 to parameter change, keeping
its trained n-tuple TD algorithm unchanged. This is a new experiment, not a
retuning or extension of V120's closed evaluation.

## Learners and task stream

Inherit each of V120's four histories and two separate query models at its
predeclared final 4096-game checkpoint (A: p4=.1). Preserve the learned swipe
program, four symmetric six-cell tables, learning rate .0025, greedy tie rule,
scalar query utilities, terminal targets and choose-before-update timing.
New phases are B: p4=.5 and A_RETURN: p4=.1. Only the environment sampler
receives p4. CONT receives boards and observed outcomes without a phase label,
change signal, model reset, router, replay or query change.

CONT keeps the same model through both phases. FROZEN_A holds the original
V120 weights without updates. RESET starts from zero at each phase boundary;
this control has privileged boundary knowledge. Both updating methods collect
their own on-policy games. They share episode seed numbers within each phase,
not trajectories or TD targets. Queries remain separately trained.

## Fixed budgets and outer comparisons

Each active learner receives exactly 524288 post-action environment transitions
per phase, for 16777216 new training transitions across all lives and queries.
Initial two-tile observations and all costs are additionally reported; equal
post-action budgets do not imply equal initial observations or equal lifetime
cost, since CONT and FROZEN_A inherit V120 training.

Checkpoint labels are 0,131072,524288. The middle checkpoint follows the first
complete game reaching 131072 transitions; record its actual cumulative count
(less than 133072). Training then continues to the exact phase cap. Each game
has max_steps=min(2000, remaining transitions). The final game may be censored;
its last unresolved afterstate receives no terminal update, as in V120. Keep
every cutoff and its cost without replacement. Pending TD state never crosses
episode boundaries. Weights and cumulative updates persist for CONT across B
and A_RETURN; RESET starts a new model at the latter boundary.

At every checkpoint evaluate eight independent full games, max2000 actions,
in that phase's environment with updates disabled. Use one fresh paired outer
cohort per phase across methods, queries and checkpoints. A_RETURN uses fresh
seeds relative to B, V120 and all training. Evaluate FROZEN_A once per phase
and reuse those outcomes as its fixed comparator. Its B outcomes also equal
CONT at checkpoint0 and are reused explicitly. Thus 832 physical outer games
cover 896 logical checkpoint/control rows; no hidden duplicate evaluation cost.
No outer information feeds learning, stopping, selection or budget extensions.

Primary contrasts within each phase: final CONT minus FROZEN_A, final CONT
minus RESET, and final CONT minus initial CONT. At A_RETURN checkpoint0,
CONT minus FROZEN_A measures retention immediately after B; its change by the
final return checkpoint describes recovery. Report all checkpoints, per-life
utility differences, score and win rates, actual cumulative transitions and
cutoffs. Average eight replicas within life, then weight four lives equally.
Do not compare raw A and B score changes as evidence of adaptation: the task's
difficulty and score distribution also change. No new H2/MC4 run is needed.

## Streams, retention and accounting

BASE=121*100000000. Training seed=BASE+1000000+life*10000000
+query_index*4000000+phase_index*1000000+episode_index. Phases have indices0/1,
queries reward/risk_goal have indices0/1. Even one-step games fit in each
1000000-wide episode namespace. Methods share this seed schedule intentionally.
Outer seed=BASE+90000000+life*100000+phase_index*10000+replica, replica0..7.
These namespaces are disjoint from V120 and each other.

Use four workers, one per lifecycle; process queries sequentially. Before one
formal execution, retain the protocol and source snapshot and test TD timing,
phase continuity/reset, exact caps, evaluation isolation, reuse and accounting.
No new core learner change is required. Retain replayable compact training and
outer traces, cumulative update counters, interim/final sparse weights, origin
references for unchanged snapshots, and independent analysis. All builds,
temporary files, logs and results remain inside the project workspaces folder.

Count new actual transitions, initial spawns, TD work, evaluation work, model
loads/saves, setup, storage and elapsed time separately. Counter deltas start
after load; loaded V120 counters are not new work. Attribute V120's training
and supplied deterministic rule separately, without duplicating old reference
H2/MC4 evaluation. No generated model sampling is added by these TD actors.

## Scope

This tests parameter learning, adaptation and retention under one specified
mechanism-parameter shift. It does not test structure revision, arbitrary-query
transfer or change detection. Continued learning may reflect more practice as
well as shift-specific adjustment; there is no unchanged-environment training
branch to isolate those causes. RESET is cheaper in inherited experience but
has boundary knowledge. A positive mean on four histories is not a general
superiority claim. Censored outer games remain in costs and prevent treating
the primary full-game comparison as complete. U005 stays FAIL; U006 is unstarted.
