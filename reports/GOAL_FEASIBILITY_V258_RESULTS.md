# V258: goal-feasibility acquisition through A/B/A

The frozen stage **fails: six of eight conditions pass**. Independent audit is
valid. Late-B reuse queries23/36 miss27/36; paid observations do not decrease.

| Complete lifecycle | REBUILD | REUSE |
|---|---:|---:|
| Joint completion | 160/216 | 176/216 |
| Queries certified | 176/216 | 192/216 |
| Execution resolved | 200/216 | 200/216 |
| New impossibilities versus same-snapshot box bounds | 0 | 0 |
| Late-B / return queries | 14/36;72/72 | 23/36;72/72 |
| Full paid observations | 48,241 | 48,248 |
| Summed model process CPU | 174.64 s | 190.92 s |

Sixteen paired joint gains, no losses. Shared cost34,200 per arm; reuse saves16
member draws but pays23 extra execution draws. A query qualification uses65.87%
of shared budget; every B phase exhausts its remainder. The16 execution-only
reuse gaps receive complete query rounds even after their queries are ready.

All16 new multipliers move and tighten upper bounds, but all16 full retained
CS intersections still admit risk1/20, goal>2 kernels. Independent membership
verification passes208 constraints. This establishes an information barrier
to further impossibility certification on these unchanged regions.

Next predeclare continuous row evidence for legally identical A/B parameters,
then test declaration-specific acquisition: query rounds for unresolved queries,
feasibility rows for unresolved execution goals. Preserve budgets and full fees.

Twenty-two tests pass after a retained fixture repair. Science/audit each run
once: exit0, stderr0, wall83.06/270.10s; audit valid, zero failures over432 targets,
3,456 previews and439 intermediate plans. [Verification](v258_runtime_tmp/verification_summary.json),
[audit](goal_feasibility_v258/analysis.json), [budget diagnosis](v258_runtime_tmp/phase_budget_posthoc.json),
[region witnesses](v258_runtime_tmp/goal_region_posthoc.json), [independent witnesses](v258_runtime_tmp/independent_region_witness_posthoc.json).

Limits: fresh seeds prevent causal comparison with V256; both arms get the two
new mechanisms. Known types/change/equality interfaces and H2 remain. Original
scientific Gate FAIL; U006 unstarted. V256 passed and V257 negative stay frozen.
