# V245: query-directed acquisition fails the matched lifecycle test

The fresh 648-target experiment is **FAIL: 6/11 frozen conditions pass**, with independent audit **valid=true** and no failures. The single-goal bad-kernel KL allocation is not adopted. Relative to ONE_WAY, it gains no query or joint completion, loses three late-B targets, and spends 944 more observations (+2.02%).

| Arm | Late-B queries /36 | Return queries /72 | Joint completion /216 | Total charged observations |
| --- | ---: | ---: | ---: | ---: |
| ONE_WAY | 28 | 48 | 132 | 46,672 |
| QUERY_DIRECTED | 25 | 48 | 129 | 47,616 |
| REBUILD | 23 | 48 | 124 | 48,384 |

The [frozen protocol](../specs/QUERY_ALLOCATION_LIFECYCLE_V245.md) changes only acquisition when execution is resolved and goal SHORT→DETOUR_RETRY remains unproved. It reuses the current retained candidate, with no additional optimizer or certificate. Query proofs, execution, budgets, stopping and the strong REBUILD control remain fixed. All decisions precede truth scoring.

The [retained regression trace](v245_runtime_tmp/regression_diagnosis.json) identifies all three losses at life 2, B targets 42/43/53: goal **DETOUR_RETRY→SHORT** remains unproved, while risk and execution are resolved. Their target sampling rises from 16/0/320 to 384/384/384 without lifecycle-budget exhaustion. The new branch never runs in B. The first difference is A target 8, where identical evidence yields DETOUR for ONE_WAY and SHORT for QUERY_DIRECTED; that target's S/D allocation changes from 176/208 to 256/128. B subsequently inherits different A evidence and applies the same original acquisition rule to different histories.

The [acquisition ledger](v245_runtime_tmp/acquisition_ledger.json) records 569 active choices in A and 570 on return. Return RETRY sampling falls from 544 to 368 observations; all 24 original paired return failures still include goal SHORT→RETRY. The rule therefore fails both its return objective and preservation of later query quality. RETRY has positive KL at every active return choice; this is not a zero-score implementation bug. Model CPU also increases from 4,804.95 to 4,990.37 seconds.

Next fix a common paid inheritance prefix to isolate return acquisition from upstream A changes, then test acquisition against the joint needs of unresolved comparisons. The longer-term objective must account for the value of retained mechanism evidence under later queries and policy reversals. Another weight adjustment to this single-candidate rule has no support from this cohort.

Validation: 22 targeted tests passed. One producer run completed in 2,761.21 seconds; one independent audit checked all 6,973 plans and 21,450 proof profiles in 914.45 seconds, with zero binary projection tolerance and empty audit stderr. Seventy-three source files were captured before dispatch. [Summary](query_allocation_lifecycle_v245/summary.json), [independent analysis](query_allocation_lifecycle_v245/analysis.json), [execution metadata](v245_runtime_tmp/verification_summary.json).

Limitations: these are three fixed layouts with known type/change interfaces and controlled observations. The trace establishes changed inheritance as the path of the B regression but does not isolate an individual row's causal contribution or rule out other acquisition methods. Producer stderr retains 801 bytes of the original SLSQP bound-clipping warnings. This phase changes neither the original scientific Gate nor U006's unstarted status.
