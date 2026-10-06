# V179 — Shared action-conditioned consequences

**Sharing afterstate consequences turns the fixed H3 diagnostic positive.** One six-feature full-vector regression replaces partitions; exact labels, first rewards and RAW/ONE/STRUCTURE baselines stay fixed.

| Cohort | SHARED − ONE | SHARED − RAW | Oracle headroom closed |
| --- | ---: | ---: | ---: |
| SOURCE, design-group mean | +0.090490 | +0.043228 | 52.4% |
| TARGET, root mean | +0.016831 | +0.049639 | 22.7% |

TARGET has 11 improved, 3 worsened and 10 equal-value roots versus ONE, with zero fallback. Positive-regret roots fall from 13 to 6; remaining oracle regret is **0.057428**. The target component change is R **+0.036560**, F **−0.000063**, S **−0.019792**: higher utility does not mean higher success probability.

The optimistic per-root feature-restricted oracle preserves **98.5%** of target headroom (+0.073168 versus full +0.074259); only two roots lose headroom to action aliasing. This ceiling ignores cross-root and linear constraints. The main unresolved issue is therefore shared estimation or function capacity, rather than within-root aliasing alone. On the largest remaining error, `v69_h3_01`, LEFT is predicted +0.58788 over DOWN but is actually **−0.94737**; DOWN wins immediately, whereas LEFT succeeds with probability 0.525.

**16 pure tests, 23/23 independent checks, 66/66 source and 7/7 input comparisons pass.** Main/audit run once (0.96 s / 0.63 s), stderr 0. New work is 284 deterministic swipes, 233 source pair rows and one 6×3 least-squares solve. Baselines and exact kernels are reused; new physical samples, source games and native updates are zero. All inherited/new costs and a three-file, zero-fit diagnosis of all six remaining errors are retained.

**Next:** freeze an action-ranking capacity diagnostic to distinguish incompatible shared linear rankings from a SOURCE squared-error solution that learns the wrong rankings. Use the result to choose between a richer shared consequence function and a SOURCE decision objective; examine the known absorbing-goal boundary in the largest error. Do not fit a deployable predictor to TARGET labels or first optimize computation cost.

[Protocol](../specs/SHARED_CONSEQUENCES_V179.md) · [Summary](controlled_predictive_shared_consequences_v179/summary.json) · [Audit](controlled_predictive_shared_consequences_v179/analysis.json) · [Ledger](v179_runtime_tmp/stage_checks.json) · [Remaining errors](v179_runtime_tmp/remaining_diagnosis.json)

**Limitations:** Reused 47 SOURCE/24 TARGET finite-H3 roots with fixed continuation, not fresh confirmation or general multi-episode strategic learning. Retain H2; U005 FAIL, U006 unstarted.
