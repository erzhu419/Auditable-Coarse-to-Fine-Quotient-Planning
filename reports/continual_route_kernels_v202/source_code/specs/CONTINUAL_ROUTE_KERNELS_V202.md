# V202 — fixed-learner conditional-kernel revision and reuse

V201 qualified a small route task. V202 tests whether a fixed learner can infer conditional sharing from controlled experience, revise it when new weather is observed, and plan in unobserved combinations. The V201 task, costs, horizons, three queries and hard-risk budget are unchanged.

## Learning object and information boundary

The nine-state graph, successor alphabets, terminal semantics, numeric costs and composition/planning interfaces are supplied priors. They are not learned achievements. Unknown quantities are the categorical successor laws of SHORT_PASS, DETOUR_PASS and RECOVERY_RETRY. Alphabets respectively DELIVERY/LOST, DELIVERY/LOST/RECOVERY, DELIVERY/LOST.

The learner receives observed context fields weather, operating, retry_cost and one sampled successor per controlled operator request. It never receives true probabilities, full support, oracle values/actions or future observations. Cost fields are directly supplied to the planner; new-cost probes measure probability-kernel reuse through this interface, not discovery of a new reward mapping.

Controlled acquisition resets directly to the requested operator state. This includes RETRY observations, even when ordinary policy execution rarely visits RECOVERY. Charge every reset and single-step draw. This is a controlled generative experience stream, not autonomous whole-game exploration.

## One frozen learner and controls

For each operator, consider all eight subsets of operating/retry_cost/weather, canonical field order lexicographic. For each projected context group, aggregate categorical counts from the available prefix. Dirichlet alpha=1/2. Log evidence is the sum over groups of:

lgamma(K*alpha)-lgamma(N+K*alpha)+sum_category(lgamma(count+alpha)-lgamma(alpha)).

Do not include a multinomial count coefficient; grouping must not change which observed sequence is scored. Uniform prior over the eight models. Add groups in sorted projected-key order and categories in the fixed alphabet order. Replace a score winner only on gain>1e-9; within1e-9 prefer fewer fields, then lexicographic field tuple. Posterior mean probability is exact Fraction(2*count+1,2*N+K). An unseen projected group uses the uniform Dirichlet prior, with no true-probability/global fallback.

REVISED reselects conditions using all available prefix counts at each acquisition checkpoint. FULL_CONTEXT uses all three fields and cumulative counts. FIXED_WEATHER uses the manually supplied weather partition and cumulative counts; it is a strong reference for correct factorization. FROZEN keeps the SOURCE-selected models/counts permanently. RESET reselects using only the latest acquisition batch, and has no data before the first batch of a new phase. Evaluation-only retention does not reset it.

All five controls receive the same sampled prefix. Their statistical/selection/planning work is charged separately. Persist counts, all tested condition scores, selected fields and posterior rows. A change in selected fields must follow data, not developer modification.

## Chronology and finite budget

Twelve independent learner lifecycles use random.Random(202000+i), i=0..11. Only the environment owns true V201 probabilities. Within every batch order contexts by the schedule below, operators SHORT_PASS/DETOUR_PASS/RECOVERY_RETRY, then individual draws. Every draw consumes exactly one random() and maps it through Fraction cumulative probabilities in the stated alphabet order.

1. SOURCE: normal/low, retry17/20 then19/20, 256 draws per context/operator. 1536 observations per lifecycle. Fit all initial controls; freeze FROZEN here. Evaluate these two old contexts.
2. NEW_COST_ZERO: predict normal/high, both retry costs, before any high-cost sampling. RESET is empty; other models carry SOURCE knowledge.
3. NEW_COST128: acquire128 per normal/high context/operator, 768 observations. Update; evaluate those two contexts.
4. NEW_WEATHER_ZERO: predict wet/high then blocked/high, both retry costs, before their acquisition. RESET is empty; other controls carry prior knowledge.
5. NEW_WEATHER64: acquire64 per new-weather context/operator, 768 observations. Update and evaluate those four contexts.
6. NEW_WEATHER256: acquire another192 per same context/operator, 2304 observations. Update and evaluate those four contexts.
7. FINAL_REUSE: no acquisition or model update. Evaluate the remaining eight contexts: old normal/low two; normal/high two; wholly unacquired wet/low and blocked/low four. Combine these with NEW_WEATHER256's four scores to obtain final all12 metrics.

Total5376 controlled draws/resets per lifecycle,64512 overall. Store per-batch sufficient counts, seed and draw counts rather than large raw tapes. The independent audit regenerates each stream once and compares these counts. Acquisition order/budget do not depend on policy or oracle feedback.

Freeze model snapshots and predicted planning decisions before oracle scoring at every probe. Oracle diagnostics never feed the learner, sample schedule or condition selection.

## Own-policy evaluation and uncertainty

Compile the estimated conditional laws into the supplied graph and plan H4 with the three unchanged queries. Save selected root and recovery actions, predicted joint R/F/S, actual joint R/F/S under that complete continuation, oracle regret, and each operator's probability TV. The four pure policy classes suffice for this graph; keep one attainable joint vector per policy.

Also run the unchanged hard-budget optimizer on the estimated pure vectors. Save its whole-policy mixture, predicted risk/goal utility, actual joint vector, actual violation F>1/20 and positive violation magnitude. This plug-in plan is diagnostic: estimated feasibility is not a safety certificate. Hard-risk violations are reported separately and do not enter the conditional-learning decision below.

Use each independently trained lifecycle as the statistical unit. Compute paired percentile-bootstrap mean intervals with5000 resamples and random.Random(202900), one common12-index resample for all four contrasts; bounds are sorted samples at floor((5000−1)*0.025) and floor((5000−1)*0.975). Count bootstrap operations separately from environment draws. Cases sharing a fitted learner are not independent replications.

## Frozen development decision

All four conditions are required for CONDITIONAL_LEARNING_SUPPORTED; otherwise CONDITIONAL_LEARNING_NOT_SUPPORTED. Do not alter task, sample budgets, learner, thresholds or seeds after outcomes.

1. ZERO_SAMPLE_REUSE: at NEW_COST_ZERO, mean FULL_CONTEXT TV minus REVISED TV exceeds0.05 and its paired95% bootstrap lower bound is>0.
2. CONDITION_REVISION: at final unacquired wet/blocked low-cost contexts, mean FROZEN TV minus REVISED TV exceeds0.02 with paired95% lower bound>0; at least10/12 final REVISED SHORT_PASS models select exactly(weather).
3. POLICY_TRANSFER: at those four final unacquired contexts, mean REVISED utility exceeds FULL_CONTEXT by>0.05 and FROZEN by>0.01, each with paired95% lower bound>0. Average the three queries equally, then contexts, then lifecycles.
4. QUALITY_RETENTION: final all12 REVISED mean kernel TV<=0.05, own-policy mean oracle regret<=0.05, each mean absolute predicted R/F/S error<=0.05; mean regret exceeds FIXED_WEATHER by at most0.01; on the two old normal/low contexts mean regret worsens from SOURCE to FINAL_REUSE by at most0.01.

Report every control, checkpoint, failure and hard-risk violation. Passing supports conditional probability learning/revision/reuse within this given task grammar. It does not prove general strategy discovery, autonomous experience acquisition, unknown-mechanism graph learning, safety assurance, total-cost benefit or old2048 superiority.

## Execution

Output reports/continual_route_kernels_v202; runtime reports/v202_runtime_tmp. Use distinct test_ and stage_ log names. Retain this specification, new core/runner/auditor/tests/wrappers and the reused V201 planner as source bytes before acquisition. No hashes. Eight focused synthetic tests cover prefix isolation, condition selection, posterior/unseen groups, graph reward mapping and independent verification. Run one main and one independent audit; repeat only a failed check after its repair.

Retain all sufficient-count batches, model snapshots, compact own-policy/constraint results, bootstrap summaries, costs and executed source. Count controlled samples/resets, count/evidence updates, graph compilation, planning, replay, mixture optimization and independent reconstruction. No CSV, checkpoint or remote download. Old negative results, U005 FAIL and U006 unstarted stay.
