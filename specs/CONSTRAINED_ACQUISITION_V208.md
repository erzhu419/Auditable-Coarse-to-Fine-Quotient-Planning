# V208 — task-sufficient constrained policy acquisition

Freeze before tests/new observations. Keep V207 task, three empty persistent
arms, chronological12-task lifecycle, member pilots for all three operators,
16 batch,384 total budget, raw complete-member confidence family2016,
online condition fits and all four COST/QUALITY/RISK_RETENTION/LEARNING gates
verbatim. Do not reinterpret the V207 failed quality/cost gate.

Replace only post-pilot allocation. For each non-WAIT pure policy, compute
point utility achievable by mixing that whole policy with WAIT under failure
limit. Value = max(0, R+4S)*min(1,.05/pointF); all pointF positive.
If some candidate point value>=2, prefer the fewest stochastic operators
(SHORT and DETOUR_RETURN need1, DETOUR_RETRY needs2), then greatest point
value, then lexicographic policy. If none, greatest point value then policy.
The prediction chooses a task-sufficient evidence target; it is not a certificate.
No teacher, true law, fixed weather-to-action map or imposed RETURN.

For SHORT query SHORT_PASS; for DETOUR_RETURN query DETOUR_PASS.
For DETOUR_RETRY compare two hypothetical single-operator knowledge resolutions:
on copies of current envelopes, replace only DETOUR or RETRY category bounds
by current selected-field posterior means as zero-width bounds.
Compute settled common-kernel upper failure/lower goal for the selected policy
and its best WAIT mixture. Choose greatest prospective certified lower goal,
ties DETOUR then RETRY. This is a deterministic sensitivity forecast, not an
expected posterior gain or actual evidence. Counts/model/envelopes must remain
unchanged. A shared mean outside current member boxes is allowed in this
hypothesis forecast; never use it for the actual safety plan or stopping.

Retain member counts,pilot,reason,target_policy,point_scores and sensitivity
scores; no entire hypothetical model tables. Actual plan/stop always raw
member observations and robust mixture optimization. At certificate>=2 stop,
even if other point queries remain unresolved. Own full three-query policies
and late pre-query regret stay evaluated, so sacrificing strategic knowledge
to certify RETURN cannot silently pass LEARNING.

Fresh paired streams209000+(life*12+task_index)*3+operator_index;
bootstrap2089005000 shared lifecycle resamples124/4874.
Three arms follow identical allocation; LOCAL keeps all previous observations.
No prepaid samples or budgets beyond165888 actual calls.
All four gates unchanged from V206/V207 and all required for
CONSTRAINED_ACQUISITION_SUPPORTED; otherwise NOT_SUPPORTED.
Four synthetic tests: point risk-feasible WAIT objective; sufficient one-operator
target over optional retry; RETRY sensitivity copies never create observations;
independent full acquisition correspondence. One tests/main/audit, only failed
commands repaired/repeated with original failure retained. Source byte capture
all dependencies including old independent mathematics, no hashes.
Output reports/constrained_acquisition_v208; runtime reports/v208_runtime_tmp.
Old versions unchanged. Compact results/current route update. U005 FAIL,
U006 unstarted and old-game H2 remain.
