# V261: query point learning from predeclared policy paths

V260 is complete and independently valid but stage-negative5/8. Required-row
acquisition loses8 joint/query targets against complete continuous reuse; shared
fees are identical. Partial comparisons grow while native complete-only point
estimates stop learning. V261 changes the query point estimator alone.

Three arms: PARTIAL_POINT_REUSE, REQUIRED_ROWS_REUSE (V260 frozen-full-point
required-unit control), CONTINUOUS_REUSE (complete-unit strong reference).
Lives0/1/2, targets3..26 and30..77,72 per job,648 target decisions, nine jobs,
six workers and cold per-job caches. Fresh paired seed bases source323000,
shared324000, member325000, execution326000, mix327000 use original addressing.
All three execution engines use V259 continuous compatible row confidence.
Both first arms use identical V260 required-row acquisition rules; CONTINUOUS
keeps complete S,D,conditional-R. No change to phase budgets or type scheduling.

For PARTIAL_POINT_REUSE, maintain a native context/type aggregate per policy.
SHORT depends on S; DETOUR_RETURN on D; DETOUR_RETRY on D,R. WAIT is known zero.
A SOURCE/SHARED unit updates a policy aggregate exactly when the unit declaration
covers that path BEFORE its outcomes. Use every such D/R unit, including every
non-RECOVERY branch. An S/D declaration cannot update RETRY even if its D did
not recover. Never join fields from different units or impute missing outcomes.
Tails, member observations and actual execution feedback do not update query
point aggregates. No cross-context point reuse: B learns only B, A_RETURN only A.

Per policy retain n,delivery,failure,recovery_calls,last_unit_id. For SHORT use
reward=-short_cost, failure=n_failure/n and delivery=n_delivery/n. For RETURN
reward=-detour_cost; D=RECOVERY is an abort, not delivery/failure. For RETRY use
reward=-detour_cost-retry_cost*n_recovery_calls/n, including actual R terminal
success/failure after recovery and D terminal outcome otherwise. Before any
unit, zero vectors follow the old empty-history behavior. With all declarations
ALL, these means equal the old complete-joint empirical vectors exactly.
Keep the old full joint point state as well; add partial aggregates only to the
new arm. Retain query_point_method/native policy aggregate fields so the auditor
can reconstruct means from actual units. Do not repeat long per-policy ID lists.

Keep original goal/risk empirical argmax weights and lexical ties. Only its
input vectors change in the new arm. Comparison evidence still uses fixed V260
ordered streams over complete required-row declarations, legal static context
compatibility, original scores/predictable bets and216 events at threshold4320.
Do not reset evidence when candidates change. All ordered directions were
reserved before data, so adaptive empirical choice adds no new confidence event.
Keep the same query regret tolerance1/20; point means are not certificates.

SHARED mask rules remain: before each batch retain all12 actual public cost/type
plans; per type union every uncertified comparison's fixed required_rows; any
execution-unresolved cost adds ALL. First two arms use the same rule and cyclic
unready-type selector, batch<=256. Reserve maximum unit cost before any draw;
R requires D and is sampled only when predeclared and D reaches RECOVERY.
Insufficient batch remainder uses the original native-only S tail. SOURCE stays
full A3456/B1152 per arm. Source/member/exec fees, member16/cap384, total life
caps14144/17072/17168, future B source and2-per-remaining-target reserves remain.
All12 preview AND stop, execution goal2/risk1/20, old member operator choice,
posterior/mix, original20-step goal-dual search and feedback rules stay fixed.

Capture new sources/spec/tests and dependencies before fresh sampling. Freeze
all648 terminal decisions, every initial/member plan, full preview and actual
execution before truth scoring. Independently replay declarations and observed
fields, native per-policy aggregates, full joint metadata, vectors/argmax,
unchanged comparisons/events/row bounds/goal proof, stops, seeds and every fee.

Eight frozen advancement conditions: new point arm late-B queries>=27/36 and
return>=54/72; late-B, return and total joint completion each no worse than BOTH
controls; strictly fewer full paid observations than BOTH controls; all life
caps; zero false query/execution/impossibility/numerical-bound claims or risk
violations across all arms/history/previews/terminal plans, and goal upper<=own
box. Require valid independent audit. Retain paired query/joint/execution and
impossibility gains/losses vs each control, all source/shared/member/exec fees,
CPU and partial/full/tail unit counts. Distinguish paid acquisition changes from
cost changes caused by fewer executions; do not treat a loss of work as efficiency.

Require V260 complete, independent valid and frozen stage-negative. Preserve
V256-V260 results, including their negative outcomes, without pooling old seeds
or posthoc retuning. Known type/change/equality interfaces and H2 remain. The
new estimator and its improvement are untested until this frozen run. Confidence
scope is per life/fixed arm; original scientific Gate FAIL and U006 unstarted.
