# V254: direct executable-trajectory evidence

The frozen qualification is **positive**. Both methods read the same 48,384
fresh controlled observations, including 13,824 source observations, and choose
identical policies. RETRY is observed only after actual RECOVERY.

| Terminal public targets | ROW_JOINT | TRAJECTORY | Paired gains / losses |
|---|---:|---:|---:|
| Goal certified | 50/72 | 59/72 | 9 / 0 |
| Risk certified | 48/72 | 56/72 | 8 / 0 |
| All three queries certified | 48/72 | 48/72 | 0 / 0 |
| Certificate computation, summed process CPU | 73.31 s | 10.81 s | 85.25% less |

Both methods have zero false certificates; terminal point policies have zero
true regret. The 24 incomplete projections remain because the gains leave
opposite gaps: life0/type1 has goal3/8, risk0/8; life1/type2 has goal8/8,
risk0/8; life2/type1 has goal0/8, risk8/8. Fixed round-robin continues sampling
the other two types although both already pass all costs after source learning.

Twenty-two initial focused tests and one repair regression pass. Independent
audit is valid with zero failures: 180 decision pairs, 22,284 complete rounds,
648 row profiles and 7,200 leaves. Science runs once, exit0, wall29.79s, retaining
three SLSQP clipping warnings. The first audit fails on one-sided cost-string
normalization; the repaired second audit passes on unchanged science, exit0,
wall25.14s, stderr0. Original failure/source are preserved; only auditor/test
are recaptured after science.
See [verification](v254_runtime_tmp/verification_summary.json),
[independent analysis](executable_trajectory_v254/analysis.json) and
[audit repair](executable_trajectory_v254/audit_repair.json).

Next compare fixed round-robin against currently joint-unresolved type sampling,
keeping source, budgets, point-selection rule, bets and confidence unchanged.
Reconsider all queries/costs after each batch; measure combined gains and fees.
Then qualify native-trajectory integration in fresh A/B/A against rebuilding.

Limits: stationary known types; projections reuse evidence. No full-lifecycle or
interaction-saving result. Costs count controlled observations, not episode
timesteps. Confidence is separate per fixed method, with no OR. V251 remains
10/11; the original scientific Gate remains FAIL and U006 remains unstarted.
