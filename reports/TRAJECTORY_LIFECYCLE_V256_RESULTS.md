# V256: direct-trajectory A/B/A with actual execution

The frozen stage **passes**, including independent audit. Both arms retain
their own A/B histories; only legal cross-context evidence reuse differs.
All432 target plans and actual executions freeze before truth scoring.

| Complete lifecycle / actual fee | TRAJECTORY_REBUILD | TRAJECTORY_REUSE |
|---|---:|---:|
| Queries certified | 197/216 | 205/216 |
| Execution resolved, including certified impossibility | 192/216 | 200/216 |
| Joint completion | 173/216 | 189/216 |
| Late-B queries | 28/36 | 31/36 |
| Return-A queries | 72/72 | 72/72 |
| Source observations | 13,824 | 13,824 |
| Shared observations | 29,793 | 28,056 |
| Member observations | 3,440 | 4,832 |
| Actual execution observations | 170 | 186 |
| Full paid observations | 47,227 | 46,898 |
| Expected executed goal utility, mean | 2.5533 | 2.8608 |
| Realized deliveries / failures | 146 / 3 | 160 / 3 |
| Summed model process CPU | 111.22 s | 128.75 s |

Sixteen paired joint gains, zero losses or false claims. All life caps hold.
Saving1,737 shared observations is offset by1,392 member and16 execution
observations: net saving329 (**0.70%**), with15.76% higher model CPU.
All27 reuse fallbacks occur in B:16 execution-only and11 query-only gaps.

Posthoc diagnosis, independently recomputed, finds all16 execution-only targets
truly infeasible under risk1/20 and goal2: true optimum1.162–1.176 for life0/type2
and1.819–1.839 for life1/type1. Their retained upper bounds still exceed2;
this diagnosis is not an acquired impossibility certificate. Next compare a
coupled risk-constrained impossibility upper bound on these same paid snapshots,
then address the11 changed-R-dependent query gaps. Freeze V256 as the baseline.

Twenty producer and nine audit tests pass. Initial producer test collection
failed on a test syntax error; the repair and both attempts are retained.
Science/audit each run once: exit0, wall55.84/206.10s, stderr0; audit valid,
zero failures across2,940 auxiliary decisions,8,380 direct profiles and949
execution plans. Physical total94,125 observations, including27,648 source.
See [verification](v256_runtime_tmp/verification_summary.json),
[audit](trajectory_lifecycle_v256/analysis.json) and
[posthoc diagnosis](v256_runtime_tmp/execution_gap_posthoc.json).

Limits: three known types, declared changed operator/equality map and fixed
H2 policies; descriptive paired results, no automatic-interface or overall
computational-saving claim. Original scientific Gate FAIL; U006 unstarted.
