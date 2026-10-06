# V275 online support continual lifecycle — results

## Status

The frozen V275 execution-only diagnostic completed for four seed lifecycles
with zero stderr. It uses 12 episodes × 8 START opportunities in each of
A, B, and A_prime (96 opportunities per phase and 288 per arm/lifecycle).
Only reached operators generated outcomes. The raw receipt is
[summary_final_v3.json](publication/v327_snapshot/online_support_continual_v275/summary_final_v3.json.gz);
the terminal stderr is
[stderr_final_v3.log](/home/erzhu419/mine_code/Auditable Coarse-to-Fine Quotient Planning/workspaces/acfqp-controlled-predictive-quotient-exploration/reports/online_support_continual_v275/stderr_final_v3.log).

## Main result

Mean cumulative exact oracle regret per seed lifecycle was:

| arm | A | B (primary) | A_prime |
|---|---:|---:|---:|
| PHASE_RESET_ONLINE | 24.421750 | 28.797300 | 26.720125 |
| FROZEN_FACTOR_ONLINE | 8.642000 | 10.073200 | 8.642000 |
| CONTINUAL_FACTOR_ONLINE | 8.642000 | 10.073200 | 8.642000 |
| LEGACY_COERCE_ONLINE | 8.642000 | 10.073200 | 8.642000 |

The continual, frozen, and legacy factor arms are identical on all three
phase totals and their paired per-opportunity curves. Thus this cohort shows no
measured benefit from support admission or continual updating. The reset arm
is much worse because it has no amortized source model; that is a control
contrast, not evidence that online updating solved the bottleneck.

## Exposure and accounting

Across the four lifecycles, "DELAYED" was reached only 3 times by the phase
reset arm and 5 times by each source arm, all in B. No A_prime trial generated
a new successor. For the factor arms this is 5 of 269 B-phase executed events
(1.86%), because a retry is sampled only after a reached recovery branch. This
is a real exposure limitation: no recovery probe was injected after seeing the result. The source arms executed on average 69.75,
67.25, and 70.25 events per seed in A, B, and A_prime respectively; these
counts are separate from their one-time 720-fit/240-audit source corpus.

## V276 retained-data diagnosis

Low DELAYED exposure alone does not explain the result. Exact arithmetic shows
that preserving DELAYED changes the optimal action in only target_2_2/goal in B,
where RETURN beats RETRY by 0.0133. Across the four lifecycles, that cell accounts
for 0.4256 of the 40.2928 B regret; the other 39.8672 (98.94%) is wet-road ranking
error in source seed 275402.

That seed selects both context fields for SHORT_PASS, leaving every crossed
target with zero matching source rows and a 1/2 SHORT delivery estimate. It
executes zero SHORT_PASS observations over all 288 opportunities, so passive
updating cannot repair that estimate. It also keeps DETOUR_PASS globally pooled.
Rescoring the same committed A feedback with the same source criterion would
favor the road partition for DETOUR (-171.488 versus -175.548), but there is no
new SHORT evidence to rescore.

The main follow-up therefore tests online factor revision and bounded lawful
coverage within the existing opportunity budget. No new sampling was needed
for this diagnosis. V275 remains a finite synthetic null result; U005 remains
FAIL and U006 unstarted.
