# V193 — Similar geometry does not ensure consequence transfer

**Coverage expansion is not the supported first response to V192's failure.**
This diagnoses the fixed model and retained TARGET96, without new fitting or
labels. The reference uses 1,518 ordered SOURCE action pairs, excluding each
query's entire SOURCE group; joint-distance Q95 is 0.338688.

| Retained cohort | Within SOURCE joint Q95 | Opposite nearest-SOURCE tail direction within Q95 |
|---|---:|---:|
| All NONLINEAR errors | 46/50 | 28/46 |
| New errors versus LINEAR | 17/18 | 9/17 |

Only six of all 96 pairs exceed joint Q95; four have individually covered
endpoints. No exact zero-distance pair-label conflict appears.

The largest loss, `v192_target_r01_17`, exposes an additional failure: DOWN
beats LEFT by **+2.281642**, but the model predicts **−0.349365**. First-reward
gap is −0.093750; true tail R/F/S gap is **[1.375392, 0, 1]**, versus model
**[0.010365, 0.027215, −0.238765]**. The nearest SOURCE tail gap is positive
(+0.300330), yet the global center combination is negative. Center utility
contributions sum from +48.906138 and −49.161752. Exact action replay passes;
this is a learned-function error, not a floating-point decision mismatch.

**Next:** replace global signed-center extrapolation with conditional transfer
of complete same-board action-pair consequences. Preserve goal-relative merge
and blocker conditions when deciding which SOURCE pairs apply, then combine
their R/F/S differences with nonnegative local weights. Learn/select only on
SOURCE groups; freeze before fresh targets, keeping LINEAR and V192 controls.

**Verification:** 16 tests, **29/29 audit, 35/35 source, 8/8 input** comparisons
pass; main/audit once, **7.48/8.24 s**, stderr 0. 534 frozen centers; 96 decisions
and 188,502 target kernel evaluations reconstructed. Zero new fits, solves,
eigen/SVD, feature derivations, SOURCE scores, labels or physical kernels.

**Limitations:** Q95 is geometric coverage, not semantic sufficiency. Nearest
label reversals and signed contributions are diagnostic evidence, not causal
proof. No observed exact alias does not prove the representation sufficient.
Finite H3/fixed teacher; general strategy remains unresolved. Keep H2;
U005 FAIL, U006 unstarted.

[Protocol](../specs/KERNEL_TRANSFER_V193.md) · [Summary](controlled_predictive_kernel_transfer_v193/summary.json) · [All roots and contributions](publication/v327_snapshot/controlled_predictive_kernel_transfer_v193/diagnostics.json.gz) · [Reference](controlled_predictive_kernel_transfer_v193/reference.json) · [Audit](controlled_predictive_kernel_transfer_v193/analysis.json) · [Ledger](v193_runtime_tmp/stage_checks.json)
