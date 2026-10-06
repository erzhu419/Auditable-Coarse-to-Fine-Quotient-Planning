# V259: continuous compatible row confidence

Frozen stage **FAIL, 7/8 conditions**. Late-B queries21/36 miss27/36; the other seven conditions and independent audit pass. The original scientific Gate remains FAIL and U006 unstarted.

Only the execution row confidence process changes. Legally identical A/B rows continue one canonical Jeffreys process; changed rows stay native. Query rules, sampler, goal-dual search, seeds paired across arms, caps and all physical fees are frozen.

| Metric | Continuous reuse | Separate reuse | Own-history rebuild |
|---|---:|---:|---:|
| Joint completion /216 | 170 | 162 | 160 |
| Query certificates /216 | 178 | 178 | 176 |
| Execution certificates /216 | 192 | 192 | 192 |
| Goal-impossible certificates | 16 | 8 | 0 |
| Execution unresolved | 8 | 16 | 24 |
| Full paid observations | 48,237 | 48,251 | 48,246 |
| Late-B queries /36 | 21 | 21 | 20 |
| Return queries /72 | 72 | 72 | 72 |
| Source observations | 13,824 | 13,824 | 13,824 |
| Shared observations | 34,216 | 34,216 | 34,220 |
| Member observations | 32 | 48 | 48 |
| Execution observations | 165 | 163 | 154 |
| Model CPU seconds | 195.33 | 198.59 | 184.52 |

Continuous versus separate reuse gains8 joint decisions with0 paired losses; versus rebuilding gains10 with0 losses. The eight new decisions are **impossibility certificates**, not eight additional successful executions. Cost savings are only14 and9 observations respectively; continuous query decisions equal separate reuse.

At the retained common paid prefix life0/B/type2/check30, all four cost cases have exactly equal evidence counts in both reuse arms. Continuous upper1.94348–1.96537 is below2; its box upper2.00071–2.02139 and separate upper2.27358–2.29852 are not. S/R goal binary uppers also match exactly: the full compatible D region supplies the demonstrated information gain. No posthoc sampling or bound recomputation is used.

All nine B acquisition phases exhaust budget. Continuous acquisition frees995 type-allocation draws in life0, then spends them on unresolved queries; shared fees remain34,216. A queries consume25,376 of these shared draws. In life1, A uses12,320, leaving only32 for B; the final four cost cases all share one risk comparison, DETOUR_RETURN versus SHORT, requiring S/D. Its retained6173 rounds give e4309.323<4320. This blocks the phase despite the selected policy having zero scored regret.

**Next:** preserve continuous evidence and implement acquisition units for each unresolved query comparison, e.g. S/D when R is unnecessary, plus execution-specific rows where needed. Keep confidence thresholds, point-choice rules and total caps fixed in the first causal comparison. Merely adding goal-directed acquisition misses the main A risk-query blocker. Isolate any subsequent cross-phase budget policy change in its own fresh control.

Thirty focused tests pass on the first attempt. Science and audit run once: exit0/stderr0, wall134.25/431.81s. Audit valid with0 failures:648 targets,5,256 full previews,656 intermediate execution decisions and429,208 checks. All numerical/certificate/risk-limit errors are0. Each arm realizes2 stochastic failures, with0 risk-limit violations.

[Verification](v259_runtime_tmp/verification_summary.json), [audit](continuous_row_cs_v259/analysis.json), [same-evidence diagnosis](v259_runtime_tmp/continuous_row_diagnosis.json), [acquisition diagnosis](v259_runtime_tmp/shared_sampling_cost_posthoc.json).

Limits: one fresh paired run; stage failure is preserved without retuning. Known type/change/equality interfaces and H2 remain. Confidence allocation is per life/fixed arm, not a simultaneous whole-cohort guarantee. V256 passed and V257/V258 negative artifacts remain immutable.
