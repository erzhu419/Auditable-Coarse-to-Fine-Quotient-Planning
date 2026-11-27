# Phase-III (`learned_portal_phase3`): PAC-Certified Spectral-Portal Quotient Learning (SPQL `v3` Delivery-Verified)

This isolated package implements **PAC-Certified Spectral-Portal Quotient Learning (SPQL)** — learning decision-sufficient bottleneck quotient Green operators **end-to-end from unknown-dynamics exploration trajectories** in finite-state LMDPs without spatial coordinates or occupancy-grid priors, organized into **four explicit guarantee tiers** (`Tier-1` exact M-matrix all-goal sandwich, `Tier-2` time-uniform predictable-sampling confidence sequences, `Tier-3` IEEE-754 `float64` Higham-verified multi-decade bounds, and `Tier-4` empirical fitted Voronoi continuous surrogate control).

> **Strict Non-Destructive Archive Integrity**: Frozen Phase-I (`green_response/`, SHA-256 `271ac8df...`), Phase-II (`quotient_phase2/`, SHA-256 `e6ea565b...`, `m233_sisc_unlock_results.json` `339e723f...`, `m233_clean_isolation_replication.json` `73101638...`), Phase-III `v1` exploratory archive (`p3_neurips_benchmark_results.json`, SHA-256 `0e2c76ea...`), and Phase-III `v2` archive (`p3_v2_verified_benchmark_results.json`, SHA-256 `6167bd5f...`) are **100% byte-for-byte untouched** (`verified automatically in Gates P3-C10 & P3-C18`).

---

## Core Modules & Artifacts

| File | Description |
| :--- | :--- |
| `__init__.py` | SHA-256 byte-freeze guards (`verify_phase1_and_phase2_untouched`, `verify_phase3_v1_archive_untouched`, `verify_phase3_v2_archive_untouched`) and Phase-III manifest (`7fd45fbf...`). |
| `spql_core.py` | Time-uniform Dual PAC M-matrix envelopes $(\underline{A}_n, \overline{A}_n)$, exact killed-portal Dirichlet reduction onto $E_\Gamma = \Gamma \setminus G$, strictly binary Fiedler PoU trees (`max_children = 2`, exact `50.0%` LU conservation), Tier-3 IEEE-754 Higham verifiers (`higham_verify_upper_subsolution`, `higham_verify_lower_supersolution`), shortest-path Doob $h$-transform multi-decade equilibration, and typed `solver_status` / `fallback_*` reporting. |
| `baselines_and_contracts.py` | Matched Tier-3 PAC comparators & mechanism ablations (`PlugIn_CE_FullGraph`, `Uncompressed_SpectralSchur_PAC`, `MatrixFree_SpectralSchur_PAC`, `Scalar_L0_Portal_Ablation`, `TransitionSVD_Resolvent_Ablation`, `Sampled_Desirability_TD`) and the **18-gate deterministic counterexample, fault-injection, & delivery suite (`P3-C01..P3-C18`)**. |
| `continuous_manifold_spql.py` | Zero-fallback continuous Voronoi surrogate control (`raises ValueError if Pi_ext_csr is None`), damped (`0.85`), padded (`4e-4`), chord-guarded Euler diffusion simulator with **exact analytic Liang–Barsky chord collision checks across `96/96` goals**, and `7` same-data controllers (`including SPQL_UniformPortals`). |
| `run_phase3_r747_delivery_repair.py` | Single-threaded (`OMP/BLAS/MKL = 1`, `workers = 1`) `v3` delivery-verified runner on `seeds 4000..6007`, enforcing `192/192` E2 policy delivery and `96/96` E3 zero-fallback policy delivery. |
| `p3_v3_r747_delivery_verified_results.json` | Primary `v3` delivery-verified ledger (`SHA-256: 0ffd1d3a...`, `18/18` gates, `192/192` E2 policies, `96/96` E3 policies, `0` PAC violations, `0` exact chord hits). |
| `p3_v3_fig1_rotated_pac_and_active.png` | 3-panel `v3` figure: $37^\circ$-rotated 9-room Cap-80 regret, finite policy delivery vs. tight $\varepsilon = 0.18$, and `PlugIn_CE` optimism underestimation vs. `SPQL` PAC validity. |
| `p3_v3_fig2_3d_matched_delivery_and_continuous.png` | 2-panel `v3` figure: matched-delivery 3D cave lifecycle (`192/192` policies) and zero-silent-fallback 7-control continuous surrogate evaluation (`96/96` policies, `0` chord hits). |
| `p3_v2_verified_benchmark_results.json` | Byte-frozen `v2` archive (`SHA-256: 6167bd5f...`, preserved untouched for historical audit traceability). |
| `p3_neurips_benchmark_results.json` | Byte-frozen `v1` exploratory archive (`SHA-256: 0e2c76ea...`, preserved untouched). |
| `NEURIPS_MANUSCRIPT_DRAFT.md` | Full `v3` delivery-verified manuscript draft (`4-tier scope`, `Propositions 1–4`, `Theorems 1–4` with `Corollary 1.1`, honest boundary disclosures, and complete proofs in Appendix A). |

---

## Reproducible Single-Threaded Execution Commands

1. **Fast 18-Gate Mathematical, Fault-Injection, & Multi-Decade Delivery Audit (`~11.1s`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     PYTHONPATH=. /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_r747_delivery_repair --gates-only
   ```

2. **Full `v3` Delivery-Verified Multi-Seed Benchmark & Figure Generation (`workers = 1`, `~12.4 min`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
     PYTHONPATH=. /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_r747_delivery_repair
   ```

---

## Headline Verified `v3` Summary (`p3_v3_r747_delivery_verified_results.json`, `0ffd1d3a...`)

- **18/18 Deterministic Contract Gates Passed (`P3-C01..P3-C18` in `11.09s`)**: Includes fault-injected subsolution rejection (`P3-C16`), 3D `seed=5000` multi-decade coarse policy delivery (`higham_pes_eps_fl = 3.55e-14`, `P3-C17`), continuous `None`-policy rejection + exact Binomial $m=69$ quantifier + 4-state rank-2 SVD positive example + `v2` archive byte-freeze (`P3-C18`).
- **Rotated 2D Multi-Room PAC Calibration & Active Exploration (`Block E1`)**: `0` PAC violations across all budgets vs. `73.4%–98.4%` optimism violations for `PlugIn_CE_FullGraph` (`which attains 2.19 uncertified regret at 240k`). Under `v3` Tier-3 witness repair at `240k`, both `SPQL_Active` and `SPQL_Passive` deliver **`128/128` coarse-certified policies (`0` fallbacks)**, with `SPQL_Active` improving both regret (`7.81` vs. `10.63`, $p_{2s} = 8.48\times 10^{-6}$) and certified width (`47.44` vs. `69.18`, $p_{2s} = 9.28\times 10^{-7}$).
- **Matched-Delivery 3D Curved Caves (`Block E2`, `192 / 192` Certified Policies)**: `SPQL` delivers **`192/192` proper policies** (`180` coarse at `16.7%` active DOFs + `12` timed/charged Doob-equilibrated fallbacks; `44.28` regret vs. `43.82` exact full-portal), **beating `MatrixFree_SpectralSchur_PAC` in both lifecycle LU RHS (`3,025.5` vs. `7,498.9`, `-59.7%`) and wall time (`7.28s` vs. `7.89s`, $p_{2s} = 0.0334$)**, and cutting LU RHS by `15.7%` and initial array memory by `35.2%` vs. pre-batched `Uncompressed_SpectralSchur_PAC` (`6.03s` at $n_\Gamma = 577$).
- **Zero-Fallback Continuous Surrogate Control (`Block E3`, `96 / 96` Policies, `0` Exact Chord Hits)**: Eliminating `v2`'s `42/96` `None -> u=0` witness-abort confound lifts start-localized **`SPQL` to `100.0%` goal success (`1.521` cost)** across all `7,680` rollouts, matching both `SPQL_UniformPortals` (`1.520`, $p_{2s} = 0.779$) and `Uncompressed_PAC` (`1.520`, $p_{2s} = 0.779$) while beating `Scalar_Portal_Ablation` (`6.801`, $p_{2s} = 4.47\times 10^{-5}$) and `SVD_Resolvent_Ablation` (`8.958`, $p_{2s} = 5.25\times 10^{-7}$) on `8/8` seeds.
