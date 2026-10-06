# V77: one learner's multi-episode consequence learning lifecycle

Frozen before the main experience stream, 2026-09-13. The question is whether
updating a persistent consequence model improves later planning, and whether
revising its state partition adds value beyond updating fixed leaf statistics.
V69 dynamics are supplied equally to all methods. No dynamics discovery or
unrestricted module invention is claimed in this first lifecycle experiment.

## Knowledge and autonomous update

For each fixed continuation policy GREEDY, SPACE, SNAKE, learn the joint vector
of subsequent merge reward / 2048, first failure and first success. An input is
the deterministic afterstate before the current random spawn and a remaining
action horizon (30 or 31). The current merge reward is excluded from this
vector and added exactly by the planner. Terminal events are counted once.
The vector is conditional on one achievable continuation policy; components
from different policies must never be independently maximized and combined.

Each policy uses the same fixed board features and a multi-output regression
tree, depth <=8, min_samples_leaf=16, random_state=7701. At warmup, fit once and
copy the same knowledge into FROZEN, FIXED and REVISED. FROZEN stops updating.
FIXED retains the original partition and updates leaf means from cumulative
training examples. REVISED first updates its current leaf means, then proposes
a newly fitted partition. It accepts per policy only if new internal-validation
MSE improves and old internal-validation MSE is at most incumbent*1.02+1e-12.
Otherwise retain the updated incumbent. Empty validation strata are explicitly
reported. Split selection and acceptance never use evaluation games.

Episode indices are zero-based; episode%5==4 is internal validation, the rest
training. All methods receive the same completed experience prefix. Update
times are fixed at 15, 39 and 75 completed episodes. No learning algorithm,
feature, query, threshold or seed is changed after inspecting main results.

## Natural experience and evaluation

Three independent lifecycles have IDs 0,1,2. Training episode seed is
7700000 + lifecycle*10000 + episode. Behavior policies cycle through
GREEDY (merge score, then vacancy count), SPACE (vacancies, then score), and
SNAKE (fixed snake-order tile-weight sum, then score); action ties are lexical.
Every game starts with two ordinary random tiles on an empty 4x4 board and
ends at 2048, no legal move, or the declared 2000-action cap (CUTOFF).
Only one actual spawn is sampled per interaction; no exact-support teacher
is called for learning. Initial spawns, actual transitions, known-model
computation, imagined spawns, and evaluation interactions are counted separately.

After a complete training episode, create Monte Carlo labels at step indices
0,4,8,... plus the last step, for horizons 30 and 31. Use subsequent observed
rewards and events only. A true terminal state closes a shorter window; an
administrative cutoff does not. Omit incomplete windows at a cutoff.
This is a shared, sequentially revealed offline experience stream, not a test
of autonomous exploration or ordinary interaction-only discovery of dynamics.

At each checkpoint, evaluate two fresh natural-game seeds per lifecycle:
7790000 + lifecycle*100 + replica (replica=0,1), paired across all checkpoints
and methods. Queries are reward=(1,0,0) and risk_goal=(1,4,4), ordered as
(reward_weight,failure_penalty,goal_bonus). Evaluation data never enter training
or candidate acceptance. Complete game score and terminal outcomes are primary;
the learned 32-step prediction is not represented as a full-game value guarantee.

Five methods run every evaluation case, with rotated execution order:
H2_ONLY (known-model short planning), FROZEN_PLAN, FIXED_PLAN, REVISED_PLAN,
REVISED_DIRECT. PLAN uses two sampled root-spawn outcomes per action, shares
their uniform draws across root actions, enumerates second actions and uses
policy-conditioned horizon-30 leaf predictions. DIRECT chooses among exact
first swipes plus horizon-31 predictions from the same revised knowledge.
Both therefore use a nominal 32-action window. H2_ONLY uses the same two root
samples plus exact analytic H1 terminal masses; its horizon is explicitly two.
The model RNG is separate from the environment RNG; all cases use paired
per-step random numbers. No query-dependent hidden environment samples.

## Interpretation and costs

Report lifecycle learning curves, held-out full-game utility/score/terminal
outcomes, query-dependent decisions, prediction losses, accepted/rejected
partition revisions, model sizes, known-model expansion and actual samples.
Primary paired comparison is REVISED_PLAN versus FIXED_PLAN at the final
checkpoint, by query and independent lifecycle. FROZEN tests accumulation;
REVISED_DIRECT tests the value of extra model-based planning with identical
knowledge. H2_ONLY is a short-planning reference, not an equal-horizon arm.

Charge experience collection/label preparation and initial fit once to each
learning method, plus its cumulative updates, model serialization and evaluation.
FROZEN only needs the warmup experience; FIXED and REVISED pay for the growing
prefix. Previously identified V69 dynamics are common supplied prior knowledge.
REVISED_DIRECT shares the same actual revised updates but receives their full
counterfactual attribution. Do not sum those attributed totals as actual wall
cost. Validation games are reported separately from training interactions.

Three lifecycles are a bounded exploratory test, not a precise uncertainty or
superiority claim. If structure revision fails to improve transfer over the
fixed-partition learner, do not call it strategic self-evolution. Retain failed
updates, capped games and negative results. U005 FAIL and U006 status remain.
