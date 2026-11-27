# Phase-III (`learned_portal_phase3`): PAC-Certified Spectral-Portal Quotient Learning (SPQL v2)

This isolated package implements **PAC-Certified Spectral-Portal Quotient Learning (SPQL)** — learning decision-sufficient bottleneck quotient Green operators **end-to-end from unknown-dynamics exploration trajectories** without spatial coordinates or occupancy-grid priors, backed by **time-uniform predictable-sampling confidence sequences** and **exact all-goal four-inequality PAC regret certificates** across all $2^N - 1$ unseen goals (including goals intersecting discovered portals).

> **Strict Non-Destructive Archive Integrity**: Frozen Phase-I (`green_response/`, SHA-256 `271ac8df...`), Phase-II (`quotient_phase2/`, SHA-256 `e6ea565b...`, including `m233_sisc_unlock_results.json` `339e723f...`), and the Phase-III `v1` exploratory archive (`p3_neurips_benchmark_results.json`, SHA-256 `0e2c76ea...`) are **100% byte-for-byte untouched** (`verified automatically in Gate P3-C10`).

---

## Core Modules & Artifacts

| File | Description |
| :--- | :--- |
| `__init__.py` | SHA-256 byte-freeze guard (`verify_phase1_and_phase2_untouched`) and Phase-III package manifest generator (`ef37a7b3...`). |
| `spql_core.py` | Time-uniform Dual Clopper–Pearson / predictable-Hoeffding M-matrix envelopes $(\underline{A}_n, \overline{A}_n)$ (`zero 1e-15 upward floor`), exact killed-portal Dirichlet reduction onto $E_\Gamma = \Gamma \setminus G$ + straddling-block splitting (`all 2^N - 1 goals`), strictly binary Fiedler PoU trees (`max_children = 2`, exact `50.0%` LU conservation), relative coarse stopping, and predictable portal-directed active exploration. |
| `baselines_and_contracts.py` | Honest mechanism ablations & same-data controls (`PlugIn_CE_FullGraph`, `Uncompressed_SpectralSchur_PAC`, `MatrixFree_SpectralSchur_PAC`, `Scalar_L0_Portal_Ablation`, `TransitionSVD_Resolvent_Ablation`, `Sampled_Desirability_TD`) and the **16-gate deterministic mathematical & counterexample suite (`P3-C01..P3-C16`)**. |
| `continuous_manifold_spql.py` | Zero-tunneling continuous $35^\circ$-rotated stochastic diffusion control (`exact multi-wall bounce segment intersection`, `u_t = 0` passive exploration, online Voronoi quotienting, and 6-method same-data HJB exit-direction feedback controls). |
| `run_phase3_v2_verified_suite.py` | Single-threaded (`OMP/BLAS/MKL = 1`, `workers = 1`) held-out `v2` benchmark runner (`seeds 4000..4007, 5000..5007, 6000..6007`), saving all `3,648` per-task events, 300-DPI figures, and strict RFC-8259 JSON provenance. |
| `p3_v2_verified_benchmark_results.json` | Protocol-verified held-out `v2` benchmark ledger (`SHA-256: 6167bd5f...`, `3,648` events, `0` PAC violations, `0` wall-tunneling segments). |
| `p3_neurips_benchmark_results.json` | Byte-frozen `v1` exploratory benchmark archive (`SHA-256: 0e2c76ea...`, preserved untouched for audit traceability). |
| `p3_v2_fig1_rotated_pac_and_active.png` | 4-panel `v2` figure: $37^\circ$-rotated unrestricted-goal PAC validity, active vs. passive finite enclosure & width contraction, and structural counterexamples. |
| `p3_v2_fig2_3d_lifecycle_and_continuous.png` | 4-panel `v2` figure: 3D curved-cave unified LU/memory/wall-time tradeoffs (`4`-arm cyclic schedule) and zero-tunneling 6-control continuous diffusion evaluation. |
| `NEURIPS_MANUSCRIPT_DRAFT.md` | Full protocol-verified `v2` paper draft (`Propositions 1–4`, `Theorems 1–4`, honest scope & boundary disclosures, and complete mathematical proofs in Appendix A). |

---

## Reproducible Single-Threaded Execution Commands

1. **Fast 16-Gate Mathematical & Counterexample Audit (`~3.5s`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_v2_verified_suite --contracts-only
   ```

2. **Full Held-Out `v2` Multi-Seed Benchmark & Figure Generation (`workers = 1`, `~8.4 min`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
     /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_v2_verified_suite
   ```

3. **Fast Figure Re-Render from Verified `v2` JSON (`~2s`)**:
   ```bash
   /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_v2_verified_suite --replot-from-json
   ```

---

## Headline Verified `v2` Summary (`p3_v2_verified_benchmark_results.json`, `6167bd5f...`)

- **16/16 Deterministic Contract Gates Passed (`P3-C01..P3-C16` in `3.54s`)**: Exhaustive all-15-goal-subset 4-state verification (`P3-C11`), 392-state portal-goal `236` exact 4-inequality verification (`P3-C12`), 2-look exact (`2.87e-7 <= 0.00625`) & 29-look dyadic optional-stopping verification (`P3-C13`), boundary-unbiased cost-noise soundness (`P3-C14`), zero continuous wall tunneling (`P3-C15`), and cancellation-free `1e-12` proper-policy evaluation (`P3-C16`).
- **Zero-Violation Unrestricted-Goal PAC Coverage (`Block E1`, `37°`-Rotated 9-Room Worlds)**: **`0 / 768` PAC violations** across `SPQL_Passive` & `SPQL_Active` (including `119` portal-intersecting goal evaluations), vs. **`73.4%–98.4%` optimism violations** for `PlugIn_CE_FullGraph`. At `240k`, `SPQL_Active` achieves **`95.31%` finite four-inequality certification** (vs. `82.03%` passive) and narrows certified width by **`-18.94`** ($p = 2.52\times 10^{-4}$).
- **3D Unstructured Curved Caves (`Block E2`, `~15,678` states, Unified Accounting)**: `0 / 192` PAC violations; activates **`10.98%` (`63.4 / 577.3`)** of portal DOFs, cutting **total lifecycle 3D room-LU backsolves by `37.5%` vs. `Uncompressed_SpectralSchur_PAC` (`1,941.9` vs. `3,108.4` RHS)** and **`34.9%` vs. `MatrixFree_SpectralSchur_PAC`**, and reducing initial resident array memory by **`35.2%`** (`55.71 MB` vs. `85.97 MB`), while honestly reporting that at moderate portal size $n_\Gamma \approx 577$, pre-batched `Uncompressed` (`2.65s`) and `MatrixFree` (`2.91s`) tie or slightly lead adaptive Python `SPQL` (`3.01s`, $p = 0.245$ vs. `MatrixFree`) in wall-clock time.
- **Zero-Tunneling Continuous `35°`-Rotated Diffusion Control (`Block E3`, `6` Same-Data Controls)**: **`0` wall-crossing segments** across `244,800` passive exploration steps and all policy rollouts. Full-portal **`Uncompressed_PAC` (`1.520`, `100.0%` success)** matches `PlugIn_CE` (`1.402`, `100.0%`) and `Sampled_Desirability_TD` (`1.577`, `99.1%`), whereas start-localized coarse `SPQL` (`4.746`, `62.1%` success) beats `Scalar_Portal_Ablation` (`6.801`, $p = 0.0378$) and `SVD_Resolvent_Ablation` (`8.958`, $p = 6.14\times 10^{-4}$) but sacrifices off-path continuous rollout feedback when pruning away from $s_0$.
