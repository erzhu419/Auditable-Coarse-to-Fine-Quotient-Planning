# V203 — fixed-evidence uncertainty and condition-bias-aware risk planning

V202 supports conditional learning but its final REVISED plug-in plans violate the true F<=1/20 budget in70/144 cases. V203 changes only constraint planning. No acquisition, fit, condition selection, new context, task change or parameter search. Use V202's final cumulative observations and frozen final models.

## Inputs and information boundary

Read and retain exactly V202 cases.json, batches.json and snapshots.json. Use FINAL_REUSE models/predictions, with NEW_WEATHER256 predictions for its four contexts. All twelve contexts and twelve lifecycles are fixed. Raw cumulative counts come from all four acquisition batches, indexed by complete context and operator. Predictions and model fields are reused, not recomputed by fitting. Existing V202 independent audit validity is a prerequisite; do not regenerate or resample its streams.

The nine-state graph, operator alphabets, costs and complete-policy grammar remain supplied priors. True laws, true pure-policy vectors and the hard-risk oracle may be read only after all144 context/lifecycle decisions across all arms are saved. They never set intervals, weights, objectives or thresholds.

## Simultaneous probability envelopes

For each independent lifecycle, construct intervals for12 contexts times7 categorical marginals. Confidence failure budget alpha=.05 for this entire fixed final family; beta=log(2*84/.05). At marginal empirical frequency x=k/n, retain p satisfying n*kl(x,p)<=beta, with kl(x,p)=x log(x/p)+(1-x)log((1-x)/(1-p)), continuous boundary conventions. Use64 bisections per nontrivial endpoint; round outside to a dyadic grid of2**40. No samples means[0,1]. Intersect each operator's category box with its probability simplex.

Binomial tail bounds and a union bound give at least95% simultaneous coverage within each lifecycle under the controlled independent categorical sampling model. This is not a95% simultaneous statement across all twelve lifecycles. No prior pseudo-counts enter these envelopes. A selected shared leaf does not establish equality of its members; unseen complete contexts stay unknown even if their leaf has observations.

## Whole-policy robust constraint

At H4, denote SHORT failure s, DETOUR failure f and recovery r, RETRY failure q. Pure complete risks are WAIT0, SHORT s, DETOUR_RETURN f, DETOUR_RETRY f+r*q.

Let s+=min(UshortLost,1-LshortDelivery), q+=min(UretryLost,1-LretryDelivery), f+=min(UdetLost,1-LdetDelivery-LdetRecovery), r*=min(UdetRecovery,1-LdetDelivery-f+). Then any nonnegative complete-policy mixture has exact worst-envelope risk:

wShort*s+ + wReturn*f+ + wRetry*(f+ + r* * q+).

The same DETOUR extremum maximizes every mixture: the coefficient on f is wReturn+wRetry, at least wRetry*q+, the coefficient on r. This equality is specific to the supplied route grammar. Optimize the frozen point-estimate goal utility R+4S by enumerating feasible pure vertices and all two-policy crossings of delta=1/20. Use exact Fraction arithmetic after interval construction. Break objective ties by lexicographic serialized mixture, matching V201. Persist the mixture's original predicted joint R/F/S separately from the robust risk bound; never splice a bound into an achievable joint vector.

## Frozen arms

1. PLUGIN: reuse V202 REVISED's final hard-plan mixture unchanged.
2. REVISED_ROBUST: complete-context envelopes above, fixed REVISED point objective.
3. FULL_ROBUST: identical complete-context envelopes, fixed FULL_CONTEXT point objective.
4. POOLED_ABLATION: fixed REVISED objective, intervals from counts pooled by its selected operator fields. Same beta for a descriptive ablation; data-selected groups and unequal member laws do not have the complete-context coverage claim. An unobserved projected group has full simplex. This arm cannot supply a member-level safety certificate.

All decisions freeze before oracle evaluation. Score exact true joint R/F/S and whole-policy goal utility, true violation count/max excess, WAIT mass, and envelope coverage. Report known complete contexts (eight with samples) separately from unknown combinations (four with none); the twelve cases within a fitted lifecycle are not independent replicas. The safe planner may mix WAIT, but zero-action feasibility alone cannot support usefulness.

## Frozen scientific decision

Two conditions determine RISK_PLANNING_SUPPORTED; otherwise RISK_PLANNING_NOT_SUPPORTED.

1. RISK: every final REVISED_ROBUST plan has robust bound<=1/20 and exact true failure probability<=1/20.
2. SUPPORTED_UTILITY: across the eight observed contexts, REVISED_ROBUST mean true goal utility exceeds half the mean true hard-risk oracle utility, with the paired lifecycle95% bootstrap lower bound on that difference>0.

Bootstrap5000 shared12-index lifecycle resamples, random.Random(203900), percentile indices124 and4874. Also bootstrap REVISED_ROBUST minus FULL_ROBUST utility in observed and unobserved groups, and unobserved REVISED_ROBUST minus half-oracle utility. These last contrasts are diagnostics, not criteria for the two conditions. Do not use their values to add samples, change alpha or adopt another arm.

Unknown-context information boundary is reported independently of the decision: all three non-WAIT pure policies have worst risk1, so action mass<=.05 and true R+4S<=.2 because costs are nonnegative and success probability<=1. Safe planning on this evidence cannot establish high-utility unobserved reuse without additional structural assumptions or observations. Do not hide this limitation in an overall mean or call confidence in a pooled estimate evidence of equality.

## Execution and retained evidence

Output reports/robust_route_planning_v203; runtime reports/v203_runtime_tmp. Freeze source bytes and the three input files before planning. Four core and four independent-analysis synthetic tests detect rare-event/unknown endpoints, alias pooling, common-kernel mixture risk and changed decisions/results. Run focused tests once, one main and one independent audit; repeat only failed checks after their repair. Compare retained source/input bytes once after the run. No hashes.

Retain intervals and counts, frozen plan decisions, all arm results, oracle reference, summaries, execution work and source. Charge input bytes, count accumulation, interval arithmetic, exact optimization, original-prediction mixture arithmetic, true evaluation, bootstrap and independent reconstruction. New samples/fits are zero. Old negative Gates and U006 unstarted stay.
