# V177 — Exact H3 learning diagnostic

**Removing Monte Carlo label noise does not repair target action selection.** Both cohorts have first-action oracle headroom; TREE/ONE never fall back.

| Fixed cohort | Roots | Oracle − ONE | TREE − ONE | Headroom closed |
| --- | ---: | ---: | ---: | ---: |
| SOURCE, design-group mean | 47 | +0.172675 | +0.047262 | 27.37% |
| TARGET, root mean | 24 | +0.074259 | −0.032809 | −44.18% |

TREE learns canonical cell 8 rank ≤ 6. Both source crossfit directions are positive, but target reward falls 0.015746 and failure probability rises 0.017063, with success unchanged. Five target roots improve, eight worsen, eleven have equal value.

The three largest target losses enter the same leaf. On `v69_h3_21`, TREE predicts +0.14400 over ONE's action; exact gain is **−0.42279**, including failure probability +0.405 despite immediate reward +0.0078125. Shared leaf continuation coefficients do not preserve this board's action-dependent risk.

The original 48-root source roster contains **47 H3 and one H2**; the H2 root is excluded and retained, correcting V176's proposed count. Exact Fraction R/F/S labels follow one saved native teacher. Target choices freeze before kernel labels are read; no suffixes are invented.

**20 distinct pure checks, 128/128 independent checks, 60/60 frozen-source and 53/53 input comparisons pass.** Main/audit run once, 1.28 s / 1.23 s, stderr 0. Formal evaluation reads 9,737 cells / 30,618 rows / 42,950 atoms and performs 232 leaf solves; independent and inherited costs are separately retained. Physical samples, source games and native updates are zero. Two pre-freeze floating-comparison test failures remain recorded; only the affected case was rerun.

**Next:** replace raw rank predicates with frozen action-conditioned afterstate structure: vacancies, equal adjacent ranks in compressed rows/columns, and goal-merge opportunities. Keep exact labels, immediate-reward parameters, crossfit objective and support/tree limits fixed. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/EXACT_H3_LEARNING_V177.md) · [Summary](controlled_predictive_exact_h3_v177/summary.json) · [Audit](controlled_predictive_exact_h3_v177/analysis.json) · [Ledger](v177_runtime_tmp/stage_checks.json) · [Action-error decomposition](v177_runtime_tmp/transfer_diagnosis.json)

**Limitations:** These reused boards diagnose finite H3, where CUTOFF contributes zero failure/success. Oracle optimizes the first action under fixed continuation; design groups are not independent episodes. No population CI, fresh confirmation, long-game success or unique cause of earlier failures is established.
