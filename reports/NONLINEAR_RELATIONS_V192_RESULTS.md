# V192 — Better SOURCE fit, negative fresh transfer

**Shared nonlinear relation learning improves SOURCE fitting but does not
solve transfer.** Keep the 98 input columns and SOURCE143/36 groups fixed;
SOURCE-only group validation selects RBF gamma=1, lambda=0.001, utility 1.239221.
SOURCE regret roots fall **72→53**, mean regret **0.109982→0.036994**.

The frozen model then evaluates 96 fresh H3 boards:

| Comparator | NONLINEAR utility difference | Comparator regret roots |
|---|---:|---:|
| LINEAR | −0.024991 | 42 |
| RELATION | −0.019763 | 40 |
| OLD_SHARED | −0.013751 | 42 |

NONLINEAR has **50/96 regret roots**. All three contrasts have two positive
and two negative replicas. Against LINEAR it introduces 18 errors and repairs
10; failure probability rises 0.019260→0.026063, success falls
0.324306→0.315972, and reward falls by 0.009856. One root contributes 75.15%
of positive gains. **Do not adopt this model.**

**Next:** fix the model and parameters; compare selected–optimal action pairs
with individual SOURCE action neighbors and same-board SOURCE pair neighbors,
then decompose the fixed kernel's reward/failure/success contributions. Use
all retained roots, with the 18 new errors and largest loss
`v192_target_r01_17` as concrete examples. This tests coverage versus incorrect
combination without new fitting, labels or kernel tuning.

**Verification:** 18 synthetic tests; corrected **220/220 audit, 88/88 source
and 8/8 input comparisons** pass. Main ran once, 47.21 s, stderr 0. The first
audit failed on teacher metadata import after 1.40 s (stderr 1616 bytes);
its record and frozen sources remain. Corrected audit takes 28.79 s, stderr 0.
31 predictors, seven eigen decompositions, 96 kernels/plans; no physical
samples/native updates. Audit pays one incomplete plus 31 corrected direct
solves, zero repeated eigen/SVD, training or labels.

**Limitations:** Finite H3 and fixed continuation teacher. This rejects the
frozen RBF learner on this cohort, not every nonlinear function or the input's
information sufficiency. Near-neighbor diagnostics do not prove causality.
General strategic learning remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/NONLINEAR_RELATIONS_V192.md) · [Summary](controlled_predictive_nonlinear_relations_v192/summary.json) · [Audit](controlled_predictive_nonlinear_relations_v192/analysis.json) · [Original ledger](v192_runtime_tmp/stage_checks.json) · [Correction](v192_runtime_tmp/AUDIT_METADATA_AMENDMENT.md) · [Corrected ledger](v192_runtime_tmp/corrected_stage_checks.json)
