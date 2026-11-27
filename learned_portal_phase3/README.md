# Phase-III (`learned_portal_phase3`): PAC-Certified Spectral-Portal Quotient Learning (SPQL `v4` Contract-Verified)

This isolated package implements **PAC-Certified Spectral-Portal Quotient Learning (SPQL)** — learning bottleneck quotient Green operators **end-to-end from unknown-dynamics exploration trajectories** in finite-state LMDPs without spatial coordinates or occupancy-grid priors, organized into **four explicit guarantee tiers** (`Tier-1` exact M-matrix all-goal sandwich & posterior variational duality, `Tier-2` time-uniform predictable-sampling confidence sequences, `Tier-3` outward-rounded IEEE-754 stored-operator & delivered-`CSR` policy verification, and `Tier-4` empirical fitted Voronoi continuous surrogate control).

> **Strict Non-Destructive Archive Integrity**: Frozen Phase-I (`green_response/`, SHA-256 `271ac8df...`), Phase-II (`quotient_phase2/`, SHA-256 `e6ea565b...`, `m233_sisc_unlock_results.json` `339e723f...`, `m233_clean_isolation_replication.json` `73101638...`), Phase-III `v1` exploratory archive (`p3_neurips_benchmark_results.json`, SHA-256 `0e2c76ea...`), Phase-III `v2` archive (`p3_v2_verified_benchmark_results.json`, SHA-256 `6167bd5f...`), and Phase-III `v3` archive (`p3_v3_r747_delivery_verified_results.json`, SHA-256 `0ffd1d3a...`) are **100% byte-for-byte untouched** (`verified automatically in Gates P3-C10, P3-C18, & P3-C20`).

---

## Core Modules & Artifacts

| File | Description |
| :--- | :--- |
| `__init__.py` | SHA-256 byte-freeze guards (`verify_phase1_and_phase2_untouched`, `verify_phase3_v1/v2/v3_archive_untouched`) and Phase-III manifest (`a2bb98b4...`). |
| `spql_core.py` | Time-uniform Dual PAC M-matrix envelopes $(\underline{A}_n, \overline{A}_n)$, killed-portal Dirichlet reduction onto $E_\Gamma = \Gamma \setminus G$, strictly binary Fiedler PoU trees (`50.0%` LU conservation), outward-rounded IEEE-754 Higham verifiers (`2^{-1074}` subnormal guard, zero `1e-12` floors), log-space row-stochastic `CSR` policy construction + SHA-256 binding, and strictly separated native room-LU vs. global-fallback counters. |
| `baselines_and_contracts.py` | Matched Tier-3 PAC comparators & ablations (`PlugIn_CE_FullGraph` + `evaluate_posterior_pac_policy_upper_bound`, zero-waste `Uncompressed_SpectralSchur_PAC`, strictly-linear `MatrixFree_SpectralSchur_PAC`, `Scalar_L0_Portal_Ablation`, `TransitionSVD_Resolvent_Ablation`, `Sampled_Desirability_TD`) and the **20-gate deterministic counterexample suite (`P3-C01..P3-C20`)**. |
| `continuous_manifold_spql.py` | Zero-silent-fallback continuous Voronoi surrogate control (`raises ValueError if Pi_ext_csr is None`), damped (`0.85`), padded (`4e-4`), chord-guarded Euler simulator with exact Liang–Barsky chord checks across `96/96` goals, and `7` same-data controllers. |
| `run_phase3_r675_targeted_audit.py` | Single-threaded (`OMP/BLAS/MKL = 1`, `workers = 1`) `v4` audit runner (`seeds 4000..6007`), exporting all `1,952` per-task events (`512` E1 + `768` E2 + `672` E3), 4-level error/bound decompositions, and E3 policy-fingerprint verification. |
| `p3_v4_r675_verified_results.json` | Primary `v4` contract-verified ledger (`SHA-256: 798a9e2b...`, `20/20` gates, `0` zero-slack PAC violations, `1,952` saved events). |
| `p3_v4_fig1_rotated_pac_and_decomposition.png` | 3-panel `v4` figure: $37^\circ$-rotated 9-room Cap-80 curve, `240k` uncapped vs. Cap-80 regret, and 3D 4-level cost decomposition. |
| `p3_v4_fig2_3d_linear_mf_and_continuous.png` | 2-panel `v4` figure: 3D cave lifecycle (`strictly linear MatrixFree & separated native LU`) and zero-silent-fallback continuous surrogate control (`96/96` policies). |
| `p3_v3_r747_delivery_verified_results.json` | Byte-frozen `v3` archive (`SHA-256: 0ffd1d3a...`, preserved untouched). |
| `p3_v2_verified_benchmark_results.json` | Byte-frozen `v2` archive (`SHA-256: 6167bd5f...`, preserved untouched). |
| `p3_neurips_benchmark_results.json` | Byte-frozen `v1` exploratory archive (`SHA-256: 0e2c76ea...`, preserved untouched). |
| `NEURIPS_MANUSCRIPT_DRAFT.md` | Full `v4` contract-verified manuscript draft (`Infante et al. 2022 positioning`, `Propositions 1–5`, `Theorems 1–4`, 4-level decomposition, and complete proofs). |

---

## Reproducible Single-Threaded Execution Commands

1. **Fast 20-Gate Mathematical & Outward IEEE-754 Counterexample Suite (`~11.8s`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     PYTHONPATH=. /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_r675_targeted_audit --gates-only
   ```

2. **Full `v4` Targeted Audit Suite & Figure Generation (`workers = 1`, `~13.0 min`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
     PYTHONPATH=. /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_r675_targeted_audit
   ```

---

## Headline Verified `v4` Summary (`p3_v4_r675_verified_results.json`, `798a9e2b...`)

- **20/20 Deterministic Contract Gates Passed (`P3-C01..P3-C20` in `11.77s`)**: Closes all `R675` IEEE-754 gradual-underflow (`2^{-1074}`), `q_min ~ 1e-15` unit-equivariance, `1e-310` log-scaled `CSR` policy normalization + SHA-256 binding (`P3-C19`), strictly linear `MatrixFree` matvec (`oddness_err = 0.0`), and native-LU accounting (`P3-C20`) probes.
- **Same-Data 4-Level Decomposition & Active Exploration (`E1 240k` & `E2 460k`)**: Certifying `PlugIn_CE` post-hoc inflates worst-case upper bounds by $2.35\times$ in 2D (`159.36` vs. `67.73`) and $4.46\times$ in 3D (`973.30` vs. `218.44`), proving empirically and variationally (`100%` of tasks) why pessimistic planning trades higher empirical cost (`+8.44` in 2D, `+26.28` in 3D) for dramatically tighter worst-case bounds, while portal coarsening adds `0.00%` loss in 2D (`24.905` vs. `24.907`) and `+0.466` (`+0.74%`, $p_{2s} = 0.00255$) at `16.7%` active DOFs in 3D. At `240k` (`512` saved events), `SPQL_Active` beats `SPQL_Passive` on `8/8` seeds in both uncapped/cap-80 regret (`7.81` vs. `10.63`, $p_{2s} = 8.48\times 10^{-6}$) and width (`47.44` vs. `69.18`, $p_{2s} = 9.28\times 10^{-7}$).
- **3D Curved Caves (`Block E2`, `768` Saved Events)**: `SPQL` delivers `192/192` certified proper policies (`0` zero-slack PAC violations), cutting native room-LU RHS by **`68.7%` (`2,756.8` + `1.5` global fallbacks vs. `8,798.8`)** and bounds-only query time by **`34.2%`** against strictly-linear `MatrixFree_SpectralSchur_PAC` (`-3.47%` full lifecycle time, paired-$t$ $p_{2s} = 0.0392$, sign-flip $p_{2s} = 0.0625$), while using `17.7%` fewer native room-LU RHS and `35.2%` less initial array memory (`55.71` vs. `85.97 MB`; `100.09 MB` post-24q) than pre-batched `Uncompressed_SpectralSchur_PAC` (`which runs 7.09% faster / SPQL +7.63% slower at n_Gamma = 577`).
- **Continuous Surrogate Control (`Block E3`, `672` Fingerprint-Verified Policies, `0` Silent Control Fallbacks)**: All `672/672` `v4` policies match frozen `v3` within `8.77e-15 <= 1e-12` (`0` rollout re-simulations); `SPQL` (`89` coarse + `7` numerical fallbacks) attains **`100.0%` success (`1.521` cost, `0` chord wall crossings)**, with no significant cost difference vs. `Uncompressed_PAC` (`1.520`, $p_{2s} = 0.779$) and `8/8` seed wins over `Scalar_Portal` (`6.801`) and `SVD_Resolvent` (`8.958`).
