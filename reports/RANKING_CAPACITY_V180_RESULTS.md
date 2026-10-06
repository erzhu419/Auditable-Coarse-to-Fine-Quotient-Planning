# V180 — Shared ranking capacity

**The six-feature shared linear class cannot reproduce all correct action rankings.** This is a capacity conflict on exact labels, while V179's positive mean utility remains unchanged.

| Scope | Certified uniform score-margin upper bound |
| --- | ---: |
| SOURCE, 47 roots | −189/512 = −0.369141 |
| TARGET, 24 roots | −253/2048 = −0.123535 |
| JOINT, 71 roots | −631/1536 = −0.410807 |

Even margin zero is impossible for all required comparisons. The smallest SOURCE proof uses only `v68_source_28` and `v6_crossing_rescue_pair_3`: correct LEFT over DOWN requires `beta_vacancy + delta <= -1/4` and `-beta_vacancy + delta <= -125/256`. Their other five features match. At delta=0, the same vacancy coefficient must be **≤−0.25 and ≥0.488281**. Thus a constant vacancy slope cannot capture the preferred middle vacancy count; changing the linear fitting loss cannot remove this contradiction.

All **56 absorbing-goal action labels** equal [first reward, 0, 1]. The retained dual evidence cancels linear feature coordinates, but not individual feature tuples. It therefore does not rule out an arbitrary nonlinear shared function of these six features, or establish that such a function can succeed.

**Next:** test cross-root consistency with one free value per distinct feature tuple, retaining all optimal-action alternatives. If this broader class is feasible, implement a SOURCE-trained nonlinear full-consequence model. If it also conflicts, add missing rank/layout information. This separates function shape from information loss before choosing model terms.

**17 pure tests, 62/62 independent checks, 35/35 source and 6/6 input comparisons pass.** Main/audit run once (1.07 s / 0.19 s), stderr 0. Main uses three LPs and three small exact dual balances; the auditor solves no LP. No new predictor, kernel evaluation, physical samples or native updates. Inherited costs and a two-file, zero-solve conflict explanation are retained.

[Protocol](../specs/RANKING_CAPACITY_V180.md) · [Capacity proofs](controlled_predictive_ranking_capacity_v180/capacities.json) · [Audit](controlled_predictive_ranking_capacity_v180/analysis.json) · [Ledger](v180_runtime_tmp/stage_checks.json) · [Two-root explanation](v180_runtime_tmp/conflict_explanation.json)

**Limitations:** Reused finite-H3 roots and fixed continuation; these bounds concern simultaneous optimal rankings, not the maximum attainable mean utility or general multi-episode learning. Keep V179's target +0.016831 utility and −1.98 percentage-point success change. H2 remains; U005 FAIL, U006 unstarted.
