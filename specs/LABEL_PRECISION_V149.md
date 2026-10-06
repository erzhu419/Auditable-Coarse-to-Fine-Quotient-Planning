# V149: label precision under a fixed learner

V148 found that training-label fit gains failed to reproduce at the same roots.
Change only the number of paired suffixes averaged into each training target.
TRAIN8 uses retained V148 suffix indices0..7; TRAIN32 uses indices0..31.
Both use the identical256 TRAIN roots, with83 same-action exact zeros and173
action disagreements (OLD45, NEW128). Keep the collapsed SHARED disagreement:
the present learner uses the unchanged V144/UPDATED six-cell representation.
No root selection uses labels, feature support or model performance.

For each life0..3 and query risk1/risk8, initialize each new PairedAdvantage
model with zero weights. Run32 ordered passes OLD16 then NEW16 with alpha=.1,
the same signed feature multiplicities and three-component normalized LMS.
Average paired H1_CONT-minus-H2 total reward/2048, failure and success, then
subtract the exact immediate reward difference once from the reward target.
Each method makes8,192 update attempts; the two new learners make16,384.
Retain original UPDATED and ZERO unchanged. ZERO keeps its existing empty
shared-format checkpoint; its total prediction is the immediate reward difference.

Freeze all32 models (16 new,16 references) and all1,024 fixed-root predictions
before acquiring independent evaluation labels. Use the unchanged strict
positive recomposed-advantage gate, with H2 on ties. No new complete policy
games or model fitting follow inspection of evaluation results in this run.

For each of173 disagreement roots acquire32 independent paired suffixes:
5,536 pairs/11,072 branches. Keep all83 same-action roots as deterministic
zero differences without sampling. Reuse V148 acquisition and V143 run_branch:
force the retained H1_CONT/H2 first actions, then the query-specific frozen H2
continuation; SINGLE leaf, no initial spawns, environment p_four=.1, goal rank11,
spawn after winning actions,2,000-action cap. Both actions separately initialize
their RNG with the same suffix seed. BASE=149*100000000; seed=BASE+
life*1000000+query_index*100000+origin_index*50000+replica*10000+slot*100+suffix.
Queries risk1/risk8; origins OLD/NEW; replicas0..3, slots0..3, suffixes0..31.
Keep all outcomes and costs; any cutoff blocks complete-cohort scientific
claims. Do not replace roots, stop early or change the budget after outcomes.

Report OLD and NEW sixteen-root means separately and their equal combined
32-root mean per life/query, then four-history means and signs. The main
contrast is TRAIN32 versus TRAIN8: MSE reduction and fixed-gate value change.
Also compare each learner against ZERO's MSE and H2/ ZERO gate value. Positive
MSE reduction means smaller error. Report new-label variance/32, unclipped
noise-corrected MSE, and four fixed blocks of eight suffixes. Label-based
training diagnostics (both eight/32 targets) are dependent observations and
cannot establish independent gains. Lower error relative to TRAIN8 alone
does not establish useful decisions or improvement over H2.

Reuse V148 labels with zero new training-environment interaction; retain its
full actual acquisition cost and earlier costs by references. Record nested
TRAIN8/32 used-pair, branch and transition counts as budget views, without
adding them or treating unused portions as refunded. New evaluation work is
counted once, shared by four frozen predictors. Charge target reads, training,
frozen prediction, loads, actual transitions/planning and independent replay.
Freeze protocol and executable sources before fitting; retain fitted models
and predictions before sampling. Audit label construction, update order/weights,
fresh streams, terminal returns, unchanged continuation and accounting.

This is an exploratory fixed-root intervention with four learning histories.
Use the result to decide whether target precision or regularization deserves
the next intervention; keep H2 while general strategic learning is unresolved.
U005 FAIL; U006 remains unstarted.
