# V246: common inheritance does not rescue the single-goal allocation rule

**FAIL: 4/5 frozen conditions pass; independent audit valid=true, zero failures.** From the same paid A/B history, RETURN_DIRECTED and ONE_WAY certify and jointly complete exactly the same 48/72 return targets, below the required 54/72. The rule is not adopted.

| Arm | Return query /72 | Joint completion /72 | New observations | Full charged observations |
| --- | ---: | ---: | ---: | ---: |
| ONE_WAY | 48 | 48 | 8,912 | 46,672 |
| RETURN_DIRECTED | 48 | 48 | 8,912 | 46,672 |

The [frozen protocol](../specs/COMMON_INHERITANCE_RETURN_V246.md) replays only V245 ONE_WAY's paid source and native A/B batches, then forks independent pools and cold caches. Both arms pay the full 37,760-observation prefix and use fresh paired return streams, unchanged budgets, certificates and stopping. All 144 decisions were frozen before truth scoring. No source observations were redrawn; the new experiment physically acquired 17,824 observations.

The [retained diagnosis](v246_runtime_tmp/return_allocation_diagnosis.json) finds **zero gains, zero losses and identical cost for every paired target**. All 24 failures are query-only and retain goal SHORT→DETOUR_RETRY. The new branch is active on all 557 acquired batches with no fallback. SHORT/DETOUR/RETRY observations change from **3,984/4,416/512 to 6,096/2,592/224**. RETRY scores positively on every active choice but wins only 14. Other unresolved comparisons move in opposite directions: goal SHORT→DETOUR_RETURN rises from 17 to 19, while risk DETOUR_RETURN→SHORT falls from 19 to 17. Changing allocation toward one retained bad kernel does not improve the full query AND on this history.

Next replace the single-candidate objective with the joint evidence needs of **all unresolved goal/risk comparisons**. Predict the worst certificate deficit after a candidate batch using the existing retained cell/dual and convex proof parameters, keep the original certifier and stopping decision, and charge prediction CPU. Qualify this objective before another complete lifecycle experiment. This phase closes further tuning of the V245 score; general strategic learning and the value of evidence under later queries remain unresolved.

Validation: **18 targeted tests passed**; one producer run completed in 331.48 seconds. One independent audit checked 1,258 plans, 5,128 unique proof profiles, 40,987 global leaves and 1,164 execution projections in 142.31 seconds, with zero binary tolerance and empty audit stderr. All six certificate/execution error counts are zero. Seventy-five source files were retained before dispatch. [Summary](common_inheritance_return_v246/summary.json), [independent analysis](common_inheritance_return_v246/analysis.json), [execution metadata](v246_runtime_tmp/verification_summary.json).

Limitations: this is one fresh suffix on three selected, shared historical prefixes, not an independent complete-lifecycle replication or a new REBUILD comparison. Later target starting evidence differs in 21/72 pairs because earlier allocations diverge. Confidence guarantees remain unconditional over each full process, not conditional on selecting this prefix. The trace does not isolate RETRY sampling as the sole cause. Model CPU is 1,116.21 versus 1,096.43 seconds; this single run establishes no stable speed benefit. Producer stderr retains 591 bytes of SLSQP clipping warnings. The original scientific Gate and U006's unstarted status remain unchanged.
