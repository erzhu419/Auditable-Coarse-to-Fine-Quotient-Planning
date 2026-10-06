# V253: compatible paid return evidence

The fixed TWO_WAY view adds **no return-query or combined-readiness gains** at
V251's original terminal times. All 144 endpoints were frozen before planning.

| V251 acquisition arm | Query-ready ONE / TWO | Execution-certified ONE / TWO | Risk-query certificates ONE / TWO | Retained observations |
|---|---:|---:|---:|---:|
| UNIFORM_SHARED | 48 / 48 | 72 / 72 | 50 / 48 | 48,384 |
| QUERY_SHARED | 48 / 48 | 72 / 72 | 56 / 56 | 48,112 |

All point-query choices remain unchanged. SHORT-to-RETRY still blocks all 24
failed returns per arm. Secondary goal blockers fall from 17 to 9 and from 5 to 3,
without completing a query. UNIFORM loses two risk-query certificates.

For QUERY_SHARED life1's hard type, R observations rise from 528 to 2176. Two cost
profiles improve log-evidence from -3.794 to -2.341 and -1.902 to -0.366,
still below 6.867. Thus compatible evidence improves a bound without resolving
the decisive comparison.

Sixteen focused tests pass once. Independent audit is valid with zero failures:
144 new plans, 444 profiles, 4,804 global leaves and 137,230 checks. Producer/audit
exit 0; wall times 13.66/5.91 s. New planning uses 60.96 summed CPU seconds.
See [verification](v253_runtime_tmp/verification_summary.json) and
[independent analysis](paid_return_views_v253/analysis.json).

Next end quota and TWO_WAY refinement. Freeze a new exploratory comparison of
row-based inference against directly observed SHORT/DETOUR_RETRY executable
continuations, learning their joint success, loss, conditional cost and value
difference. Charge every primitive step; execute RETRY only after RECOVERY.
Match the full interaction budget and retain source costs, targets, regret
tolerance and confidence scope before drawing new outcomes.

Limits: the retained unknown proofs do not establish loose dual bounds or bad
kernels in the new regions. Snapshot replanning changes neither historical
execution nor adaptive stopping; no new observations or cost savings occur.
V251 remains 10/11 with actual return 48/72. The original scientific Gate remains
FAIL and U006 remains unstarted. The proposed trajectory learner is untested.
