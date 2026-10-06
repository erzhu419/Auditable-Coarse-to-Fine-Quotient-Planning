# V120: persistent afterstate n-tuple TD learning

V119 shows that the frozen planner can use directly simulated consequences:
MC4/16 improve on fitted trees and H2 on all four returning-history query
means, at substantial online model cost. Implement the trained value-learning
baseline requested by GPT_MultiEpisode, before more consolidation changes.

## Fixed learning algorithm

Use four new independent training histories, each with separate scalar models
for reward and risk_goal. The environment is fixed at p4=.1 and stops at the
first 2048 tile or loss. The learned V69 deterministic program is supplied;
it supplies legal action afterstates, not training trajectories or labels.
The existing ground episode sampler supplies every observed transition.
No V119 evaluation, rollout targets, selected tree or new router update enters TD.

The representation has four six-cell base patterns:
(0,1,2,4,5,6), (4,5,6,8,9,10), (0,1,2,3,4,5), (4,5,6,7,8,9).
Share each pattern's table across all eight rotations/reflections. Ranks0–10
give4*11^6=7,086,244 float64 parameters per query model. Its value is the sum
of32 active table occurrences, initially zero. Duplicate addresses contribute
their multiplicity both to the value and the semigradient.

Choose the alphabetically first legal action maximizing immediate score/2048
plus afterstate value. A winning afterstate has the analytic query goal bonus.
The learned scalar excludes the merge score which produced its afterstate.
After the next spawn, select the next actual action before updating the prior
afterstate toward the next action's immediate score/2048 plus next value.
For a losing final spawn use -failure_penalty; winning afterstates use the
known boundary and never update a terminal-rank table entry. A cutoff's last
unresolved afterstate is not trained as a terminal outcome.

Use undiscounted online TD(0), one chronological pass, no exploration mixture,
replay, clipping, optimism or best-model selection. For one pre-update error
delta, update each address by .0025*delta*multiplicity. One model is specific
to one query throughout; reward weights are1, terminal penalties/bonuses are
0/0 for reward and4/4 for risk_goal. The latter is a full-game win-sensitive
objective R+8*WON-4 on terminal games, not the old30-step risk estimate.

Afterstate evaluation, additive symmetric n-tuples and the .0025 step size
follow the basic TD discussion in [Yeh et al.](https://arxiv.org/pdf/1606.07374).
The fixed patterns, goal termination, query-specific utilities, budget and
retention are this project's choices. This is not a reproduction of the
paper's multi-stage or million-game results.

## Budget and comparisons

Each history/query trains4096 games; checkpoints0,256,1024,4096.
Total32768 training games. Each checkpoint evaluates eight independent games
per history/query with updates disabled:256 TD evaluations. Reuse the frozen
256-game checkpoint's evaluations as the early-knowledge control on the same
seeds; do not rerun those deterministic games. The final checkpoint is primary.

Run H2 and frozen MC4 on the same eight seeds for each history/query:128 more
evaluations,384 total. They retain the V119 router/rule snapshots. Charge the
source observations/router work used by these references separately; the old
consequence tree fits and utility selection are not inputs to these actors.
The TD actor is one-step learned-value selection; references retain depth-two
planning. This whole-method comparison does not isolate representation alone.
No same-budget/sample-efficiency claim; actual training transitions, generated
model work, update operations, parameter bytes and evaluation work are separate.

Max2000 actions in every game. Retain cutoffs and incurred costs without
replacement, extension or interpreting them as losses. Four workers, one per
history, train queries sequentially to bound memory. Parameters persist between
checkpoints and are never selected using outer results.

Primary reporting: final minus frozen256 TD, final minus H2 and final minus
MC4; also all checkpoint learning curves, query-specific utility, score and
win rates, per-history differences. Average replicas within history then
histories equally. Count full-game training wins and actual interaction growth.
Early vs late checkpoints use one prespecified common outer cohort; the cohort
does not supply feedback, labels or update decisions.

## Streams and evidence

BASE=120*100000000. Training seed=BASE+1000000+life*100000
+query_index*10000+episode_index, with episode_index0–4095.
Outer seed=BASE+2000000+life*100000+replica, replica0–7; pair methods,
checkpoints and queries. Planner seed adds50000000; MC4 seed adds60000000
with V119's per-call stride10^12. Training and outer streams are disjoint
from one another and retained V115–V119 streams.

Before one formal execution, freeze source/protocol and validate native tuple
evaluation/updates, terminal reward timing and non-updating evaluation.
Retain compact lossless replay traces (initial board, actions, rewards, spawn
locations/ranks, final board/status), per-game costs, block aggregates, all
checkpoint sparse model files and an independent analysis. Compilation uses
only supplied learned line tables. Builds, test temporary files and artifacts
remain inside the project workspaces directory. No new hashes.

This stage tests fixed-representation parameter accumulation on one game and
two separately trained objectives. It does not implement autonomous structural
revision, arbitrary-query transfer or A/B/A-return adaptation.
U005 remains FAIL; U006 remains unstarted.
