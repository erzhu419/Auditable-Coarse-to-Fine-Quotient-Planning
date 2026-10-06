# V249: fixed S/D probe timing fails

**FAIL: 9/11 frozen conditions; independent audit valid=true, zero failures.** Earlier acquisition of the fixed probe quota is not adopted. Return and late-B quality remain below 54/72 and 27/36.

| Arm | Late-B queries /36 | Return queries /72 | Joint completion /216 | Full charged observations | Model CPU seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| BEFORE_SHARED | 23 | 48 | 132 | 47,792 | 1,955.31 |
| DEFERRED_SHARED | 23 | 48 | 132 | 47,792 | 1,962.77 |
| REBUILD | 23 | 48 | 128 | 48,256 | 1,997.71 |

The [protocol](../specs/SHARED_PROBE_TIMING_V249.md) runs 648 fresh decisions. Treatments each pay 768 probes/life under existing native A events. Decisions precede scoring; REBUILD retains its own histories and full budget.

The [diagnosis](v249_runtime_tmp/timing_diagnosis.json) confirms identical A/B histories and paired probes. **All 72 return outcomes and target costs tie**: first-type queries 6/9, later 42/63. Nine targets change allocation, but all 24 failed returns retain SHORT→DETOUR_RETRY blockers; 20 hit member caps and four exhaust ordinary budgets. Net saving versus REBUILD is 464 observations: B/return savings 1,856+912 minus 2,304 probes. This does not identify a timing benefit.

Next use exploratory offline search for budget-feasible acquisition schedules with unchanged member caps and certifiers. Selected schedules require fresh confirmation; finite search failure cannot prove impossibility.

Validation: **17 tests passed once**; audit (378.94 s, exit0) checked 6,758 plans, 29,181 profiles and 288 probe batches. Seventy-one sources were captured; 116,192 observations were made. [Summary](shared_probe_timing_v249/summary.json), [audit](shared_probe_timing_v249/analysis.json), [verification](v249_runtime_tmp/verification_summary.json).

Limitations: three fixed known-structure layouts; quota insufficiency/general learning remain unproved. The producer tool reported exit143 despite all 648 rows, complete phase markers and an identical final printed/saved summary; shutdown cause remains unresolved. Producer stderr retains 2,613 bytes of clipping warnings; audit stderr is empty. The original Gate and U006 remain unchanged.
