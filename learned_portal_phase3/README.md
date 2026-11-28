# Phase-III (`learned_portal_phase3`): PAC-Certified Spectral-Portal Quotient Learning (SPQL `v4.1 / R7A` Release-Frozen)

This isolated package implements **PAC-Certified Spectral-Portal Quotient Learning (SPQL)** — learning bottleneck quotient Green operators **end-to-end from unknown-dynamics exploration trajectories** in finite-state LMDPs without spatial coordinates or occupancy-grid priors, organized into **four explicit guarantee tiers** (`Tier-1` exact M-matrix all-goal sandwich & coordinatewise surrogate optimality, `Tier-2` time-uniform predictable-sampling confidence sequences, `Tier-3` outward-rounded IEEE-754 stored-operator & delivered-`CSR` policy verification, and `Tier-4` empirical fitted Voronoi continuous surrogate control) plus **explicitly labeled post-hoc numerical diagnostics** (`coordinatewise surrogate & Bauer row-stochastic simplex evaluators`).

> **Strict Non-Destructive Archive Integrity (`47 / 47` Frozen Files Untouched)**: Frozen Phase-I (`green_response/`, `271ac8df...`), Phase-II (`quotient_phase2/`, `e6ea565b...` + all 13 JSONs including `m233_clean_isolation_replication.json` `73101638...`), Phase-III `v1` (`0e2c76ea...`), `v2` (`6167bd5f...`), `v3` (`0ffd1d3a...`), and `v4` (`p3_v4_r675_verified_results.json`, `798a9e2b...`) are **100% byte-for-byte untouched** (the R7A runner checks a 47-path SHA-256 manifest against commit `5be3f35`).

---

The [November 28 project review](../GREEN_PLANNING_REVIEW.md) distinguishes the published evidence from the latest source and reproduction. Fresh outputs default to project-local `.tmp/` directories.

## Core Modules & Artifacts

| File | Description |
| :--- | :--- |
| `__init__.py` | SHA-256 byte-freeze guards (`verify_phase1_and_phase2_untouched`, `verify_phase3_v1/v2/v3/v4_archive_untouched`) and Phase-III manifest (the published sidecar records `45b76718...`; reproductions record their own source hashes). |
| `spql_core.py` | Time-uniform Dual PAC M-matrix envelopes $(\underline{A}_n, \overline{A}_n)$, killed-portal Dirichlet reduction onto $E_\Gamma = \Gamma \setminus G$, binary Fiedler PoU trees (one fresh RHS for two cold child columns when the parent is cached), outward-rounded IEEE-754 Higham verifiers (`2^{-1074}` subnormal guard, zero `1e-12` floors), log-space `CSR` policy + SHA-256 binding, explicit `interface_candidate_stage_ms` / `certified_bounds_stage_ms` timers, and separated LU counters. |
| `baselines_and_contracts.py` | Matched Tier-3 PAC comparators & ablations, `evaluate_posterior_pac_policy_upper_bound` (`coordinatewise surrogate diagnostic`) + `evaluate_row_stochastic_simplex_posterior_diagnostic` (`Bauer exact vertex simplex diagnostic`), and the **21-gate deterministic counterexample suite (`P3-C01..P3-C21`)**. |
| `continuous_manifold_spql.py` | Zero-silent-fallback continuous Voronoi surrogate control (`raises ValueError if Pi_ext_csr is None`), damped (`0.85`), padded (`4e-4`), chord-guarded Euler simulator with exact Liang–Barsky chord checks across `96/96` goals. |
| `run_phase3_r7a_sidecar_audit.py` | Non-destructive `R7A` provenance & diagnostic sidecar runner (`21` gates, `672` actual cross-commit `67532c9` vs. current E3 `CSR` policy comparisons, `320` CE `pred_val` + separated `global_lu_rhs`, Decision-C Bauer simplex table, and `R7A` figures). |
| `p3_v4_r7a_sidecar_diagnostics.json` | Primary `R7A` provenance & diagnostic sidecar (`SHA-256: 6bbedca9...`, `21/21` gates, `672/672` E3 `CSR` diffs $\le 1.75\times 10^{-14}$, `320` CE `pred_val` verified). |
| `p3_v4_r7a_fig1_rotated_pac_and_decomposition.png` | Updated 3-panel figure (`explicit v2 vs. v4 labels; 94.5% CE self-underestimation distinguished from 0% PAC violations`). |
| `p3_v4_r7a_fig2_3d_linear_mf_and_continuous.png` | Updated 2-panel figure (`Plug-In CE labeled "258 global RHS"; Tier-4 continuous surrogate with explicit numerical fallback counts`). |
| `p3_v4_r675_verified_results.json` | Byte-frozen `v4` primary benchmark ledger (`SHA-256: 798a9e2b...`, `1,952` saved method events: `960` discrete PAC + `320` CE + `672` Tier-4 continuous). |
| `NEURIPS_MANUSCRIPT_DRAFT.md` | Current SPQL manuscript (`repaired Proposition 5 surrogate/simplex scope, Theorem 4 sufficiency distinction, Infante et al. 2022 & Saxe et al. 2017 citations`). |

---

## Reproducible Single-Threaded Execution Commands

1. **Fast 21-Gate Mathematical, Counterexample, & Freeze Verification (`~13.1s`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     PYTHONPATH=. /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_r7a_sidecar_audit --gates-only
   ```

2. **Full Non-Destructive `R7A` Cross-Commit `CSR`, CE `pred_val`, & Bauer Simplex Sidecar (`workers = 1`, `~12.2 min`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
     PYTHONPATH=. /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_r7a_sidecar_audit
   ```

---

## Headline Verified Summary (`v4` `798a9e2b...` + `R7A` Sidecar `6bbedca9...`)

- **21/21 Contract Gates Passed (`P3-C01..P3-C21`) & `0 / 960` Discrete PAC Violations**: Separates `960` discrete PAC events (`384 E1 + 576 E2`, `0` zero-slack violations, `0` reaching tight $\varepsilon = 0.18 / 0.15$) cleanly from `320` uncertified `PlugIn_CE` controls and `672` Tier-4 empirical continuous surrogate events.
- **Coordinatewise Surrogate vs. Bauer Row-Stochastic Simplex Diagnostic (`Proposition 5`, `P3-C21`)**: Accommodates 2-state counterexamples (`simplex worst case 2.9534 < U_PAC,full = 3.2651 < surrogate 3.5027` for $\hat{\pi}_{\mathrm{CE}} = (0.2, 0.8)$) while quantifying on fixed E1/E2 data that observed-support simplex constraints alone tighten `Full_PAC` by only `0.36%` in 2D (`67.73 -> 67.48`) and `0.0005%` in 3D (`218.4366 -> 218.4355`), on the fixed policies. The marginal 3D control cost of coarsening is `+0.466` (`+0.74%`). Observed-only support is an additional modeling assumption. More informative confidence sets remain a research question.
- **Actual 672-Policy Cross-Commit E3 Provenance (`67532c9` vs. Current)**: Independent two-commit reconstruction confirms bit-identical inputs on `8/8` seeds, `672/672` identical fallback status, `max_abs_entry_diff = 8.77e-15`, and `max_matrix_infinity_norm_diff = 1.75e-14 <= 1e-12` (`numerical tolerance equivalence, 0 rollout reruns`).
