# V125: confirmed contexts with value learning on fresh streams

V124 met its retained-trace routing milestone. Freeze its router and test
actual value learning on new training/evaluation seeds. Retain all prior
negative outcomes, U005 FAIL and U006 unstarted.

## Frozen methods

All methods inherit the same V120 final4096 n-tuple model for each of four
source histories and two separately trained queries. Keep the representation,
alpha .0025, query rewards, lexicographic greedy ties and terminal semantics.

CONT is ordinary immediate afterstate TD. DELAY has one value table and the
frozen V124 router controlling64/128-observation update batches. BANK uses
the identical router/batching rule with separate value tables per context.
Both initialize the router using the same retained256 source ranks; no phase
label, true p4 or boundary notification reaches a learner.

For each new post-action observation: route its observed spawn rank, creating
a BANK copy before any delayed TD updates if needed; choose the next action
under the now active context; queue the preceding afterstate and this causal
next-choice value. Only then commit any router-confirmed64/128-observation batch.
Apply its stored targets chronologically with the fixed alpha, censoring any
eligible row whose action context or bootstrap context differs from the final
destination context. Apply this same censor to DELAY's virtual context IDs
although its table is shared. Fixed terminal loss targets have no bootstrap
context; a winning afterstate or budget cutoff contributes one observed rank
and a no-target queue entry. Never recompute old targets at commit.

Queue and router state persist across games, checkpoints and phases. No end
flush. First-change batches will usually be censored, preventing them from
writing the previous bank. Normal within-context TD targets are delayed/stale:
DELAY controls this changed update schedule, and CONT measures the practical
cost relative to the original learner. Different policies collect different
trajectories, so matched delay rules do not imply identical realized schedules.
Inactive BANK weights retain their parameters. New banks clone the active
table; existing contexts restore their own table. No pruning or tuning.

## Fresh experiment

Four existing source histories, queries reward/risk_goal; hidden B p4=.5 then
A_RETURN p4=.1. Each method receives exactly524288 new post-action transitions
per phase/query/history, max_steps=min(2000, remaining). Total25165824 new
training transitions across CONT, DELAY and BANK. Do not reuse V121/V122 training.

Training seed =125*100000000+1000000+life*10000000+query_index*4000000+
phase_index*1000000+episode. Pair methods by episode seed; their trajectories
and episode lengths may diverge. Queries and phases have separate training
streams. Router initialization is reused data, not new acquisition.

Evaluate at phase0 and exact524288 using8 fresh games per model/phase/checkpoint.
Evaluation seed =125*100000000+90000000+life*100000+phase_index*10000+replica.
Pair methods, queries and checkpoints within phase, with a separate return cohort.
FROZEN_A is evaluated once per phase and reused as a comparator. CONT B0 reuses
its identical FROZEN_A results. DELAY and BANK B0 run their own physical games
to charge router work. Total896 logical rows /832 physical games.

Every adaptive evaluation uses a private router and read-only value views.
Discard pending training TD records from the evaluation copy, preserve its
already-observed router state, and perform no TD. Discard evaluation state
after each game. No outer outcome enters training or checkpoint choice.
All final model states are retained; phase0 references existing snapshots.
Save only final phase checkpoints, not intermediate model duplicates.

## Outcomes and verification

Primary final contrasts: BANK minus DELAY, CONT and FROZEN_A, separately for
each phase/query. Also show return0 retention, every life, wins, utility,
score, steps and physical runtime. Average8 replicas within life, then4 lives
equally. Require terminal outer games for complete full-game primary evidence;
retain cutoffs and report incompleteness without replacing them.

Replay observed ranks independently through V124 to reconcile action/context
IDs, router events, delayed commits, applied/skipped/no-target TD counts, and
phase-final pending queues and router state. Test actual native-value protection,
causal next-choice timing, terminal/cutoff handling, delayed single-table control
and evaluation isolation on synthetic fixtures before formal execution.
No redundant full25-million-transition native-weight replay is required.

Account separately for acquired training/outer transitions, initial spawns,
actual TD updates, censored targets, queue peaks, route work, bank copies,
model setup/load/save, saved bytes and resident table bytes. Charge shared
V120 training22124667 as inherited, plus reused warmup processing. Earlier
V121/V122 training and outer evaluations are not inputs. Record source/protocol
before one main execution. No outcome-dependent extension, seed selection or
adjustment of the frozen router; every artifact remains inside the project.

## Limitations

The four source histories are reused, not four new independent pretraining
runs. This tests a single parameter change and return with block-aligned
boundaries. BANK changes storage and routing-conditioned use; DELAY controls
update delay/censor rules, not all downstream trajectory differences. No claim
of general strategy learning or overall sample efficiency follows from router
stability alone. New contexts incur full-table memory/copy costs.
