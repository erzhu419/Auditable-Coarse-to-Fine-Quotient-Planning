# V88: learn positive, negative, and unresolved paired candidate evidence

Frozen before V88 production label inspection, fitting, or evaluation. V87's
mean update did not produce new aggregate strategy gains. This experiment
changes the learning target from mean consequences to evidence about advantage.

## Paired evidence and learned regions

For each lifecycle 0/1/2 and allocation COVERAGE/REPEAT, concatenate original
V83 checkpoint 6 and 12 root logs, then append V86 complete allocation blocks.
Group by query, episode, and board. Repeated replicas extend their original
root; incomplete blocks supply no labels. Reconstruct all four candidate R/F/S
means and require agreement with V86's final training_rows before fitting.

For each candidate, compute scalar utility for each paired replica, including
the R/F/S covariance through the original query utility. With n replicas define
SE=sample_standard_deviation(ddof=1)/sqrt(n). Label positive if mean-2*SE>0,
negative if mean+2*SE<0, otherwise unresolved. A zero mean with zero variance is
unresolved. This fixed two-SE rule is an exploratory evidence convention, not
a calibrated confidence interval or a guarantee under adaptive selection.

Fit one four-output DecisionTreeClassifier per query, predicting the candidate
labels jointly from the same 36 board features, depth 3, minimum leaf 2 roots,
random_state 8301. Episode%5==4 roots remain held out of splits, class frequencies,
and leaf means. Roots have equal weight; sixteen replicas improve a root's label
precision without duplicating it. Store each leaf's three label frequencies per
candidate and its mean R/F/S consequences over the same training roots.

POINT selects the candidate with highest strictly positive leaf mean utility.
SUPPORTED uses exactly the same tree and means, but considers only candidates
with positive-label frequency strictly above 0.5. It selects the highest positive
mean among these, or H2. The frequency denotes training-root labels, not the
probability of positive true advantage. Both use the original OPTIONS tie order.
Their partition and predicted means must match exactly; the evidence restriction
can suppress an intervention or select another candidate. Also retain OLD, the
unmodified V86 selector, to expose changes caused by the new partition/target.
Export models, reconstructed replica data, evidence labels, and learning logs
before evaluating each lifecycle. Count twelve new classification trees total.

## Independent deployment and attribution

Methods: H2_ONLY and each allocation's OLD, POINT, SUPPORTED. Run sixteen natural
games per query and lifecycle: 672 games. Environment seed=8890000+life*100+replica,
replica=0..15; model seed adds 1000000. Pair all methods and queries by seed and
rotate execution order. Keep V83's first active <=6-empty-cell trigger, one
committed one/four-step fragment followed permanently by H2, four model uniforms
per active action, and terminal/2000-action stop. Three lifecycle workers run
concurrently. No additional training source games or paired branches are acquired.

Primary contrasts per allocation: SUPPORTED-POINT, SUPPORTED-OLD, POINT-OLD,
SUPPORTED-H2, POINT-H2. Average within lifecycle, then equally across lifecycles.
Use the common seven-method terminal cohort; retain all cutoff histories/costs.
For SUPPORTED versus POINT and OLD, classify enabled, disabled, same_fragment,
changed_fragment, both_h2 at the shared trigger. Check exact full histories for
identical choices. Category contributions divide paired sums by the full common
cohort size before lifecycle averaging. Report changed/enabled candidate benefit
against H2 separately from cancelled-intervention recovery. Improvements from
H2 fallback alone do not demonstrate new strategy learning. Fresh game suffixes
provide the new outcome evidence; previously inspected V86 validation roots do
not supply new validation or tune this method.

## Work and interpretation

Count actual evaluation transitions (hard maximum 1,344,000), preparation,
classification fits, prediction traversal, and wall time. Carry forward V83
acquisition, V84/V85 construction, V86 base loading and each allocation's
acquisition/fitting. V87 models and previous evaluation/validation are not
construction inputs here. Shared method cost attributions are not additive
actual work. Retain synthetic-fit and real-controller test work separately.

This tests whether sampling evidence can guide reusable candidate selection in
the existing one-initiation fragment family. Keep negative and all-abstaining
outcomes. Do not change evidence thresholds, tree parameters, candidates, seeds,
or replica counts after observing labels/results. U005 stays FAIL; U006 unstarted.
