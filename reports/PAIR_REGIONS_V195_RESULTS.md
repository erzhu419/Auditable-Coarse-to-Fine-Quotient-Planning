# V195 — Coordinate regions merge opposite continuation consequences

**TREE32 fails against its same-input RAW32 control and all strong primary baselines; neither new arm is adopted.** The learner receives complete positioned afterstates, rather than relation moments. SOURCE143/36 equal-group actual utility selects depth4/minimum8 roots for TREE32 and k32 for RAW32; held-out utilities are **1.070593 / 1.080503**. Full-SOURCE regret roots are 91/78, respectively.

| Fresh TARGET96 arm | Utility | Regret roots | TREE32 minus arm | Positive replicas |
|---|---:|---:|---:|---:|
| TREE32 | 1.113184 | 63 | — | — |
| RAW32 | 1.204639 | 57 | **−0.091455** | 1/4 |
| CONDITIONAL (V194) | 1.217250 | 44 | **−0.104066** | 1/4 |
| LINEAR | 1.263427 | 46 | **−0.150243** | 0/4 |
| NONLINEAR (V192) | 1.228243 | 42 | **−0.115059** | 0/4 |
| OLD_SHARED | 1.268807 | 45 | **−0.155623** | 0/4 |

TREE32 loses reward and success and increases failure relative to LINEAR: ΔR/F/S **[−0.088469,+0.004092,−0.057682]**. Of its eleven regret roots with nonzero true selected-minus-oracle success difference, nine estimates are zero and one has the wrong sign. RAW32 misses zero of five; CONDITIONAL misses one of three. The frozen V194 CONDITIONAL−PAIR98 benefit also reverses on this cohort, to **−0.008912**.

Retained replay localizes the largest loss, `v195_target_r02_16`: DOWN instead of oracle RIGHT costs **2.655801**. The immediate reward advantage is +0.125, but true tail R/F/S difference is **[−1.375801,+0.405,−1]**. Both direction queries enter **leaf15**, so raw antisymmetric and projected differences are exactly zero. That leaf contains 1,347 prototypes from 142 roots/36 groups: **92 positive and 92 negative success labels**, with weighted contributions **+1.493967 / −1.493967**. They cancel. The full library has 190 nonzero-success prototypes; the selected tree has fourteen leaves, four with nonzero mean success. Successful SOURCE signals exist inside the merged region; the learned coordinate conditions fail to separate their applicability.

**Next:** learn shared relational condition programs preserving tile identity, merge dependencies and goal-relative continuation structure. Use SOURCE to induce applicability and select by actual utility, then freeze before fresh targets. This result prioritizes condition induction over coordinate partition refinement.

**Verification/cost:** 21 distinct tests pass after correcting one faulty integer-threshold assertion before actual data; the first failure and targeted rerun are retained. **228/228 independent audit, 91/91 source, 10/10 input** comparisons pass; main/audit once, **74.90/30.60 s**, stderr0. Three libraries, seventeen tree fits/seven RAW configurations, zero parameter solves; 96 exact kernels/plans/labels. Zero new SOURCE games, physical random samples or native updates. Full costs remain in the ledger.

**Limitations:** One fresh descriptive cohort; diagnostic denominators depend on each arm's chosen errors. The leaf replay identifies this failure mechanism, not every error's cause. Coordinate regions are not compositional goal-path programs, and fixed-teacher H3 does not establish general strategy. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/PAIR_REGIONS_V195.md) · [Summary](publication/v327_snapshot/controlled_predictive_pair_regions_v195/summary.json.gz) · [Models](controlled_predictive_pair_regions_v195/models.json) · [Shared libraries](controlled_predictive_pair_regions_v195/libraries.json) · [Choices](controlled_predictive_pair_regions_v195/choices.json) · [Audit](publication/v327_snapshot/controlled_predictive_pair_regions_v195/analysis.json.gz) · [Ledger](v195_runtime_tmp/stage_checks.json)
