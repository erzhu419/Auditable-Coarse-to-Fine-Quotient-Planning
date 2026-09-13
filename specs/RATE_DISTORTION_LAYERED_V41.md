# V41: one bounded horizon-layered soft-abstraction comparison

Frozen 2026-09-10 before V41 fitting or outcomes. Continue the V40 route once;
preserve U005 FAIL, U006 ineligibility, all earlier outcomes and paid samples.

## Inputs and intervention

Use exactly V39/V40's three public exact H2 models, gamma .95, legal completion,
raw and DoorKey-normalized reward/distance units, author source
`0d3b6f7e1cd63f8df8056bd35a0c82934390cefd`, independent betas [6,7,8,9,10].
Re-enumerate the three small closures and their missing distances; charge these
costs. Reuse V40's saved beta10 E/decoder/u/fixed_u/clamped_u for controls.
Reconstruction is not independent task validation. No new stochastic draws.

Fit the candidate separately within each positive remaining-horizon block,
using the original flat BA solver with uniform conditional prior, cap n_h,
max_outer=200, max_inner=50, tolerance=1e-6, no warm starts. H1/H2 encoders and
representatives cannot cross layers. Use an independent absorbing code with
encoder/posterior 1, decoder the original legal absorbing pair and value zero.
Concatenate blocks H1,H2,terminal; total initial code cap remains N legal pairs.
Preserve the original global pruning mass 1e-4 by passing 1e-4/(n_h/N) in each
active block. Compute global information with mu=1/N, including layer identity.
No action-specific split, reward correction, extra features or post-result fit.

The original transition model and Bellman maximum remain unchanged. Terminal
codes start at zero and remain zero through updates and ladder switches. Verify
exact zero cross-layer mass and terminal preservation; verify the descending
H2 structure settles within two synchronous updates from terminal-zero input.
These checks detect implementation/semantic faults, not scientific success.

## Readout, controls and endpoints

For all new policy comparisons (flat, clamp, layered, exact DP), divide Q by
its reward scale, select the first legal action in the existing ACTION_LABELS
order whose gap from the legal maximum is <=1e-12. This tolerance only affects
policy readout; Bellman values, controller residuals and switches use true max.
Evaluate chosen policies independently on original uncollapsed transitions.
Retain V40 exact-argmax policies and explicitly record any change from this new
readout rule; never overwrite or reinterpret old results.

Primary comparison: beta10 fixed points from zero for the layered candidate
versus the retained flat and terminal-clamp fixed points at the same beta.
Use original-unit iterate tolerance 1e-12, maximum 20,000; report residual and
actual update calls, terminal values, full legal-Q error versus exact Q,
root/state prediction minus actual-policy value and root/state policy regret.
Record the new tie-DP policy against the exact mathematical optimum as well.

Secondary comparison: the unchanged author adaptive controller on the five
layered fits, same 100N backup-unit budget and max-sweep/record rule as V39.
Retain each beta's fixed endpoint as a diagnostic; beta selection is forbidden.
Primary conclusions use beta10, never another beta's quality or cost.

Use the unmodified V40 array compiler at each beta. Compare author/compiled
updates and legal grounded Q on every layered adaptive snapshot, error <=1e-12
in original units, and separately count stable-readout action disagreements
and exact policy consequences. Save six beta10 operators and witnesses; replay
all in a fresh process with only compiler arrays, without original model imports.
No compiler, sparsity-layout or fit optimization is introduced in this experiment.

## Resource and route decision

Count literal operator arrays, legal encoder plus pair-index readout, deployed
u, and their sum. Report common state/board lookup separately as excluded from
all compared numeric payloads. Also report full P/r and the exact fixed-task
policy cache (and policy+V cache): a repeated identical query needs no replan.
Dense zero entries are charged as stored; theoretical sparse savings are not.

Measure new acquisition/distance, five fits, rectangular embedding, per-beta compilation, adaptive
budget execution, fixed-point solving/readout and independent evaluation
separately. The primary beta10 model cost uses its own fit/compile/solve plus
common acquisition/distance and actual embedding/grounding, while all performed experiment work remains paid.
Flat construction timings are retained V40 costs, not a new paired speed test.
Compare candidate one-query deployment preparation with current exact DP using
the same acquisition cost; do not count evaluation/verification as deployment.
The exact deployment baseline is the author's tabular optimal-value DP plus
Bellman Q and stable readout. Its Q must agree with the independent original
finite-horizon solution; obtaining that original truth/evaluation is charged
separately, not included in the deployment timer.
No same-query amortization or statistically established speed claim is made.

Continue the efficiency branch only if the same beta10 candidate meets all:
- all six root policies have regret <=1e-10;
- versus flat, absolute root calibration error divided by max(|V*|,1e-12)
  does not worsen by >1e-6 in any condition and improves by >1e-6 in at least one;
  report the clamp comparison in full as an additional control;
- at least one of the six conditions has both a smaller complete numeric model
  than P/r and lower measured one-query preparation cost than exact DP at that
  condition. Report cached-policy storage too; backup-only speed is insufficient.

These are exploratory route decisions, not a new formal assurance Gate. If the
conditions fail, end the current flat/layered BA efficiency-candidate branch;
preserve structural findings and the paper replication. Do not expand seeds,
beta, budgets, queries or sampled models to rescue this result. Any later
research direction must state a new task with actual reuse opportunities.
