# V148: independent remeasurement of fixed training labels

V147 increased shared-feature support without improving prediction or control.
Test whether its existing training gains, and V145 UPDATED's gains, reproduce
on new outcomes at exactly the same TRAIN roots. Do not fit any model.

Keep all256 retained TRAIN roots (OLD128 from V144 examples, NEW128 from
V145). Acquire fresh labels for all173 action disagreements,45 OLD and128
NEW, including the SHARED zero-feature disagreement. The other83 OLD roots
have the same first action, so their paired components are exactly zero;
retain them in primary averages without additional interaction. No selection
uses old label signs, prediction errors, feature support or prior outcomes.

Freeze ZERO, UPDATED and SHARED predictions from retained V147 models before
any new outcome acquisition. ZERO's total prediction is the immediate reward
difference. Compose each total advantage as immediate difference + predicted
remaining score/2048 - failure_penalty*failure_difference + goal_bonus*success_difference.
Retain strict-positive H1 selection and H2 on ties. No updates or new policy games.

For each disagreement root run32 new independent paired suffixes:11,072
physical branches,5,536 pairs. Force the existing H1_CONT and H2 first actions,
then use the unchanged query-specific frozen H2 continuation and SINGLE leaf.
Reuse V143 run_branch: no initial spawns, environment p_four=.1, goal rank11,
spawn after every executed action including a winning one,2,000-action cap.
Both first actions use separately initialized RNGs with the same suffix seed.
BASE=148*100000000; seed=BASE+life*1000000+query_index*100000+
origin_index*50000+replica*10000+slot*100+suffix. Query order risk1,risk8;
origin order OLD,NEW; replicas0..3; slots0..3; suffixes0..31.
Retain every branch and all costs. A cutoff blocks complete-cohort scientific
claims; do not replace it or stop sampling based on intermediate outcomes.

Primary comparisons use the same sixteen roots per origin/query/history,
four roots per source game, then equal means over four histories. Report
disagreement-only means separately. For each unchanged predictor p_m report
old and fresh mean-label MSE, MSE gain over ZERO
((p_ZERO-y)^2-(p_m-y)^2), and fixed-gate value versus H2 and ZERO
(I[p_m>0]*y and (I[p_m>0]-I[p_ZERO>0])*y). Positive gains favor the learner.
The paired MSE gain cancels common fresh-label sampling variance in expectation.
Also report fresh suffix variance/32 and fresh MSE minus this variance,
unclipped. Old TRAIN predictions depend on old labels: no unbiased correction
claim applies to them. Keep OLD/NEW and queries separate, per-history signs,
old/fresh label sign agreement, and the four prespecified consecutive blocks
of eight new suffixes. These blocks describe sensitivity, not four new histories.

Count physical transitions, forced actions, continuation decisions, native
planning, frozen prediction work, loads and independent replay separately.
Existing acquisition/training/evaluation costs remain explicit references.
Freeze protocol, complete cohort/predictions and executable sources before
acquisition. Audit retained input correspondence, first actions, spawn RNG,
scores, terminal labels, query binding, unchanged models and accounting.
Four histories and one training-root distribution support a diagnosis;
this test alone cannot establish generalization or closed-loop policy benefit.
Keep H2 as the working baseline; U005 FAIL, U006 unstarted.
