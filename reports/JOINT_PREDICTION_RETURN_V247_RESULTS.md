# V247: joint one-batch prediction fails

**FAIL: 4/5 conditions; independent audit valid=true, zero failures.** The fixed-proof predictor is not adopted. All 72 paired outcomes and sampling costs tie; return quality remains below 54/72.

| Arm | Query / joint completion /72 | Full charged observations | New SHORT / DETOUR / RETRY | Model CPU seconds |
| --- | ---: | ---: | ---: | ---: |
| ONE_WAY | 48 / 48 | 46,672 | 3,696 / 4,624 / 592 | 1,474.26 |
| JOINT_PREDICTION | 48 / 48 | 46,672 | 0 / 0 / 8,912 | 1,503.34 |

The [frozen protocol](../specs/JOINT_PREDICTION_RETURN_V247.md) preserves the common paid prefix, fresh paired streams, budgets, certifiers and stopping; all 144 decisions precede truth scoring. Each arm pays the full 37,760-observation prefix.

The [retained diagnosis](v247_runtime_tmp/joint_prediction_diagnosis.json) finds **557 active choices, all RETRY**, with no fallback. SHORT→RETRY dominates every selected maximum. The best candidate predicts worsening in 472/557 batches; actual progress is negative in 398/557. Mean predicted/actual improvement is −0.001236/−0.001424, against a missing log margin averaging 16.153. All 24 previous failures remain. Unresolved goal SHORT→RETURN and risk RETURN→SHORT each increase from ONE_WAY's 18 to 24.

Three first-batch pairs share identical starting evidence and actual S/D histograms equal to the predicted histograms. At life 0, target 58, risk deficit starts at 8.649: the fixed tangent predicts **18.362**, but the existing engine's updated proof gives **8.490**. Lives 1/2 also predict risk deterioration while actual proofs improve. Their dominant SHORT→RETRY bounds still deteriorate, so these examples expose proxy looseness without establishing a better unselected joint action.

Next stop this one-batch score. First distinguish genuine full-region bad kernels from loose bounds at the retained endpoints; then test shared mechanism acquisition **before return**, within the same complete lifecycle budget and against strong REBUILD. The core problem remains valuing evidence across queries and episodes.

Validation: **24 targeted tests passed**; one producer run, 525.02 seconds, and one independent audit, 144.38 seconds, checked 1,258 plans and all 73,524 prediction cells. All certificate/execution error counts and binary tolerance are zero. Seventy-six source files were captured. Acquisition CPU is 1.008 versus 102.146 seconds, included in model CPU, which rises 1.97%. [Summary](joint_prediction_return_v247/summary.json), [analysis](joint_prediction_return_v247/analysis.json), [execution metadata](v247_runtime_tmp/verification_summary.json).

Limitations: this selected-prefix qualification does not establish complete-lifecycle or general learning results, or impossibility for all budget-matched allocations. Later starting evidence differs in 21/72 pairs; confidence guarantees remain unconditional over each full process. Producer stderr retains 591 bytes of clipping warnings; audit stderr is empty. The original scientific Gate and U006's unstarted status remain unchanged.
