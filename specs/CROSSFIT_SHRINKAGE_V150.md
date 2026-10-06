# V150: training-only cross-fitted tail shrinkage

V149 reduced label noise but TRAIN32 still lost to ZERO in independent MSE.
Keep its256 training roots,173 action disagreements,83 same-action exact
zeros,32 retained V148 suffixes, representation and TRAIN32 final weights.
The single new rule shrinks predicted tail advantage; deterministic immediate
reward remains unchanged. No intercept, candidate grid or coefficient selected
from V149/V150 evaluation labels. H2 remains the operational baseline.

For every life0..3/query risk1,risk8 use four fixed heldout suffix blocks
0..7,8..15,16..23,24..31. Fit a zero-initialized V144 PairedAdvantage model
on each complementary24-suffix mean, with32 ordered OLD16-then-NEW16 passes,
alpha=.1 and unchanged three-component normalized LMS. Subtract exact
immediate reward once when constructing the tail reward target. Keep all
same-action roots as exact zeros. This makes32 fold models,32,768 update
attempts and1,024 out-of-fold prediction records (692 feature predictions).

Within each life/query pool the128 heldout root/fold records. Let x be
query-weighted predicted tail utility and y query-weighted heldout tail
utility. Set beta=clip(sum(x*y)/sum(x*x),0,1), or zero for zero denominator.
Fit exactly eight coefficients. Multiply all three components of retained
TRAIN32 weights by that coefficient in a separate CF checkpoint. Compare
ZERO,TRAIN32,CF using the unchanged strict-positive total-advantage gate,
with ties selecting H2. ZERO retains its empty SharedLocalAdvantage schema.
Charge all weight scaling, fold fitting, prediction, reads and model loads.

Freeze code and protocol before fitting, then all coefficients, final models
and768 predictions before fresh labels. First count CF action changes versus
TRAIN32 and ZERO across all256 roots. If CF and TRAIN32 choose identically
everywhere, retain the no_action_change result and acquire no fresh labels.
Otherwise acquire exactly32 new paired suffixes on each173 disagreement:
5,536 pairs/11,072 branches, shared by all three predictors. No selective
root acquisition, budget adjustment, replacement or outcome-driven stopping.

Reuse V148 acquisition and V143 branch execution: force retained H1_CONT/H2
actions, then the frozen query-specific H2 continuation, SINGLE leaf,
p_four=.1, goal rank11, no initial spawns, spawn after winning actions,
2,000-action cap. Both actions initialize separate RNGs with the same seed.
BASE=150*100000000; seed=BASE+life*1000000+query_index*100000+
origin_index*50000+replica*10000+slot*100+suffix. Query order risk1/risk8,
origin OLD/NEW, replica0..3,slot0..3,suffix0..31. Keep all83 same-action
roots at deterministic zero, with no sampling. Any cutoff blocks complete
cohort scientific claims. No new training interaction or full-policy games.

Report OLD16/NEW16 and combined32 means within each life/query, then equal
four-history means and signs. Compare CF-TRAIN32,CF-ZERO,TRAIN32-ZERO:
positive MSE reduction means lower error; positive gate difference means
higher value. Also report gate values over H2, four fixed eight-suffix
blocks, mean-label variance and untrimmed noise-corrected MSE. Four folds
reuse roots and do not constitute four independent learning histories.
Retain inherited actual acquisition/fitting costs, including V149 preflight
and provisional reads, without double-counting overlapping budget views.
Audit fold exclusion/targets, independent LMS weights, coefficient algebra,
source model immutability, frozen predictions, fresh streams and actual work.

Positive tail scaling cannot change a zero-immediate root's action unless
beta=0. CF=ZERO is a fallback, not learned strategic benefit. This fixed-root
experiment can diagnose useful shrinkage but cannot establish new-state
transfer or full-game improvement. General strategic learning remains open;
U005 FAIL and U006 remains unstarted.
