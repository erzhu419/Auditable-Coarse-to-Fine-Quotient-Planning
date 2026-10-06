# V135: planning above a frozen learned afterstate value

V134 did not establish an advantage specific to its global occupancy bit.
Freeze its final SINGLE and CAPACITY values and isolate the contribution of
one additional decision layer. V119 already showed benefits from costly
model continuations; V120 compared differently trained models and planners.
Here the learned parameters and leaf query conversion are identical within
each DIRECT/H2 pair. This is an exploratory full-game comparison.

## Fixed inputs and readouts

Use all four V134 source histories, risk1=(1,1,1) and risk8=(1,8,8), and
both SINGLE and CAPACITY final524288 checkpoints. The parent remains the
V120 reward/risk_goal source plus its V127 constant. Load each leaf once per
history/query/representation and make its weights read-only before any game.
DIRECT and H2 share that same leaf object; no new learning, adaptation,
checkpoint selection, query-specific method selector or replay fitting.

DIRECT is the original QueryTD.choose, including its precise query-offset
arithmetic, analytical goal handling and lexical tie rule. H2 uses the same
identified line-rewrite tables for both action layers. For a legal root
action with score r and non-goal afterstate y:

    Q_H2(x,a) = r/2048 + sum_z P(z|y) * QueryTD.choose(z, query).value

Enumerate empty cells in ascending index and spawn rank1 then rank2, with
probabilities taken from that history's frozen identified spawn distribution,
divided by empty_count. The retained rank-two estimates are approximately
.10536/.10492/.10580/.10646; the actual environment remains .1. Thus every second-layer
action is scored using its immediate reward and the SAME frozen afterstate
value and query conversion. Maximize after conversion, with lexical ties.
Root reward, second-layer reward and leaf offset each enter once; the root
does not also receive a leaf prediction or a second offset.

An immediate root goal has value r/2048+goal_bonus and no branch expansion.
A postspawn state with no legal move contributes -failure_penalty; a
second-layer goal uses its analytical value without indexing goal tiles.
The actual game still performs its ordinary spawn on the winning action.
The planner neither calls the ground transition kernel nor consumes an RNG.
There is no transposition cache, pruning, stochastic rollout or depth search.

## Frozen evaluation and comparison

Four methods are SINGLE_DIRECT, SINGLE_H2, CAPACITY_DIRECT and CAPACITY_H2.
Each runs16 fresh natural games for each of four histories and two queries:
512 physical games, with no aliases. All use p4=.1, goal rank11, max2000
actions, two initial spawns and the existing terminal semantics. Retain
CUTOFF as censored, including its cost, and suppress its affected terminal
return comparison. No game is replaced or added after observing results.

BASE=135*100000000. Every method and query uses evaluation seed
BASE+90000000+life*100000+replica. Models and protocol are fixed before the
first game. The primary comparisons are H2-DIRECT separately within each
representation and query, paired by seed, averaged within history and then
equally across all four histories. Retain every history, win/loss/cutoff,
terminal utility, score and decision count. Do not pool the two queries or
select a representation based on the current evaluation outcomes.

## Work and finite validation

Charge fresh real transitions and spawn draws separately from enumerated
model outcomes, learned action applications, leaf predictions/table reads,
CAPACITY context reads, expectation arithmetic, setup/loads, decision time
and total run time. H2 uses more compute by design: this measures its
quality/cost tradeoff, not equal-compute superiority. Historical V134 and
source acquisition remain separate. All temporary builds and artifacts stay
inside this research worktree; use existing checkpoints without copying them.

Before the single main run, use finite synthetic boards to compare all native
H2 action values with independently enumerated Python calls to the original
leaf model, including root/leaf goals, losses, illegal root moves, contextual
addresses, offset rounding and the actual source's estimated spawn law.
Verify DIRECT recovery and read-only weights.
Runner tests use mocked episodes only. Independent analysis reconciles the
512-game roster, terminal accounting, retained action choices, frozen model
states and actual planner counters; it does not resample or reload weights.

## Limitations

This tests one extra decision layer on two fixed learned scalar query values
from four reused histories. It does not supply query-reusable consequence
vectors, autonomous consolidation, old-task retention or model compression.
The frozen spawn estimates have sampling error, and finite enumeration still
constructs concrete successor boards. U005 remains
FAIL and U006 remains unstarted.
