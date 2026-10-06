# V178 — Action-afterstate structure

**The structural split family does not improve the retained H3 diagnostic.** Labels, objective, support rules and V177 RAW/ONE baselines remain fixed.

| Cohort | STRUCTURE − ONE | STRUCTURE − RAW |
| --- | ---: | ---: |
| SOURCE, design-group mean | −0.002740 | −0.050002 |
| TARGET, root mean | −0.153002 | −0.120194 |

The target still has oracle−ONE headroom **+0.074259**; both models have zero fallback. Relative to RAW, seven target roots improve and six worsen, with three new and three resolved positive-regret cases.

Only **12/264 candidates** are comparable, all vacancy predicates. Every equal-adjacency, goal-pair, goal-reached and legality predicate fails the unchanged fit-child root requirement. The chosen split is `DOWN:vacancy:1`. Thus the effective tree does not use the intended merge/goal distinctions. On `v69_h3_18`, it predicts +0.01909 for DOWN over ONE's UP; exact gain is **−2.99824**, with equal immediate reward but LOST versus WON within H3.

**13 pure checks, 26/26 independent checks, 65/65 frozen-source and 7/7 input comparisons pass.** Main/audit execute once, 0.65 s / 0.44 s, stderr 0. New work includes 284 deterministic swipes, 264 candidates and 75 leaf solves; feature caches cover 71 roots. Old kernels and baselines are reused without reevaluation/refitting. Physical samples, source games and native weight updates are zero; all inherited and new costs are retained.

**Next:** replace per-leaf action constants with one shared action-conditioned consequence model. Orient each afterstate to a common action direction and use six aggregate features: goal reached, vacancy count, row/column equal-adjacency counts, and row/column goal-pair counts. Fit shared complete-vector coefficients from exact paired continuation differences; retain immediate reward, root weighting and global action support. This changes how sparse structure is shared, rather than lowering the split threshold.

[Protocol](../specs/AFTERSTATE_STRUCTURE_V178.md) · [Summary](controlled_predictive_afterstate_structure_v178/summary.json) · [Audit](controlled_predictive_afterstate_structure_v178/analysis.json) · [Ledger](v178_runtime_tmp/stage_checks.json) · [Support diagnosis](v178_runtime_tmp/support_diagnosis.json)

**Limitations:** These are reused finite-H3 boards, not fresh confirmation or long-episode learning. Failure of this supported split mechanism does not disprove merge features in other models. Oracle uses fixed continuation. Keep H2; U005 FAIL, U006 unstarted.
