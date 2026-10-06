# V314 — fixed-policy local recurrence versus complete factual MC

V313 found loss against own FIRST, including harm on the first shared cohort
before any collector feedback difference. Test the learning target directly.
MC labels are legitimate returns under their actual behavior policy; this
experiment does not label them incorrect or equate SARSA with optimal H2.

Reuse the four audited V312 SOURCE parents physically, retaining all seven source
cost fields economically. Use 16 new target lifecycles (parent=life%4), four per
parent, with inherited deterministic dynamics. This is conditional development
evidence. No old target facts enter a new fit.

Initially acquire A (.1) then B (.5) with V309 confirmed contexts, each 131,072
raw SOURCE-carrier observations plus actual detector observations. Require two
actually confirmed distinct banks. Retain failed preconditions as whole-cohort
HOLD without omitting or replacing a life. Freeze each bank's first complete-game
80% FIT spawn belief. Fit FIRST_LOCAL once using unchanged V301, alpha=.0025.
Freeze its actual reward/logit parameters and use this v0 H2 policy for EVERY
subsequent collection. Known task batches address the initially observed banks.

Clone FIRST into private MC_LOCAL and TD_LOCAL heads. Process A_R1, B_R1, A_R2,
B_R2. Acquire one new 65,536-raw cohort per task/round with FIRST_LOCAL v0;
share it physically and charge it economically to both arms. Tails remain paid.
Both arms fit all nonwinning states of the same chronological complete-game
80% FIT prefix exactly once. No HELDOUT or unfinished-tail state is fitted.
Preserve all actual next actions, next afterstates and full factual game endings.
The supervised-state count, address denominators, commits and parameter-write
counts are identical across arms; extra target reads/save costs are not equalized.

MC_LOCAL uses unchanged V301 complete future reward suffix (excluding current
action reward) and final game WIN/LOST label. TD_LOCAL changes only the targets:
for current afterstate x[t], use the ACTUAL recorded successor x[t+1] within the
same game, and that next action's reward r[t+1]. For a continuing successor:
R_target=r[t+1]+R_batch(x[t+1]); W_target=sigmoid(logit_batch(x[t+1])).
For an actual next action that wins: R_target=r[t+1], W_target=1.
For the last nonwinning afterstate of an actually LOST game: R_target=0, W_target=0.
Winning afterstates themselves remain analytically valued and untrained.
Never use r[t], choose another next action, or cross into the next game.

The TD bootstrap head is the learner's actual BATCH_START snapshot (v0 for R1,
own v1 for R2), held fixed for the whole fit. Reuse the before-fit copy required
for actual version history; do not make another dense target copy. Both methods
read current predictions from each game's start before any write, then accumulate
occurrence residuals and commit with the same V301 per-game normalization.
TD soft WIN residual uses its target probability minus the current sigmoid.
Save native actual reward/WIN/kind targets for every FIT step: kind0 is an unused
winning row, kind1 bootstrap successor, kind2 analytic next WIN, kind3 final LOST.
Store these arrays with the actual bootstrap-version receipt for full independent
target checking. Retain CUTOFF facts and block natural-terminal support.

Evaluate SOURCE/FIRST at initialization and MC/TD after each round: 32 paired
whole H2 games per task/life, max8192 steps, 6,144 physical evaluation games.
No DIRECT rerun: V313 already established that control with identical learned heads.
Sole primary is final TD_LOCAL minus own FIRST_LOCAL, equal A/B weight.
Require CI lower>0 for gain. Retained improvement also requires A and B own-FIRST
CI lower>=0; average gain cannot hide loss or unresolved preservation.
Separately test target intervention TD_LOCAL−MC_LOCAL, net SOURCE gain and MC's
own-FIRST/net-SOURCE results. Target-mechanism support requires own-FIRST gain,
both-task retention AND positive target intervention. Retain both-round curves
and every task contrast, including adverse results.

Use 20,000 paired bootstrap draws within four realized parent groups,
seed31400001. Warm seeds314100000000+task_index*100000+life*1000000+game;
initial stream seeds314200000000+task_index*100000+life*10000000;
post seeds314500000000+life*10000000+task_index*1000000+round*100000;
eval seeds314900000000+life*1000000+task_B*100000+episode.
All families and life/task/round combinations are disjoint.

Reuse the sparse actual version format acfqp.head_version.v313: SOURCE-relative
FIRST v0, each branch's own changed-address v1/v2 with absolute new values.
Retain first8/last8 actual preboard/all-action-value probes per new fixed-policy
cohort. Independent audit replays new raw tapes, reconstructs actual versions,
checks fixed FIRST ownership, literal action probes, every saved native TD target,
natural labels/FIT boundaries, equal states/writes, paired endpoints and costs.
No full re-fit, evaluation-action rerun or bootstrap re-draw.

Count all new observations, initialization, copies, target reads/sigmoids,
fit/scan/save/target-artifact costs, eval and native compiler CPU. Contained
component timings remain inside worker CPU and are not added twice. Source is
charged economically once; historical dynamics CPU remains unknown. Independent
audit CPU is separate. All intermediates belong in reports/local_targets_v314.
Freeze before formal acquisition. Do not change seeds, alpha, budgets, target
snapshot frequency, representation or interval after results. U005 stays FAIL;
U006 is not run by this experiment.
