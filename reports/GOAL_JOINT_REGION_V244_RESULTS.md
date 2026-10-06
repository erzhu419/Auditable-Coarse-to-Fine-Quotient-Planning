# V244: complete-region diagnosis of return-query failures

Independent audit is **valid=true**, with 4,723 checks and no failures. Of the 24 ONE_WAY A_RETURN goal SHORT-versus-DETOUR_RETRY unknowns retained from V243, **19 contain an exact strictly bad kernel inside every compatible query region and original execution event**. At these fixed endpoints, proof improvements within the same regions can certify at most **72 − 19 = 53/72** return queries, below the frozen requirement of **54/72**. The main next step is query-directed acquisition allocation.

| Lifecycle | Full-region bad witness | Paid constraints reject candidate | Unknown |
| --- | ---: | ---: | ---: |
| 0 | 3 | 3 | 2 |
| 1 | 8 | 0 | 0 |
| 2 | 8 | 0 | 0 |
| Total | 19 | 3 | 2 |

The [frozen protocol](../specs/GOAL_JOINT_REGION_V244.md) recovers one candidate from each original certificate and repairs SHORT once, with exact goal gap 0.050001. Each candidate is checked against all eight V235 query families and all nine original full execution events, using only its chronological paid prefix. There are no new observations, optimizer calls or query certificates. Three candidates pass the canonical region but fail other paid constraints; two fail the canonical region. Excluding these particular points does not establish that the entire bad null is empty, so all five remain uncertified.

A separate [posthoc allocation cue](v244_runtime_tmp/retained_witness_information.json) compares empirical-to-witness KL per operator with actual acquisition. RETRY provides the largest per-sample separation for five of the 19 full-region witnesses, yet those five targets assigned only 128 of 1,920 paid observations to RETRY. Across all 19 targets, SHORT/DETOUR/RETRY received 3,312/3,568/416 observations. This motivates testing allocation that responds to query ambiguity rather than marginal interval width.

Next freeze a fresh matched lifecycle experiment that changes ONE_WAY's query acquisition allocation only, preserving certificates, total budgets, stopping and the strong REBUILD control. Evaluate return-query quality and total charged observations together. The new allocation is a hypothesis to implement and test; this phase establishes the obstruction and does not claim a performance gain.

Validation: 18 targeted tests passed (11 core, two runner, five independent-audit tests); the single producer and audit runs completed in 376.88 s and 347.42 s, both with empty stderr. Twenty-one source files were retained before execution. Results: [summary](goal_joint_region_v244/summary.json), [24 records](goal_joint_region_v244/records.json), [independent analysis](goal_joint_region_v244/analysis.json), [execution metadata](v244_runtime_tmp/verification_summary.json).

Limitations: the 53/72 bound applies to ONE_WAY's current terminal prefixes, existing statistical regions and original certification times. It does not rule out different statistical evidence, additional observations or structural assumptions. The existing error allocation is at most 0.10 per lifecycle and arm, not a cohort-wide guarantee. The KL cue is descriptive and does not predict counterfactual savings or account for every possible bad kernel. V243 remains FAIL (9/11 conditions passed); the original scientific Gate is unchanged and U006 remains unstarted.
