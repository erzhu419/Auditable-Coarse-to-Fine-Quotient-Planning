# V204 — knowledge-guided acquisition of member risk evidence

V203 supplied reliable bounded risk plans but unobserved combinations retained only5.15% of constrained optimal utility and95% WAIT. V204 acquires evidence for those same four members. Task, graph, costs, queries, H4 and delta=1/20 stay. Freeze this protocol and implementation before new draws; do not tune after results.

Pre-acquisition design review added COLD_POLICY before any focused test or new sample. With uninformed categorical means and the supplied low-cost graph, DETOUR_RETURN has point goal/risk ratio3.85 versus SHORT3.8. A local greedy forecast's poor prior must not be the sole basis for claiming useful inherited knowledge. This strong prior-only control is part of the final frozen protocol.

## Prior knowledge and arms

Retain V202 cases.json, batches.json, snapshots.json and run.json. Its FINAL_REUSE REVISED/FULL_CONTEXT models contain5376 historical controlled samples per lifecycle. Conditions remain fixed; update raw sufficient counts and Dirichlet alpha=.5 posterior means after each real batch. No new condition selection or fixed-strength pseudo-prior. Source costs remain paid and reported.

Four arms:
- GUIDED: REVISED fields/counts; next operator chosen by the model-based information forecast below.
- UNIFORM: same REVISED fields/counts, cyclic SHORT_PASS, DETOUR_PASS, RECOVERY_RETRY acquisition.
- NO_SHARE: FULL_CONTEXT fields/counts; same forecast rule as GUIDED. Its four new complete contexts start with uniform categorical priors despite old-context experience.
- COLD_POLICY: FULL_CONTEXT fields/counts; choose the non-WAIT pure policy with greatest point goal utility divided by point failure probability, ties lexicographic policy. Its Dirichlet means have positive non-WAIT risk. Query the chosen policy's operator with greatest expected occupancy: SHORT has SHORT_PASS1; DETOUR_RETURN has DETOUR_PASS1; DETOUR_RETRY has DETOUR_PASS1 and RECOVERY_RETRY equal to its point recovery probability. Operator ties follow the fixed operator order. This uses supplied graph/costs and local evidence, not inherited conditional probabilities.

Twelve lifecycles carry forward their V202 models. Target contexts in fixed order are wet/low then blocked/low, each retry17/20 then19/20. Each arm keeps its own persistent counts across all four contexts. No resetting between targets.

## Acquisition and paired streams

Batch16 single-step controlled resets to one operator, max384 total draws per target/context/arm across all three operators. Stop only on batch boundaries. Per complete target and operator, seed204000+(life*4+target_index)*3+operator_index, operator order SHORT/DETOUR/RETRY. Each arm has its own Random with the same seed and consumes only requested prefixes; no unused suffix generation. Thus a marginal stream's same prefix is paired across arms. Each arm's simulator calls, including repeated seeded observations, are separately charged. Max73728 new calls across all arms/lifecycles.

Acquisition uses only current model and observed counts. The simulator alone owns true laws. Save chosen operator, all three forecast scores, increment categorical counts, operator prefix start/end, cumulative sample counts and current whole-policy plan after each batch. Raw tapes are unnecessary.

## Confidence at adaptive observation and stopping points

Per lifecycle the fixed family has old8 contexts times7 categories at their unchanged sample sizes, plus new4 times7 categories times24 possible positive observed sample counts16,32,...,384. Total728, alpha=.05, beta=log(2*728/.05). Use64 KL endpoint bisections and outward rounding to2**40 as in V203, but with this beta. Unknown operators retain full simplex.

The common potential streams let a union bound over these fixed prefixes cover all arms and their adaptive choices/stops, at least95% per lifecycle under independent categorical sampling. This is not a joint95% statement across twelve lifecycles. Intervals use only raw complete-context real counts, never learned-leaf pooling or hypothetical observations.

## Common robust goal planning and stop

All arms use the same member boxes intersected with simplex, V203's exact common-kernel risk maxima, and maximize worst-envelope goal utility R+4S subject to risk upper<=1/20. Use exact Fraction vertices and two-policy crossings, lexicographic mix ties. Preserve predicted point joint R/F/S separately from lower goal utility and upper risk.

Common utility minima: let short success dS-=max(LshortDelivery,1-UshortLost); retry success t-=max(LretryDelivery,1-UretryLost); detour success dD-=max(LdetDelivery,1-UdetLost-UdetRecovery), a=4*t--retry_cost. Choose recovery r*=min(UdetRecovery,1-dD--LdetLost) if a<0, otherwise max(LdetRecovery,1-dD--UdetLost). Pure goal lower bounds are0, -short_cost+4*dS-, -detour_cost+4*dD-, and -detour_cost+4*dD-+a*r*. Since4 exceeds both0 and a and a has a mixture-independent sign, one kernel attains these minima for every nonnegative complete-policy mixture. Mix lower utility is the weighted sum.

After each actual batch, stop on utility_lower>=2; otherwise stop at384 draws as budget exhausted. No oracle is consulted. Unknown-context initial robust lower-utility planning can choose WAIT; do not compare this new common objective/beta with V203 as an acquisition effect.

## Model-based one-batch forecast

For GUIDED/NO_SHARE, compute the current posterior successor mean p for each operator. For each candidate operator separately, on a disposable copy of this member's counts, append16*p fractional expected counts, reconstruct prospective boxes and its best robust lower goal utility. Select the largest forecast lower utility (equivalently gain over the common current value); ties follow SHORT, DETOUR, RETRY order. This is a one-batch heuristic information forecast, not an exact expectation. Fractional counts never become experience, update models or certify a real plan; retain only forecast scores. UNIFORM has no forecasts.

Only actual integer samples update model tables; freezing fields does not freeze parameters. Query/restoration behavior can be worse with shared knowledge; do not change the rule or budget to force a benefit.

## Evaluation and retention

Freeze every target history/terminal plan and initial/final old-context decisions before oracle evaluation. Replay complete randomized target plans and the three query pure policies for the old8 contexts on the true H4 graph. Report per-arm target restoration count (certificate met), total samples/mean censored effort (failed targets count384), true risk violations/maxima, true utility, WAIT and confidence coverage, first retrospective true utility>=2, and initial-to-final old-query mean regret change. No retrospective result feeds sampling or stopping.

Bootstrap5000 shared12-index lifecycle resamples, seed204900, boundsindices124/4874. Lifecycle contrasts: UNIFORM−GUIDED target mean sample cost; NO_SHARE−GUIDED cost; COLD_POLICY−GUIDED cost; GUIDED−UNIFORM true terminal goal utility; GUIDED−NO_SHARE utility; GUIDED−COLD_POLICY utility. Shared cases are not independent training replicas.

Four frozen conditions, all required for TARGET_ACQUISITION_SUPPORTED:
1. RISK: all GUIDED target history and initial/final old-context hard plans have robust bounds and true risk<=1/20.
2. RESTORATION: GUIDED reaches the common certificate in at least36/48 targets and mean true terminal goal utility>=2.
3. ALLOCATION: mean UNIFORM−GUIDED cost>=16, its paired95% lower bound>0, and GUIDED restoration count is at least UNIFORM's.
4. KNOWLEDGE: both mean NO_SHARE−GUIDED and COLD_POLICY−GUIDED cost>=16 with each paired95% lower bound>0, GUIDED restoration count at least both controls', and old8-context three-query mean oracle regret worsens by at most.01.

Otherwise TARGET_ACQUISITION_NOT_SUPPORTED, keeping every failed component. Source5376 samples per lifecycle and actual historical source-learning work are reported alongside target cost; no overall cost benefit follows from fewer target samples alone. NO_SHARE and COLD_POLICY on these targets are equivalent to cold local estimators; report their target-only sample totals as zero-source cold-start accounting references, without changing their old-context retention states.

## Execution boundary and artifacts

Output reports/target_risk_acquisition_v204; runtime reports/v204_runtime_tmp. Capture11 source files (new core/runner/audit/tests2/spec/wrappers2 and reused V201/V202/V203 cores),4 input byte copies before acquisition. Existing V202/V203 audits must be valid/complete. Four core and four independent-audit synthetic tests cover utility/risk extrema, forecasts without evidence mutation, fixed-field updates, adaptive stopping/paired prefixes and changed artifacts. Execute once focused checks, one main, one independent audit; repeat only failed checks after repair. Compare source/input bytes once, no hashes.

Retain compressed acquisition histories, frozen models/decisions, true scores, retention, summaries, per-arm sampling/update/forecast/planning costs, source cost accounting and code. Independent audit reconstructs only consumed sample prefixes, real updates, forecasts, stops and whole-policy R/F/S. No remote pulls, CSV or checkpoints. Acquisition is controlled generative access; its samples are not subject to the execution policy's5% risk bound. Graph discovery, autonomous safe exploration and general strategic learning remain open; old negative results and U006 unstarted stay.
