# V92: paired continuation learning and terminal residual correction

Frozen before V92 fitting/acquisition/evaluation. V91 reduced the variance of
predictions but increased full-return residual variance. This experiment learns
the paired continuation quantity directly and tests correction against independent
terminal outcomes. It is a method comparison, not a new assurance gate.

## Pair learning from fixed historical trajectories

Use V83 original branch games from lives 0,1,2 and cumulative checkpoints 6,12.
Keep episode%5==4 out of all fits. A training root must have all five options at
all eight complete terminal replicas; incomplete roots retain cost, not labels.
No V89 additional data, V90 replay or V91 evaluation data enter learning.

For each candidate/H2 pair take fixed step indices k=4,20,36,... while at least
one arm is active. Both active arms now run the same query-conditioned H2 policy.
Inputs contain only the two current boards and current active indicators; episode,
option, replica and step are provenance, not features. Targets are the candidate
minus reference remaining reward/2048, future failure and future success. A side
already terminated has zero remaining consequences and its observed final board.
The two arms share initial environment/model seeds and use two/four random draws
per active step. Equal active states at the same index therefore have equal tails.

Use weight 1/32 for each recorded pair row. Do not add an outcome-selected last
step or divide weights by eventual trajectory length. Those V91 choices change
the regression target distribution; V92 changes both paired representation and
the state-sampling/weighting rule. It does not isolate these changes individually.
Longer trajectories supply more fixed-grid rows; rows are not independent episodes.

For each query fit a three-output tree, max_depth=8, min_samples_leaf=16,
random_state=9201. Features are 36 board-feature means, 36 candidate-reference
differences and two active indicators. Add each swapped pair with negated target,
giving both orientations half the row weight. Predict one half of the difference
between the two oriented predictions. This preserves antisymmetry and exact zero
for equal states; two absorbed sides have zero tail. At each checkpoint fit full,
exclude-even-episode and exclude-odd-episode models. Historical training labels
use the model excluding their entire episode fold; heldout diagnostics use full.
Only source episodes earlier than the checkpoint enter fitting.

## Shared prefix data and three estimators

At each historical root obtain M=64 new independent four-action prefixes for
each of the five options. A one-action option then runs three H2 actions; a
four-action option completes its commitment. A terminal prefix ends normally;
ACTIVE after action four is a planned boundary, never a failure label. Preserve
all raw prefixes. For each root/query/replica share environment and model streams
across options. Training-prefix environment seed is 92000000000+life*10000000+
query_index*1000000+episode*1000+replica; model seed adds 1000000000000.
Acquire each root's prefix pool once, reusing the earlier batch at checkpoint 12.

Let Y be the complete paired R/F/S difference and Z the observed four-action
direct difference plus the learned paired tail. N=8 original terminal pairs and
M=64 new prefixes are distinct, and the root's fitted predictor excludes that
whole episode. Construct:

- MC: mean(Y_N).
- PAIR_ONLY: mean(Z_M).
- CORRECTED: mean(Z_M) + mean(Y_N - Z_N).

Fit the same V84 JointSelector for each: fixed 36-to-12 trees, depth 3, min leaf
2 roots, random_state8301, four candidates and exact zero H2. Head data and actual
acquisition cost are shared. MC does not receive complete outcomes for the short
prefixes. A better allocation of the prefix budget to extra MC terminal samples
is not tested here; do not claim sampling efficiency from this comparison.
Record each component's conditional variance: corrected mean variance includes
squared-error dispersion of Z_M divided by M plus that of Y_N-Z_N divided by N.
These quantities omit fitted-model uncertainty and are not confidence guarantees.

## Fresh behavior and independent finite terminal reference

Checkpoint6 methods: H2_ONLY, MC, V91_DECOMPOSED, PAIR_ONLY, CORRECTED.
Checkpoint12 adds CORRECTED_FROZEN_6, a payload copy of the initial corrected
selector. V91_DECOMPOSED loads the corresponding saved V91 selector, with no new
fit. At each life/query/checkpoint run 16 natural games, 2000-action maximum,
total1056. Environment seed=9290000+checkpoint*10000+life*100+replica, execution
model seed adds1000000. Rotate method order, retain common pretrigger histories,
single commitments and four model draws per active action, and all outcomes.

Before observing results fix twelve reference roots: checkpoint12 H2 replicas0,1
for every life/query at the original <=6-empty-cell trigger. Missing triggers
remain missing, without replacement. For each root collect 24 terminal replicas
of all five options using V83 sample_root with life=92000+life. Its environment
seed is 8310000000+(92000+life)*10000000+query_index*100000+episode*100+replica;
model seed adds1000000000000. Replicas0..7 supply N=8 estimation pairs and8..23
supply a separate sixteen-replica finite outcome reference. Also acquire M=64
independent four-action prefixes, environment seed=93000000000+life*10000000+
query_index*1000000+episode*1000+replica; model seed adds1000000000000.
No reference or evaluation observation updates a fitted model.

Compare MC, PAIR_ONLY and CORRECTED root estimates to the independent last16
outcomes. MC is not compared to its own estimation samples. Report root/candidate
errors, paired residual variance, both variance terms and reference uncertainty.
Evaluate final selectors on these same roots, with their choices fixed before
reference outcomes. Shared candidates/reference arms are not independent roots.

## Interpretation and execution

Primary behavior contrasts: CORRECTED versus MC, PAIR_ONLY, V91_DECOMPOSED and
H2, plus its own frozen-6 selector at checkpoint12; also PAIR_ONLY versus MC.
Average lifecycle effects equally within query, retaining lifecycle detail.
Separate newly enabled, changed, cancelled, unchanged and both-H2 decisions.
Prediction smoothing, label MSE or cancellation gains alone do not establish
new useful knowledge. This is a fixed batch learning algorithm, not online TD.

Attempt every fixed replica, without outcome-dependent stopping/replacement.
Keep terminal cutoffs and costs; they supply no full-return labels. Four-step
prefix boundaries are intentionally nonterminal and are counted separately.
Complete primary interpretation needs all planned natural games and full-return
reference cohorts terminal. Original historical acquisition, reused V91 fitting,
new prefix sampling, new paired/head fits, natural games, independent full/prefix
reference acquisition and computation are separate costs. Freeze source before
new work and retain snapshots and raw data. U005 FAIL and U006 unstarted persist.
