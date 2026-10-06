# V181 — Arbitrary shared feature capacity

**The six features lose information needed for consistent cross-board decisions.** Giving every distinct tuple an independent, unconstrained value still cannot reproduce all correct rankings. This excludes arbitrary nonlinear `g(phi)` in the frozen score `first_reward + g(phi)`.

| Scope | Roots / distinct tuples | Certified margin upper bound |
| --- | ---: | ---: |
| SOURCE | 47 / 49 | −11/128 = −0.085938 |
| TARGET | 24 / 34 | 0; weak rankings attainable |
| JOINT | 71 / 57 | −63/512 = −0.123047 |

The two-root SOURCE proof uses A=(0,2,1,0,0,0) and B=(0,3,1,0,0,0). At zero margin, `v68_source_13` requires **g(A)−g(B)≤5/64**, while `v68_source_28` requires **g(A)−g(B)≥1/4**. The exact first rewards are already accounted for. Their equal-weight certificate cancels both vertices; this is information aliasing, rather than a restriction to linear slopes.

TARGET's zero bound alone does not exclude a correct tie policy. Here a concrete pair does: `v69_h3_02` needs LEFT(A) over DOWN(B), and `v69_h3_11` needs LEFT(B) over DOWN(A), where A=(0,3,0,0,0,0), B=(0,3,1,0,0,0). First rewards are equal within each root. Weak rankings force g(A)=g(B); frozen DOWN-before-LEFT tie handling selects the wrong action in both. The saved weak witness is not a usable optimal policy. The JOINT certificate is a three-edge negative cycle, including a nonzero failure-probability comparison.

SOURCE contains 26/34 TARGET tuples; 16/24 TARGET roots have all their tuples observed in SOURCE. Coverage cannot resolve the contradictions. **Next: implement a shared full-consequence model that retains tile ranks and local layout, train only on SOURCE, and compare on the fixed TARGET with unchanged labels and controls.** Merely changing nonlinear shape, loss or sampling cannot remove these demonstrated aliases.

**14 pure tests, 54/54 independent checks, 37/37 source and 4/4 input comparisons pass.** Main/audit run once (0.96 s / 0.07 s), stderr 0; three main LPs and three exact dual balances, no audit LP. No new fitted predictor, physical samples, source games or native updates. Inherited costs, test ledgers and the two-input, zero-solve explanation are retained.

[Protocol](../specs/SHARED_FEATURE_CAPACITY_V181.md) · [Capacity proofs](controlled_predictive_shared_feature_capacity_v181/capacities.json) · [Audit](controlled_predictive_shared_feature_capacity_v181/analysis.json) · [Ledger](v181_runtime_tmp/stage_checks.json) · [Cycle explanation](v181_runtime_tmp/conflict_explanation.json)

**Limitations:** Reused finite-H3 roots, exposed TARGET and fixed continuation teacher. The result concerns simultaneous correct decisions in this score class, not the best attainable mean utility or general strategic learning. V179's TARGET +0.016831 utility and −1.98 percentage-point success change remain. Keep H2; U005 FAIL, U006 unstarted.
