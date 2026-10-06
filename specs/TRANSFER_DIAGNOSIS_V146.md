# V146: retained-label noise and signed-feature transfer

V145 expanded informative training pairs from45 to173 without control gains.
Freeze this descriptive diagnosis before reading individual suffix outcomes.
The primary cohort is all128 NEW V145 held-out roots (replicas4..7); the
secondary cohort is all128 OLD V143/V144 held-out roots with the same split.
Keep all roots, including OLD identical-action and zero-feature pairs.
Keep the V145 PRIOR, REPLAY and UPDATED predictions and weights unchanged.

For each root use all eight existing common-suffix H1-minus-H2 terminal
utility differences y. Compute scalar utility before variance, retaining
reward/outcome covariance. All targets remain conditional on H2 continuation.
Sample variance s² uses denominator7; s²/8 estimates the eight-suffix mean's
noise variance. Report observed (prediction−mean(y))² and subtract s²/8
without clipping. This is an unbiased error estimator for a predictor
independent of these held-out suffixes, not a nonnegative attribution.

Use fixed halves0..3 and4..7 for means, three-way signs, strict-positive gate
agreement, positive/negative pairs and explicit ties. Also summarize all35
unique unordered4/4 partitions (first half contains index0). These overlap
and are not35 independent replications. The fixed cross-half residual product
is a noisier view; averaging that product over all35 partitions is exactly
the noise-corrected error, not independent corroboration.

Use unchanged exact signed V144 n-tuple multiplicities. PRIOR and REPLAY use
the old16 training roots per history/query; UPDATED uses old16 plus new16.
Report covered squared feature norm, exact training-orthogonality, maximum
absolute training cosine and squared projection into the training row span.
Compute the projection through the Gram eigensystem with relative eigenvalue
cutoff1e-10; only roundoff within1e-8*max(1,query_norm²) may be clamped.
Zero query norms have null fractions and explicit counts. Zero-initialized
linear LMS weights remain in the training row span. Low projection establishes
limited training support, not a quantified cause of utility error or proof
that the true advantage depends on the missing directions.

Aggregate roots equally within each original game, games within each history,
then the four histories equally. Report both origins separately, with counts
of identical actions, zero features and ties; geometry fractions use nonzero
features and retain their denominators. No confidence interval, favorable-root
selection, hyperparameter choice, refit, new environment sample or gate change.
These are previously inspected diagnostic sets, not sealed new tests.

Retain input references, cohort, code, per-root values, summaries and costs.
Read compressed branch summaries locally; reuse the already validated source
trajectories without environment replay. Independently verify variance by the
pairwise-difference identity and projection through direct matrix SVD. Charge
these computations separately. Preserve V145 costs by reference; do not count
old records as newly acquired samples. U005 remains FAIL; U006 stays unstarted.
