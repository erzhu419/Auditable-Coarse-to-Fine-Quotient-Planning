# V134: global occupancy conditions on local afterstate values

V133's fixed32-step target damages both queries. Keep the original one-step
TD objective and test one representation hypothesis: whether local patterns
need a global space-constraint condition. This is an exploratory comparison;
U005 remains FAIL and U006 stays unstarted.

## Representations and controls

Use all four original V120 final4096 source histories with V127 final1024
global constants. risk1=(1,1,1) starts from reward=(1,0,0), risk8=(1,8,8)
from risk_goal=(1,4,4). PARENT is the frozen single-source CONSTANT readout.
SINGLE is the unchanged QueryTD PRIOR learner.

Both new learners use two private copies of the original four six-cell
tables. Flat addresses are bank*(4*11^6)+original_address. Their32 feature
occurrences follow the original tuple and D4 order exactly.

- GLOBAL: select bank1 when the current non-goal afterstate has at most4
  empty cells, otherwise bank0. The same global bit conditions all32 features.
- CAPACITY: for each six-cell tuple occurrence, select bank1 if an additional
  cell is occupied, otherwise bank0. Freeze additional cells(3,7,6,10) for
  the original four tuples, transformed by exactly the same D4 operation.
  Each is outside its associated six cells. This is an extra local occupancy
  interaction, not two duplicated tables that always receive the same updates.

Both banks initialize from the source table. Thus their untrained predictions,
every legal action value and tie choice must exactly match PARENT. Goal
afterstates remain analytic; they are never indexed or fitted.

GLOBAL and CAPACITY each allocate14,172,488 doubles versus SINGLE's7,086,244.
They have the same32 active feature occurrences, alpha=.0025, original
multiplicity-aware update and one pre-update TD error. Actual repeated-address
multiplicities and reachable parameter sets differ: GLOBAL's constrained bank
cannot use six-cell codes with five or six empty cells (244 allocated entries
across four tables). Keep this small structural difference; do not relabel
allocated capacity as identical expressive capacity. Record actual bank use,
unique writes and sum of squared multiplicities per update.

## Unchanged learning and acquisition

All three learners use the original V131 TDStream. Choose the next actual
action before updating the preceding pending afterstate, subtract the fixed
query offset once from the complete target, then execute the selected action
and actual spawn. A terminal loss settles the final pending item; goal
afterstates are analytic. A change of occupancy context does not reset the
stream or suppress a cross-context TD target.

Each learner acquires524288 new real transitions, with checkpoints
0/32768/131072/524288. Four lives, two queries, three learners total12,582,912.
At each active budget boundary preserve the same board, RNG and pending item;
resume that game. At the final budget retain its unresolved prefix. Real
CUTOFF at2000 steps remains censored. Keep p4=.1 and the original initial
two spawns and winning-step spawn. No model-generated samples, replay,
normalization, clipping, context-threshold search or outcome-driven splitting.

BASE=134*100000000. Training seed=BASE+10000000+life*1000000+
query_index*500000+episode; evaluation seed=BASE+90000000+life*100000+replica.
Pair training by episode index and evaluation by seed across methods.
V131-V133 trained parameters and evaluation outcomes never enter learning.

## Frozen evaluation and primary comparison

Freeze all training before evaluation. Use16 full games per life/query/method/
checkpoint. Run128 parent games once, verify all three saved zero learners
against every decision and legal action value, then retain their aliases.
Three learners at three nonzero checkpoints add1152 games:1280 physical
games and2048 logical rows including frozen-parent and exact-zero aliases.

The primary checkpoint is524288. Compare GLOBAL-CAPACITY to assess this
specific global interaction against the fixed local interaction, and
GLOBAL-SINGLE/GLOBAL-PARENT for overall benefit, separately for risk1/risk8.
Average paired differences within each history, then equally over all four.
Retain every checkpoint, history, win/loss and cutoff. Cutoffs retain costs
and suppress the affected terminal-return comparisons. No checkpoint replaces
the final comparison. There is no post-result capacity or context adjustment.

## Validation and accounting

Finite tests cover exact zero-source recovery, both context addressing rules
under D4, outside-tuple discrimination, inactive-bank isolation, multiplicity
arithmetic, save/load and ordinary TD pending across context changes. The
independent analysis checks the original retained TD identities, budgets,
frozen evaluations, context metadata, allocated/copy/save counts, bank use
and effective update-norm diagnostics without rerunning training weights.

Charge all new transitions, initial spawns, random draws, context cell reads,
lookups, predictions, updates, private copies, checkpoint loads and saves.
Historical source acquisition and V131-V133 experimental work stay separate.
Copy the protocol and executed code before one main run; retain traces and
all attempts inside this research worktree.

## Limitations

This tests one global empty-cell condition against one local occupancy
condition. It does not establish all global representations as superior,
match effective function steps exactly, or isolate representation from the
learner's resulting data distribution. Sparse coverage and shared-feature
interference can remain. The separately trained scalar queries still do not
establish reusable policy-conditioned consequences, old-task retention,
planning benefit or general strategic learning.

