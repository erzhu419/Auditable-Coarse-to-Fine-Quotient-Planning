# V151: conditional executable policy modules

V150 tail shrinkage reduced same-root MSE without stable action gains. Change
the candidate intervention to an executable policy module. Reuse each of four
histories' frozen SINGLE H2(risk1) and H2(risk8) teachers. For target query q,
the alternative teacher always receives its own query, but terminal returns
are scored under q. A module executes the other teacher for exactly1 or8
actions (or until terminal), then resumes own H2 for training consequences.
Duration0 is own H2 throughout. There are no new mechanism/leaf fits.

Each history/query keeps two independent three-component ROOT consequence
models, one per duration. Use the same boundary-aware unary/adjacent-pair
features from V147 plus a bias; root features have41 occurrences. Do not use
afterstate differences or suppress examples when first actions coincide:
eight-step interventions may diverge later. Predict total paired differences
in reward/2048,failure,success, without immediate reward subtraction. This
representation and task differ from V149/V150; the controlled comparison is
duration1 versus8 within V151, not an isolated comparison to those learners.

Four continual batches follow checkpoint0. For each history/query/batch play
two new natural own-H2 source games, select four active predecision roots per
game at floor((2*slot+1)*steps/8),slot0..3. Visit suffix0..7 outermost and
source-game/slot roots innermost. Each root/suffix physically executes a
triplet in order0,1,8, separately initialized with the same RNG seed. This
shared acquisition pool has a65,536 actual-transition cap including source
games. Each branch cap is min(2000,remaining budget). Stop when the cap is
spent or all64 triplets are attempted. Retain every partial/cutoff branch
and its cost; a triplet trains neither learner unless all three terminate.
The two learners receive exactly the same complete triplet IDs and both
budget views charge the ENTIRE shared pool. This is an equal shared-data
comparison, not independent per-method sampling-efficiency measurement.

Average each root's available complete suffixes into one paired target per
duration. Keep previous examples and weights. At each batch run32 ordered
passes (batch,source game,slot) over all accumulated root means, alpha=.1,
normalized LMS denominator=sum(feature_multiplicity**2). Do not weight a
root more heavily because it has more suffixes. No coefficient grid,
heldout-dependent model choice, label-driven root selection or early stop.

Freeze code/protocol before checkpoint0. Save both queries' model states and
training bindings before every evaluation. Checkpoints0..4 each evaluate
H2,ALT,LEARN1,LEARN8 on four fresh paired seeds per history/query:640 physical
games. H2 is also the exactly equivalent zero/no-learning gate. ALT always
uses the other teacher (always selecting either module duration gives the
same policy). LEARN selects a module iff recomposed predicted total utility
is strictly positive. Commit for its full duration, then reconsider; on a
decline execute own H2 once. Do not re-evaluate inside a chosen module.
Evaluation games never train models or modify the acquisition schedule.

From each fresh H2 evaluation game retain the same four quantile roots and
both predictions, including exact overlap with already acquired training
boards. These are transfer/activation diagnostics without counterfactual
labels; do not call them independent prediction-accuracy measurements.
Report the full checkpoint learning curves and final contrasts LEARN8-H2,
LEARN8-LEARN1,LEARN8-ALT and LEARN1-H2. Average four replicas within history
then four histories equally. Preserve all signs and cutoffs. A cutoff makes
that evaluation cohort incomplete; do not drop it or replace its seed.

All environment executions use p_four=.1,rank11 goal,2000 maximum actions,
and spawn after winning actions. Natural games have two initial spawns;
branches have none. BASE=151*100000000. Source seed=BASE+10000000+
life*1000000+query_index*100000+batch*10000+replica. Branch seed=BASE+
20000000+life*1000000+query_index*100000+batch*10000+replica*1000+slot*100+
suffix. Evaluation seed=BASE+90000000+life*1000000+checkpoint*10000+replica,
shared across methods and queries. Query order risk1,risk8; life0..3,
batch1..4,source replica0..1,evaluation replica0..3.

Charge all source/branch/evaluation transitions, random draws, teacher
planning, model updates/predictions, loads, storage and independent replay.
Retain inherited actual costs without adding overlapping budget views.
Audit terminal labels, complete-triplet matching, warm normalized updates,
frozen evaluation, module commitment, policy query binding, RNG and budgets.
This tests conditional use of two fixed policies. It does not establish
automatic strategy discovery or structural knowledge-base evolution.
H2 remains baseline; U005 FAIL and U006 remains unstarted.
