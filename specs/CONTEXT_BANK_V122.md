# V122: observed-context value retention and return

V121 found experience benefits over reset learning, but each query still had
two of four returning histories below frozen A knowledge after more updating.
Test an explicit value bank indexed by observed context. Freeze this protocol
before one main execution. Keep V120/V121 results and U005 FAIL; U006 unstarted.

## Fixed mechanism

Start each of four V120 final4096 histories and two separate query models with
one n-tuple value bank. Initialize V115's LIBRARY router with exactly the first
256 post-action spawn ranks from that model's retained V120 training trace.
These are reused observations, not new environment calls or supplied p4.
Preserve the V115 block64 Beta predictive rule and its log64 creation penalty.
No phase name, true probability or boundary notification reaches the learner.

Infer each spawn rank from the chosen deterministic afterstate and the next
visible board. Route only after this observation, before the next decision.
Initial two spawns are charged but do not update the router. Completed blocks
may create a context or reactivate an old one; pending observations and active
context persist across games and the hidden B-to-A_RETURN boundary.

A new context receives an exact copy of the currently active value parameters.
An existing context restores its own parameters. Inactive values are retained.
Keep V120 representation, step size .0025, greedy tie handling and TD targets.
Choose the next action before updating the pending afterstate. If its original
bank differs from the newly active bank, skip that pending TD update and count
the skip. This also applies to a final observed losing spawn. A winning
afterstate remains analytic; a cutoff receives no unresolved terminal update.
Observe the final spawn exactly once, including wins and cutoffs. No replay,
retroactive rerouting, bank pruning, grid search or outcome-dependent extension.

## Matched experiment and evaluation

Use the same hidden phases and training seeds as V121: B p4=.5, then A_RETURN
p4=.1, following inherited A p4=.1. BANK collects its own on-policy experience,
with exactly524288 post-action transitions per phase/query/history:8388608 new
training transitions. max_steps=min(2000,remaining); retain budget cutoffs.
Checkpoint labels0,131072,524288; the middle checkpoint is the first full game
crossing131072, with actual transition count retained.

Reuse V121 CONT's fixed training and checkpoint files rather than repeat its
8388608 transitions. Its training seeds match BANK by episode number; different
actions create different trajectories. FROZEN_A uses the original V120 final
model. These methods inherit the same V120 training costs. V121 RESET and all
old outer outcomes are excluded from the new controls and acquisition ledger.

Evaluate each method on eight fresh games per checkpoint/query/history/current
phase. Outer seed=122*100000000+90000000+life*100000+phase_index*10000+replica.
Pair methods, queries and checkpoints within a phase; the return cohort differs
from B and all V120/V121 outer data. FROZEN_A is evaluated once per phase and
reused as a fixed comparator. CONT at B0 reuses that identical fixed policy's
results. BANK runs its own B0 evaluations to measure causal routing work.
Total832 physical outer games and896 logical rows.

BANK evaluation uses a private copy of router statistics and independent model
counters with read-only views of checkpoint weights. Router observations and
context switching may occur within that game; TD updates are disabled. New
evaluation contexts share the identical active weights read-only, since no
updates occur. Discard all such state after each replica. No evaluation state
or outcome enters later training, checkpoint choice or selection. CONT and
FROZEN_A evaluation remain fixed. In particular, A_RETURN0 is an adaptive
within-game retention test, not an oracle's instantaneous context restoration.

## Outcomes and accounting

Primary contrasts: final BANK minus CONT and FROZEN_A in each phase/query, plus
A_RETURN0 BANK minus those controls. Report every checkpoint and life, wins,
score and query utility; average replicas within life then lives equally.
Define routing diagnostics from the retained causal sequence: fraction of
decisions using source bank0 in each phase; first post-action observation that
activates bank0 on return (zero if already active); predecision probability
error versus the harness probability; created/reactivated modules and skipped
cross-context updates. True p4 appears only in post-run diagnostics. No phase
identity is assigned to a new bank on behalf of the learner.

Charge new training/evaluation transitions, initial spawns, route predictions,
block scores, copies, model setup/load/save and storage separately. Charge
reused V121 CONT training and common V120 training as inherited costs; exclude
old evaluation work. Log warmup data reads/processing without counting another
environment acquisition. Report peak resident bank bytes, physical copied
parameter bytes and retained checkpoint bytes, not just the original table size.
All traces include replayable moves, spawn ranks, action bank ids, route events
and cross-context skips. Independently replay the fixed router and reconcile TD
counts/budgets; no costly full-board engine replay is needed for unchanged code.

Retain source/protocol snapshot before execution, all trained bank/router
checkpoints, origin references for unchanged models, four lifecycle workers,
and targeted tests. Every build, temporary file and artifact stays inside the
project workspaces folder. No hashes. Evaluation cutoffs are retained and
prevent treating the primary full-game comparison as complete.

## Scope

This is fixed-form parameter-module retention, not autonomous structural rule
invention. It tests one known experimental shift with a learner blind to its
timing and probabilities. Training seeds and CONT history come from V121;
fresh outer games are a new paired evaluation, not four new source histories.
The bank mechanism was motivated by V121 results. It changes routing, storage
and cross-context TD handling together; an improvement does not isolate each
component. There is no unchanged-environment training branch. Equal new
post-action budgets do not imply equal initialization observations, lifetime
cost or memory footprint. No broad sample-efficiency or significance claim.
