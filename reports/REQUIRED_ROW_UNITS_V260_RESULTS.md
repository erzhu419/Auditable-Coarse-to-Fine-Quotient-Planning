# V260: required-row acquisition without partial point learning

Frozen stage **FAIL, 5/8 conditions; method not adopted**. Late-B queries25/36 miss27/36 and the continuous control28/36; joint completion176/216 loses8 versus that control184/216. Independent audit passes. Original scientific Gate FAIL; U006 unstarted.

SHARED alone changes to batch-predeclared required-row unions; unresolved execution still requests full units. Only ALL-predeclared units update the old complete-joint query point estimate. Sources, CS thresholds, caps, member/actual execution and goal-dual search stay fixed.

| Metric | Required rows | Complete continuous reuse | Own-history rebuild |
|---|---:|---:|---:|
| Joint completion /216 | 176 | 184 | 168 |
| Query certificates /216 | 192 | 200 | 184 |
| Execution certificates /216 | 192 | 192 | 192 |
| Goal-impossible certificates | 8 | 8 | 8 |
| Full paid observations | 48,249 | 48,257 | 48,252 |
| Late-B queries /36 | 25 | 28 | 19 |
| Return queries /72 | 72 | 72 | 72 |
| Shared observations | 34,201 | 34,201 | 34,201 |
| Member observations | 48 | 48 | 64 |
| Execution observations | 176 | 184 | 163 |
| Model CPU seconds | 191.33 | 189.82 | 166.81 |

All arms physically pay13,824 source observations. Required acquisition produces5,274 partial units:1,646 S/D and3,628 D/R. All A acquisition remains full and identical to continuous reuse (6,912/4,096/5,888 draws by life); all B phases exhaust budget. Shared acquisition saves0. Total fees fall8 versus continuous solely because eight fewer physical executions occur. The frozen full-fee condition is true, but it is not an acquisition-efficiency gain.

All8 paired query/joint losses are life0/B/type0, indexes34,36,38,39,40,47,49,50. Query point history stays at175 native complete units while755 D/R partial units arrive. Required keeps goal RETURN; continuous updates590 complete units and chooses RETRY. The blocked D/R comparison has4,672 valid units versus control4,332, so lack of comparison coverage does not explain this group. Required log-e remains negative; the control opposite direction reaches27.509/40.492 above log4320=8.371.

Legal native policy-path empirical means over the930 ALL+predeclared D/R units change the goal argmax to RETRY for8/8 loss targets. These are descriptive posthoc means, not new certificates. Another retained life1/B/type2 point stays at185 complete units and chooses risk RETURN with true regret43/100; the continuous control chooses SHORT with0 regret. The query evidence correctly refuses to certify the stale candidate.

**Next:** isolate partial-path point learning. Update each policy vector sum/count from units whose declaration covered that executable path before observation; use every D/R unit including non-RECOVERY branches, without joining rows or imputing outcomes. Keep empirical argmax/ties, fixed comparison streams/threshold4320, continuous row CS, acquisition rule, total caps and execution rules. Compare against both frozen-point required acquisition and full continuous reuse on fresh paired seeds. This tests whether learning from partial data fixes the demonstrated point/evidence mismatch; no qualification pass is yet claimed.

Thirty-eight focused tests pass first attempt. Science/audit each run once, exit0/stderr0, wall136.65/435.06s. Audit valid with0 failures across648 targets,5,184 previews,658 intermediate execution decisions and5,274 partial units (525,798 checks). All numerical/certificate/risk-limit errors are0; stochastic realized failures are2/2/1.

[Verification](v260_runtime_tmp/verification_summary.json), [audit](required_row_units_v260/analysis.json), [point regression](v260_runtime_tmp/query_regression_posthoc.json), [phase/fee diagnosis](v260_runtime_tmp/required_unit_cost_posthoc.json).

Limits: one fresh paired run; posthoc means do not replace the frozen negative outcome or establish future performance. Known type/change/equality interfaces and H2 remain; confidence allocation is per life/fixed arm. V256-V259 evidence stays immutable.
