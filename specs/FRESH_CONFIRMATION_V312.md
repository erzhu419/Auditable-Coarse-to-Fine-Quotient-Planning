# V312 — new value-training SOURCE parents and frozen four-arm confirmation

V311 supports the matched active-two-table contribution, net SOURCE gain,
individual A/B gains and seven strict retention comparisons under four old
SOURCE parents. Confirm the frozen learner using four newly trained value
parents. Do not pool old target results or change the learner after new results.

## Fresh SOURCE

Read only the original V120 source_capsule.json deterministic dynamics snapshots
and their inherited acquisition costs. Initialize four risk_goal NtupleValue
models with zero weights, never loading an old value checkpoint. Keep V120's
query (reward=1, failure=4, goal=4), alpha=0.0025, p_four=0.1, goal rank 11,
4,096 episodes per parent and maximum 2,000 steps per training episode.
Source seeds are 31200000000+1000000+parent*100000+10000+episode, with
episode=0..4095. Preserve the old risk_goal query-index offset of 10000.

Choose the next action before updating the previous afterstate toward that
chosen value. A winning afterstate has analytic continuation and is not fitted;
a LOST game updates its final pending afterstate to −4; a CUTOFF game leaves
its final pending afterstate untrained. Preserve natural trajectories, actual
cutoffs and raw observations. Record compact physical transitions and decision/
update timing, emit 256-game progress blocks, and save only each parent's final
sparse checkpoint. No reward-only learner or historical reference evaluations.

Publish compatible source_capsule.json/run.json and source_summary.json with
the four new parent checkpoint paths, actual updates and training provenance.
Charge actual initial spawns plus sampled transitions as source raw. Include
setup, training and final checkpoint saving in measured worker CPU, record
compiler child CPU and coordinator CPU separately, and record source wall.
The source full CPU is the sum of these three scopes, not contained component
timings added again. Keep old dynamics raw/costs separate; its historical CPU
remains unknown. Verify source physics, seeds, TD timing/update counts and costs
independently; do not claim an independent complete value-weight re-fit.

## Confirmation

Use SOURCE, CONTEXT_MC, CONTEXT_LINEAR_WIN and CONTEXT_LOCAL unchanged from
V311: alpha=0.0025, full H2, MC episode-mean utility updates, active two-table
unclipped LINEAR_WIN2, and LOCAL reward/sigmoid WIN. The source of every new
bank is its fresh parent. LINEAR's WIN parameters start at 1/64; combine
R+8WIN−4, fit the same factual reward suffix/WIN labels with game-start
residuals and within-game address multiplicity. Matched resources do not
establish identical function classes or total compute.

Run 64 fresh A1/B1/A2/B2/A3 sequences under the four new parents, with true
p_four 0.1/0.5/0.1/0.5/0.1. Keep V309's confirmed detector: natural SOURCE
direct games to >=256 raw; best Beta(1,1) log BF >=0 reuses; otherwise new
posterior >=0.99 confirms, using new prior mass0.5 and uniform existing total
mass0.5. Pending evidence acquires another complete detector game. Start no
extra game at >=4096 raw and pay natural overshoot. Unresolved cap reuses the
best old bank without prototype commit. Only resolved detector facts commit;
FIT facts never update the router. Preserve misroutes, extra banks and costs.

Only confirmed new banks acquire 131,072 raw SOURCE-carrier data; unfinished
tails are paid and untrained. Fit the chronological floor(0.8*N_complete_games)
prefix once in all three learners. Store this first FIT LIBRARY belief with the
actual bank; all four arms use its selected probability. Reuse neither refits
nor replaces the belief. Current-task cells follow the actual route; historical
probes read-only route their first observed detector and use the selected bank.

Target detector seeds312100000000+stage_index*100000+life*1000000+game_index;
training seeds312200000000+stage_index*100000+life*10000000; evaluation seeds
312900000000+task_B*100000+life*1000000+episode. Keep nine cells A1_A, B1_A,
B1_B, A2_A, A2_B, B2_A, B2_B, A3_A, A3_B with32 paired games per cell/arm,
73,728 new physical evaluations, max8192 steps. SOURCE identity uses task and
actual selected probability. No old target observations or outcomes are reused.

Sole primary is equal-weight final A3_A/A3_B LOCAL minus LINEAR_WIN utility.
Require its CI lower >0, separately require LOCAL minus SOURCE CI lower >0,
and report A/B gains separately. Retain all six arm-pair contrasts. Use20,000
paired lifecycle bootstrap draws within the four realized new parent groups,
seed31200001; these are conditional intervals, not population-source intervals.
Incomplete games block support. Retained gain also requires all seven raw
LOCAL after-minus-first comparisons to have CI lower>=0: B1_A/A2_A/B2_A/A3_A
minus A1_A, and A2_B/B2_B/A3_B minus B1_B. Keep loss and unresolved statuses.

Charge old dynamics economically, fresh SOURCE training physically once and
economically per arm, and all new target acquisition/fit/evaluation work. Carry
fresh_source_compute through the target cost ledger. Combined source-and-target
CPU sums source full CPU plus target worker/compiler/coordinator CPU once;
combined wall sums the sequential experiment walls. Independent audits are
reported separately. Target measurements may proceed while the independent
source audit runs; confirmation support requires both final independent audits.

This is an independent value-training parent and target-stream confirmation
under shared previously identified deterministic dynamics, supplied stage
boundaries and historical probes. It does not establish full-pipeline model
independence, unsegmented discovery, same-context continued improvement or
general strategic learning. U005 remains FAIL; U006 remains unstarted.
