# V262: targeted paid operator rows under one joint row confidence proof

V261 completed independently but was stage-negative: partial policy point means changed
candidate selection without reducing unresolved certificates. V262 tests the causal next
step: pay only the operator rows needed by the current unresolved certificate and feed
them into the native row pool. The query proof is unified across all arms; direct rows
never create executable units or D/R relabels.

The fixed arms are `DIRECT_ROW_REUSE`, `FULL_UNIT_ROW_CS`, and `CONTINUOUS_REUSE`.
There are three lives, 72 targets per life, nine jobs, and six workers. Fresh paired
seeds are source 328000, shared 329000, member 330000, execution 331000, and mix
332000. Caps, source A/B budgets, member batches (16), member cap (384), execution
reserve (2 per remaining target), type schedule, and target ordering are inherited from
V261. The prerequisite is a complete, independently valid, stage-negative V261.

All three arms use `unified_native_joint_row_cs_v262`, with the fixed V259 row-CS event
allocation and exact coupled risk gap. Before target-specific acquisition, DIRECT and
FULL use the same V261 required-row partial masks; CONTINUOUS uses complete S,D,
conditional-R units. The strong reference therefore retains complete-unit reuse.

At each target, `targeted_rows_for_unresolved(plan)` returns S,D,R when execution is
unresolved, D,R when only a query certificate is unresolved, and no rows after both are
resolved. DIRECT pays a frozen batch of 16 controlled-reset rows for each returned
operator. FULL pays 16 complete declared units for the same operator set, sampling R
only after a declared D recovery. CONTINUOUS has no target-specific row stage. Each
batch is stopped only after the batch plan is rebuilt and the row certificate, goal
upper bound, cap, or remaining budget settles the next action. Direct rows update only
native row counts and an explicit provenance ledger; they are excluded from unit logs,
trajectory statistics, and execution feedback.

Every tape row records life, arm, context, identity, target, operator, seed, paired
stream id, draw prefix, controlled-reset id, and outcome. Every target records initial,
target-acquisition, member, terminal plans, needed operators, direct-row and full-unit
fees, and budget snapshots. Source, shared, direct, target-unit, member, and execution
fees are retained separately. All 648 target decisions, auxiliary previews, member
histories, and actual executions are frozen before post-hoc truth scoring.

Advancement remains qualification-only: DIRECT must meet the V261 late-B/return and
matched-joint thresholds, use strictly fewer total paid observations than both controls,
respect every cap, and have zero false query/execution/impossibility/numerical/risk
claims across plans and histories. An independent audit must replay seeds, row ledgers,
unit declarations, unified support records, certificates, stopping decisions, fees,
execution accounting, and all paired gains/losses. The original scientific Gate remains
FAIL and U006 remains unstarted until a later registered result changes that status.
