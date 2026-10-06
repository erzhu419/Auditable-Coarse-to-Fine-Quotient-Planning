# V261: native point learning from predeclared policy paths

Frozen stage **FAIL, 7/8 conditions; method not adopted**. Partial-point learning meets late-B 32/36 and return 72/72, but has no completion or fee gain against the matched required-row control. Independent audit passes. Original scientific Gate FAIL; U006 unstarted.

Only the first arm changes its query point estimator. Native SOURCE/SHARED units update a policy when their pre-outcome declaration covers its executable path; every declared D/R unit contributes to RETRY, including non-RECOVERY branches. Both first arms retain the same required-row acquisition rule; the third uses complete units. All three retain continuous execution confidence, fixed comparison thresholds, caps and execution rules.

| Metric | Partial point | Required rows, complete point | Complete continuous reuse |
|---|---:|---:|---:|
| Joint completion /216 | 200 | 200 | 197 |
| Query certificates /216 | 208 | 208 | 205 |
| Execution certificates /216 | 192 | 192 | 192 |
| Goal-impossible certificates | 16 | 16 | 16 |
| Full paid observations | 44,703 | 44,703 | 44,969 |
| Late-B queries /36 | 32 | 32 | 31 |
| Return queries /72 | 72 | 72 | 72 |
| Shared observations | 30,673 | 30,673 | 30,929 |
| Member observations | 16 | 16 | 32 |
| Execution observations | 190 | 190 | 184 |
| Model CPU seconds | 162.11 | 163.62 | 164.77 |

The first two arms have identical physical observations, unit declarations, acquisition checks, stops and actual executions. Each produces 5,666 partial units. Partial point changes 80/216 terminal vector sets, 74/1,560 preview candidate sets and 8 terminal risk candidates. Those 8 life2/B/type2 candidates change RETRY→RETURN: true regret falls 0.0095/0.0285→0, but both choices already meet the 0.05 tolerance. The estimator learns; its changed choices produce 0 additional certificates or completed targets.

Against complete reuse, both required-row arms gain 3 paired query/joint targets with 0 losses and save 266 observations: shared 256 + member 16 − execution 6. All net shared saving occurs in A; B shared acquisition remains 16,081 in all arms. These gains cannot be attributed to the new point estimator, and this fresh run does not overturn V260's negative result.

Remaining bottlenecks: 8 life2/B/type2 query-only targets are blocked solely by risk RETURN versus RETRY. Their 3,636 actual D/R units give log-e 2.425/4.479 below log(4320)=8.371. Shared acquisition spends 3,459 D calls to obtain 680 conditional R observations. Another 8 life1/B/type1 targets have ready queries but unresolved execution: true risk-constrained optimum 1.8189–1.8389 is below goal 2, while retained goal upper 2.2527–2.2759 cannot prove impossibility. After query readiness this type still spends 5,909 shared observations (S 2,093 / D 2,066 / R 1,750); both difficult B phases exhaust their acquisition budget.

**Next:** address the observation/evidence bottleneck. Predeclare row-CS as the sole query proof, sharing its uniform confidence event with execution; keep old comparison evidence diagnostic rather than combining the two without confidence allocation. RETURN/RETRY risk difference factors exactly as d_REC·(8r_DEL−4−retry_cost). The existing controlled generative interface permits a requested operator-state reset and single transition, charging each physical reset/draw. Compare direct acquisition of rows needed by unresolved certificates against full-unit acquisition using the same new proof. A standalone R draw is row evidence, never a fabricated D/R unit or a completed policy path. This new proof and sampling design remain untested.

Fifty-eight focused tests pass after one retained fixture repair (first attempt 57 pass / 1 fail). Science and independent audit each run once, exit 0 / stderr 0, wall 101.91/319.01s. Audit valid with 0 failures across 648 targets, 4,692 previews, 652 intermediate execution decisions, 11,332 partial units across both required arms and 86 captured sources (483,677 checks). All numerical/certificate/risk-limit errors are 0; stochastic realized failures are 5 per arm.

[Verification](v261_runtime_tmp/verification_summary.json), [audit](partial_path_point_v261/analysis.json), [point effects](v261_runtime_tmp/point_effect_posthoc.json), [acquisition constraints](v261_runtime_tmp/acquisition_constraint_posthoc.json).

Limits: one fresh paired run; retained-history diagnosis is descriptive and supplies no new performance evidence. Known type/change/equality interfaces and H2 remain; confidence scope is per life/fixed arm. Prior frozen results remain immutable.
