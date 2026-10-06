# Shared H2 Bellman value V94

Frozen before main fitting or new evaluation sampling. Exploratory comparison;
U005 FAIL and unstarted U006 remain unchanged.

## Question and matched intervention

Does undiscounted, short-step H2 value learning improve independent return
prediction and deployed fragment decisions over matched Monte Carlo state-value
regression? V93 paired-tail correction remains a retained negative control.

Reuse only V93 base trajectories for lives 3–8, incremental episode batches
0–5 and 6–11. Each base root has eight paired replicas of H2, SPACE_1, SNAKE_1,
SPACE_4, SNAKE_4. Whole censored roots supply neither learner with supervision;
all acquisition cost remains counted. No extra training interaction is acquired.
Source episodes, base branches, previous baseline acquisition, new evaluation,
and new reference acquisition are reported separately.

After the first four actions every active controller is the query-specific H2.
Use observed positions k=4,20,36,…; each row has weight one and no forced final
active row. The Bellman target is the next at most 16 observed scores /2048,
plus terminal loss/win indicators, plus the previous model's value at the next
active state. Terminal continuation is zero. Gamma=1; no clipping or probability
renormalization. Full remaining R/F/S is retained as separate MC supervision.

Both learners use the same 36 board features, per-query three-output regression
tree, depth 8, min leaf 16, seed 9101. MC_TAIL fits the complete remaining return
once. FQE starts from that saved MC_TAIL fit and performs exactly 128 synchronous
fitted Bellman updates. The tree partition is refitted each iteration. Fixed
iteration count does not establish convergence; retained iteration diagnostics
are not a model-selection or stopping rule. F+S conservation is an implementation
diagnostic under this warm start, not evidence of convergence or value accuracy.

At checkpoints 6 and 12, exclude future episodes and every episode %5==4 from
fitting. Fit full, exclude-even and exclude-odd models independently, including
all bootstrap targets. Each training root's prefix decomposition uses its
excluded-parity model; held-out roots use the full model only for diagnostics.
Use the original eight four-step prefixes, direct R/F/S plus boundary value,
then candidate minus H2 mean as the V84 joint-head target. Both heads use fixed
36-input/12-output per-query trees, depth 3, min leaf 2 roots, seed 8301.
No V92 residual correction, new M64 prefixes, or evaluation outcomes enter fits.

## Fixed evaluation

Six lives, checkpoints 6/12, 16 natural replicas per query and checkpoint.
Methods at checkpoint 6: H2_ONLY, MC, MC_EXTRA, V91_DECOMPOSED, V92_CORRECTED,
MC_TAIL, FQE. At 12 add MC_TAIL_FROZEN_6 and FQE_FROZEN_6. The four old learned
baselines are loaded from V93 without refitting. New natural environment seed
is 9490000+checkpoint*10000+life*100+replica; model seed adds 1000000. Rotate
execution order. Every method uses the same first trigger (at most six empty
cells), one fixed one/four-action commitment, then permanent query-specific H2,
with four model random draws per active action. Maximum episode length is 2000.
There are 3072 natural games in total.

Preselect the first two H2 natural replicas per query/life at checkpoint 12,
and retain their first trigger states: 24 intended independent validation roots.
Missing triggers remain missing without replacement. Freeze head predictions
before validation outcomes are observed. For each root run all five options for
16 full paired replicas (1920 intended trajectories), using V83 sample_root with
sampling life 94000+life. Its environment seed is
8310000000+(94000+life)*10000000+query_index*100000+replica_episode*100+replica;
model seed adds 1000000000000. No prefix-only validation cohort is acquired.

Compare frozen head R/F/S predictions to the independent 16-replica paired mean.
Separately compare MC_TAIL/FQE at active four-step boundary states with observed
full remaining returns; compare their paired prefix reconstructions with paired
full outcomes on those realized paths. This is held-out prediction error, not
MC against its own reference or an independent-prefix estimator variance test.
Keep root clustering and equal weighting across six histories. Censored roots
cannot support complete-reference claims; retain all raw paths and costs.

Report natural score and query utility (reward=R, risk_goal=R-4F+4S), independent
prediction bias/MSE and residual variance, and enabled/changed/disabled fragment
contributions. Primary contrasts: FQE versus MC_TAIL, MC, MC_EXTRA, H2_ONLY,
V91_DECOMPOSED, V92_CORRECTED and its own frozen head; MC_TAIL versus
V91_DECOMPOSED, H2_ONLY and its own frozen head. Across-history standard errors
and two-SE bands are descriptive, not a 95% confidence claim or acceptance gate.

## Execution accounting

Six workers; no repeated source/base acquisition. Expected new tree fits:
72 initial MC_TAIL +9216 Bellman updates +48 joint heads =9336. Retain all initial
and final value models, all heads, per-iteration fitting diagnostics, raw natural
and reference trajectories, source snapshot, terminal logs and cost counters.
Fit once under this specification. No post-result iteration/target tuning.
