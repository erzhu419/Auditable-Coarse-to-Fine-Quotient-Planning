# V158: bounded independent-suffix label precision

Frozen before sampling, 2026-09-27. Keep all 64 V153/V157 roots, their
query/source/history strata, frozen OLD checkpoint 4, eight-step module,
H2 teachers, gate and reward definition. Change only the number of fresh
training suffixes used to select the initial intervention. No representation
fit, threshold changes, checkpoint choice, or new root selection.

For each root acquire 32 TRAIN and 32 independent EVAL suffixes. Pair
H_GATE (own H2 one step then OLD gate) and M_GATE (other H2 eight steps
then OLD gate) on the same suffix seed. Reuse V153 branch semantics,
including target-query utility, each teacher's own query, gate reset after
the prefix, 0.1 probability of rank 2, winning-swipe spawn, and at most 2000
transitions. The seed is 15800000000 + 20000000 + split_index*10000000
+ life*1000000 + query_index*100000 + source_index*10000 + slot*100 + suffix,
with TRAIN/EVAL indexed 0/1, risk1/risk8 and H2/LEARN8 indexed 0/1,
slot 0..3 and suffix 0..31. No seeds overlap V153; modes share seeds.

For n=8,16,32 use TRAIN suffixes 0..n-1. Accept only when mean paired
utility difference M_GATE-H_GATE is strictly positive; zero rejects.
Complete all TRAIN acquisition and freeze all 192 decisions on disk before
any EVAL acquisition. All candidates and controls share the same new EVAL32.
The primary candidate is n32; the primary precision contrast is n32 minus n8.
n8/n16 describe the nested budget curve; do not choose the best n afterward.

Primary outcomes: n32 gain versus OLD, always reject and always accept, and
paired n32-minus-n8 gain. With evaluation difference d, decisions s32,s8 and
OLD o these samples are (s32-o)d, s32*d, (s32-1)d and (s32-s8)d. Average
equally over all roots within each history and then over the four histories,
separately for each query; also retain both source strata and histories.
Unchanged decisions contribute zero. A positive precision contrast alone
does not establish useful control: retain all baseline comparisons.

Pointwise conditional 95% intervals use mean ±1.96*SE, with
SE²=sum_root(w_root² * sample_variance(paired EVAL samples)/32).
Condition on fixed roots, teachers, histories and frozen TRAIN decisions.
Compute precision-contrast variance on paired differences, not by adding
the two candidates' variances. Intervals do not capture training-selection
uncertainty, generalization to new roots/histories, or multiple comparisons.
Nested budgets and shared evaluation are not independent replications.

The fixed cap is 8192 physical branches (4096 TRAIN and 4096 EVAL), at most
16,384,000 environment transitions. Count physical acquisition once; expose
the actual prefix training costs for each budget and the shared full EVAL
cost. Preserve all cutoff branches and costs; affected means/intervals remain
incomplete, without favorable-root filtering or replacement. Do not extend
the cap after seeing outcomes. Zero new learned-model updates.

Retain full new branch traces for one independent physics/RNG/gate/cost
replay, compact outcomes for metrics, frozen roots/models/code and existing
cost references. Reuse prior source metadata rather than rereading old
trajectories. Focused tests cover seed separation, freeze order, leakage,
paired contrast variance and incomplete-label handling. Main/audit run once.
If this cap gives no stable independent gain, preserve that result and turn
to variance reduction or module consequence design instead of automatically
doubling samples. Keep H2; U005 FAIL and U006 unstarted.
