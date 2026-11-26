# `green_response`: Auditable Coarse-to-Fine Green Response Planning & Goal-Oriented World-Model Sensing

Canonical modular library and benchmark suite closing all findings across `7087ec3`, `85e2323`, `ddd19c5`, `d1b926a`, `29fa7c6`, and `57e5912` (`green_kriging_v5`). All active solvers, independent counterexample regression probes (`22` suites), replayable acquisition tapes, and reproducible benchmarks (`Experiments 1–4`) live in `green_response/`; historical snapshots (`green_kriging_mvp/`, `green_kriging_v2/`, `green_kriging_v3/`, `green_kriging_v4/`) remain frozen for provenance.

---

## 1. Module Architecture, Hardened Contracts, & Provenance Manifests

- `core.py`:
  - `ProblemSpec`: Enforces explicit LMDP capability guards (`validate_cole_hopf_lmdp`) at solver entry and constructs `as_isotropic_unconstrained_surrogate()` warm-starts.
  - `IntervalCertificate`: Machine-auditable fail-closed certificate contract (`__post_init__` validates allowed `status`, finite ordered `lower_bound <= upper_bound`, `gap <= epsilon_tol` on `"epsilon_certified"`, non-negative `operator_epoch`, explicit `certificate_kind` in `{"policy_and_value_enclosure", "value_only_enclosure"}`, strict `_validate_typed_policy_entry` rejecting `None`, empty `{}` / `()` / empty `ndarray`, and non-callables when `certified=True` unless `allow_value_only=True`, and blocks `extras` from overriding protected fields).
  - `compute_source_manifest` & `collect_runtime_metadata`: Embeds `git_head_sha`, `git_dirty_green_response`, `package_py_sha256`, and `per_file_sha256` across every result JSON alongside explicit per-block `"block_provenance"` and `"generating_commit"` tags (`"85e2323"`, `"ddd19c5"`, `"29fa7c6"`, `"57e5912"`).
  - `KrigingWorldModel`:
    - Smooth-branch ReLU chain-rule mask $\mathbf{1}[\mu_{q,\text{raw}}(X_{\text{grid}}) > 0]$ (`predict_q_raw_latent_mean`) and dual-channel `(q, b)` posterior cross-covariance projection (`_build_channel_posterior_cov_and_proj`, including exact block-Cholesky Schur conditioning on arbitrary off-grid `pending_X` coordinates, verified to `3.55e-15` in `Suite 22`).
    - `select_sequential_conditional_maxvar_probes`: Explicitly separates already-trained `existing_X` from not-yet-fitted `pending_X` (conditioning both `q` and optional `b` channels on `pending_X` before selecting sentinels, closing GPT6's pending-sentinel asymmetry).
    - `select_sequential_kg_voi_probes`: Supports clean $2 \times 2$ factorial toggles (`include_drift_sensitivity` $\times$ `condition_decision_probes`) while keeping `n_sentinel` `(q + 0.25 b)` sentinels conditioned on all `n_decision` pending probes. Explicitly distinguishes `"value_only_linear_functional_std"` (`max_alt_branches = 0`) from `"pairwise_local_linear_kg_proxy"` (sum-of-pairwise Gaussian opportunity proxy under frozen batch means/branches, not exact correlated joint multi-alternative KG).
  - `holm_bonferroni_adjust`: Step-down Holm–Bonferroni family-wise error rate adjustment.
- `port_solvers.py`:
  - `SchurPortPlanner`:
    - Unified string-keyed nested partition tree (`"L1" -> "L4" -> "L8" -> "EXACT"`) across 2D and 3D with per-column `operator_epoch` tagging.
    - **Continuous Reciprocal `log1p` Single-Query Enclosure**: Derives continuous $d \ge 0$ value bounds from
      $$0 < \frac{\widetilde{Z}(x) - d}{\gamma_{\text{hi}}} \le Z^*(x) \le \frac{\widetilde{Z}(x) + d}{\gamma_{\text{lo}}},$$
      yielding additive shifts on $\widetilde{V}(x) = -\lambda \log \widetilde{Z}(x)$:
      $$s_{\text{lo}}(x) = \lambda \log \gamma_{\text{lo}} - \lambda \operatorname{log1p}\!\left(\frac{d}{\widetilde{Z}(x)}\right), \qquad s_{\text{hi}}(x) = \lambda \log \gamma_{\text{hi}} - \lambda \operatorname{log1p}\!\left(-\frac{d}{\widetilde{Z}(x)}\right).$$
- `macro_planning.py`:
  - **Recommended Default Macro-Planner (`plan_exact_subset_dp`)**: Single-pass `ExactRing + Subset-DP` is the recommended cold-start default across 2D and 3D (`25^2..31^3`), whereas `plan_economical_hybrid` is scoped to warm micro-perturbation streams (`Suite 19`).
  - **Scatter-Add, True `max_alt_branches = 0`, & Zero-Drift Upwind Kink Contract (`compute_exact_macro_q_sensitivities`)**:
    - Accumulates transition weights via `np.add.at` on `eval_nodes` and `wp_rings` (`5.49e-10` vs central FD on `start_on_ring` & `overlapping_rings`, `Suite 20`).
    - Supports true `max_alt_branches = 0` (`n_alt = 0`), solving **zero extra runner-up transpose RHS columns** (`50%` reduction on 2-branch tasks) while reporting exact `runner_up_wp` and `action_gap` from `Q_root` (`0.0` discrepancy, `Suite 22`).
    - Separates Bellman action ties (`action_tie_detected`) from upwind operator sign kinks at exact `b == 0` (`upwind_drift_kink_detected`, `n_zero_drift_kink_components`), returning exact right/left directional slopes (`grad_b_plus_optimal`, `grad_b_minus_optimal`, matching half-ray Richardson FD to `3.79e-11..2.12e-10` in `Suite 22`) and either the Clarke generalized midpoint $\frac{1}{2}(g_{b,+} + g_{b,-})$ (`"clarke_midpoint"`) or a fail-closed `ValueError` (`"strict_smooth"`).
- `highd_solvers.py` & `exp3_highd_and_kinetic.py`:
  - `LOCKED_6D_METHOD_CONFIGS` & `execute_locked_6d_method`: Single canonical factory shared across quality, serial latency, and batch makespan entry points (`0.0` discrepancy verified against frozen `57e5912` records).

---

## 2. Explicit Claim-Scope & Evidence Grading Table

| Component / Claim | Claim Grade | Scope & Mathematical Guarantee | Empirical / Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Positive-Column M-Matrix Barrier & Continuous `log1p` Residual Enclosure** | **Model-Exact Theorem (`0` violations)** | Discrete M-matrix comparison bounds on $\Omega \setminus \Gamma_b$ + $L_\infty$ residual bound with continuous reciprocal `log1p` shift (`Suite 17`) | `0` violations across `54` sign/overlap probes, `32` signed barrier probes, `625`-node `d1_noop` + `40`-seed `L1/L4/L8` probes (`Suite 17`), `144` `75^2` tours, `160` crossover tasks, and `3,456` real-GP lifecycle task checks |
| **Subset-Macro DP & Cold-vs-Warm Routing (`plan_exact_subset_dp`)** | **Model-Scoped $\varepsilon$-Certified ($O(m^2 2^m)$)** | Certifies $F_{\text{lo}} \le F^* \le J^{\hat{\mu}} \le F_{\text{hi}}$ on learned discrete model; `ExactRing + Subset-DP` is cold-start default | `0 / 37,303` `m=9` 4-way table violations; `ExactRing` wins cold-start `31^3` (`18,691 ms` vs `21,269 ms` `Hybrid`, `p = 0.00438`) |
| **Continual Partition-Structure Memory vs. Residual Column Reuse (`Exp 4B` Stage B2)** | **Model-Exact Bound + `0 / 2 / 6` Warmup Attribution** | Mandatory `cols_retained` contract across `ZeroWarm0`, `PartialWarm2`, `BroadWarm6` under `+16` real world observations (`10250..10261`) | `Residual` retains `91.0` (`PartialWarm2`) & `198.2` (`BroadWarm6`) cached level-cols in 3D, yet still needs `1.0` post-update `splu`; **`Structure-Memory` beats `ExactRing` (`-193.4 ms, p = 1.75e-4`) & `Residual` (`p = 1.16e-4`) on warm 3D marginal (`K=12`)**, while tying `ExactRing` from zero (`p = 0.627`) |
| **2x2 Mechanism Factorial (`Exp 4C` Batch B, `32` Revealed Dev Maps)** | **Controlled Causal Mechanism Attribution** | Fixes pending-conditioned `(q + 0.25 b)` sentinels; crosses `q-only vs q+b` adjoint $\times$ `Uncond vs Cond` decision probes (`10300..10415`) | **Sequential conditioning main effect: `-0.150 +/- 0.067` (`p = 7.63e-5`)**; **drift-`b` adjoint main effect: `+0.005 +/- 0.023` (`p = 0.643`, null)**; `FactB` (`qOnly-Cond`, `9.460`) & `FactD` (`9.456`) beat `Global-CondMaxVar-qb` (`9.723`, `p = 1.19e-6`), isolating **conditioned `q`-value sensitivity** |
| **Locked Fresh Confirmation (`Exp 4C` Batch C, `64` Untouched Maps)** | **Pre-Declared Single-Candidate Confirmation** | `Green-ValueOnly-qb-Cond-11+3` (`max_alt_branches=0`), deferred post-Ep-6 evaluation, compact `exp4_acquisition_tapes.json` (`20300..20431`) | **Pooled `64` maps (`Ep 2–6`)**: beats `Global-CondMaxVar-qb` (`-0.234, p_holm = 9.03e-6`) & repaired `OnPolicy-11+CondSentinel-qb-3` (`-0.131, p_holm = 0.0056`), **not significant vs pure `True-OnPolicy-14` (`-0.056, p_holm = 0.147`; Standard `32`: `-0.002, p = 0.977`)**, while **beating all 3 baselines in Competing-Corridor (`32` maps: `p_holm = 1.22e-4, 0.0028, 0.0143`)** |
| **6D Helmholtz-Bessel Physics-Mean GP Prior (`Exp 3A/3B/3D`)** | **Supporting Analytical Collar Prior + `+5%` NI** | Exact $C^2$ even collar PDE residual ($R = r I$, unconstrained); locked `M1/M2/M3` pipelines (`57e5912`) | `M1_EndToEnd_Bessel24` passes `+5%` Lin-NI vs `M2` (`p_NI <= 0.0107`) & `M3` (`p_NI <= 0.0412`) at **`5.70x` / `14.92x` query-cold serial speedup** (`2.38x` / `5.09x` incl. shared `449.5 ms` world GP) |

---

## 3. Verification & Benchmark Summary (`22/22 ALL_PASSED: true`)

All linear-algebra and benchmark runs enforce single-thread BLAS/OpenMP execution per worker (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR = 1`). Every JSON artifact (`audit_closure_results.json`, `exp1_results.json`, `exp2_results.json`, `exp3_results.json`, `exp4_results.json`, `exp4_acquisition_tapes.json`) embeds synchronized `package_py_sha256 = "2b38a2d5d6c544e33f58640eafc2d7a15f45ce573d8423506ce56188b4692939"` and explicit `"generating_commit"` provenance tags on inherited blocks. All tables below are generated directly from the JSON artifacts.

### 3.1 Independent 22-Suite Audit Closure Regression (`verify_audit_closure.py`)
- **Suites 1–21**: Full enclosure, epoch, continuous `log1p`, typed `IntervalCertificate`, stale-`EXACT` work-descriptor, `np.add.at` duplicate-node scatter (`5.49e-10`), piecewise-reflected polyline hit (`tau = 0.0861`), rank-1 Schur covariance (`1.55e-15`), and single-step planner-object isolation (`0.0` probe diff) checks pass.
- **Suite 22 (`57e5912` v5 Closure)**:
  - Single-goal exact zero-drift counterexample: `action_tie_detected = False`, `upwind_drift_kink_detected = True` (`562` components), half-ray Richardson FD error **`3.79e-11`** (right), **`2.12e-10`** (left), **`9.12e-11`** (Clarke midpoint), **`6.92e-11`** (mixed-sign direction), and `"strict_smooth"` fails closed (`True`).
  - True `max_alt_branches = 0`: `0.0` gradient/gap discrepancy vs `max_alt_branches = 1` while cutting SuperLU transpose RHS columns from `52` to `26`.
  - Off-grid `pending_X` sentinel conditioning: selects candidate `2` on GPT6's 3-candidate SPD counterexample and matches full augmented Cholesky on off-grid points to **`3.55e-15`** (`cov` & `proj`).
  - Mandatory `cols_retained` positive control: retains `1 >= 1` cached column on no-op update.

---

### 3.2 Experiments 1 & 2 (Frozen Supporting Provenance Blocks)
- **Exp 1A (`ddd19c5`)**: On `9400..9407` (`25^3`, `K = 40`), `SchurPort-r1-LumpedHaz-25` (`2,078.6 ms`, `+3.5%` Lin-NI `p = 3.5e-4`) is `14.86x` faster than `Fresh-FD-25` (`30,888 ms`) and `1.42x` faster than matched `Warm-ILU-LumpedHaz` (`2,957 ms`, `p = 0.0218`).
- **Exp 1B (`29fa7c6`)**: `0` bound violations across `144` `75^2` tours, `96` `m = 5..9` tasks, and `160` fixed-geometry crossover tasks; `ExactRing + Subset-DP` wins cold-start `31^3` (`18,691.1 ms` vs `DecisionGuided` `19,895.0 ms, p = 0.0703` & `Hybrid` `21,268.5 ms, p = 0.00438`).
- **Exp 2 (`85e2323`)**: `0 / 800` KKT tolerance misses (`<= 9.81e-9`); `1.28x` equal-tolerance speedup and `1.98x–2.02x` 3-step speedup passing `+0.5%` NI (`p_NI <= 0.0010`).

---

### 3.3 Experiment 3: High-D Physics-Mean Priors & Locked `method_config_id` Table (`exp3_results.json`, `generating_commit = "57e5912"`)
- **3D (`25^3`) Exact FD Teacher (`9700..9707`)**: `HelmholtzBessel` beats `MatchedSharpCone` on value RMSE (`-0.0824, p = 2.0e-6`) and policy RMSE (`-0.0505, p = 3.4e-5`); closed-loop differences at `n = 8` are non-significant (`p = 0.258 / 0.136`).
- **6D Bessel-Free Cone-Girsanov Teacher (`9608..9615`, `d1b926a` cohort re-intervention)**: `survivor_frac = 0.388`, `weighted_tail_mass = 0.00225`, `mean_ess = 17.31`, `min_ess = 1.31`; `HelmholtzBessel` beats `MatchedSharpCone` (`-1.385, p = 9.63e-4` unseen; `-0.957, p = 0.00507` shift).
- **Locked `method_config_id` 6D Quality–Cost Table (`8` Maps `9608..9615`, `100` physical observations, shared `mean_serial_world_gp_fit_ms = 449.5 ms`, `4.07x` [`5,148 / 1,266`] internal FK path ratio; ordinary superiority tests `p = 0.18..0.39` non-significant, supporting `+5%` expected-cost non-inferiority rather than superiority)**:

| Locked `method_config_id` | GP Rows / FK Paths / Per-Ch `q,b` Evals | Weighted Tail / Mean ESS | Closed-Loop Unseen / Shift (Reach) | `+5%` Lin-NI (`M1` vs Ref) | Query-Cold Serial (`1`-Worker) | Arithmetic `WorldGP + Query` | `8`-Worker `8`-Map Batch Makespan |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`M1_EndToEnd_Bessel24`** | `154.4` / `1266` / `22647` | `0.00078` / `23.84` | `4.374` / `5.297` (`100.0%` / `100.0%`) | — | **`187.1 ms`** (`1.00x`) | `636.7 ms` (`1.00x`) | **`914.8 ms`** (`8.74 q/s`) |
| `M2_FrozenBesselTeacher_SharpCone108` | `235.2` / `5148` / `93632` | `0.00006` / `23.54` | `4.480` / `5.367` (`100.0%` / `100.0%`) | **`0.0107` / `0.0015`** | `1067.4 ms` (`5.70x`) | `1516.9 ms` (`2.38x`) | `2583.1 ms` (`3.10 q/s`) |
| `M3_EndToEnd_IndepConeGirsanov_SharpCone108` | `235.2` / `5148` / `262091` | `0.00223` / `4.45` | `4.589` / `5.492` (`100.0%` / `99.6%`) | **`0.0166` / `0.0412`** | `2791.8 ms` (`14.92x`) | `3241.3 ms` (`5.09x`) | `6639.1 ms` (`1.20 q/s`) |

---

### 3.4 Experiment 4: Fidelity Bridge, Genuine GP Lifecycle, `2x2` Mechanism Factorial, & `64`-Map Fresh Confirmation (`exp4_results.json`)

#### Exp 4A — Coupled-Wiener Fidelity Bridge (`72` Tours on `9900..9911`, `generating_commit = "29fa7c6"`)
- `0 / 72` bound violations, `100%` root-action agreement; mean `|ΔJ|`: `L1` port (`0.0056`) << `L2c` `dt=0.005` piecewise-reflected polyline hit (`0.3432`, coupled `dt` effect `-0.2687, p < 1e-6`) < `L3` True-world vs GP mismatch (`0.8598`).

#### Exp 4B — Genuine `+16` Physical-Probe GP Refit Lifecycle (`12` Maps `10250..10261`, `ZeroWarm0 / PartialWarm2 / BroadWarm6`, Fresh Run)
- Appends `+16` real `(q, b)` observations (`64 -> 80` in 2D, `80 -> 96` in 3D) and refits Kriging posteriors across `0`, `2`, and `6` warmup tasks on a fixed `12`-WP catalog (`0 / 3,456` bound violations across all maps/methods/tasks).
- **Retained-Column Correction**: With mandatory `u_inf["cols_retained"]`, `Residual-Audited-Reuse` retains **`7.8` / `15.3` cached level-columns in 2D (`PartialWarm2 / BroadWarm6`)** and **`91.0` / `198.2` cached level-columns in 3D (`PartialWarm2 / BroadWarm6`)** (withdrawing the prior `0.0` key-typo report), while still requiring `1.0` post-update `splu` for unretained columns:

| Regime (`N_warm` Tasks, `K = 12`) | Scope | `Scratch-Rebuild` | `Structure-Memory-Fresh-Exact` | `Residual-Audited-Reuse` | `ExactRing-Rebuild` | Native Retained Level-Cols (`Resid`) | Key Paired Contrast (`K = 12`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `2D-61sq-ZeroWarm0` (`0`) | Post-Update Marginal | `483.7 ms` | `475.1 ms` | `486.9 ms` | **`220.4 ms`** | `0.0` | `Struct - Exact`: `+254.8 +/- 17.7 ms` (`p=3.62e-12`); `Resid - Struct`: `p=0.2774` |
| `2D-61sq-PartialWarm2` (`2`) | Post-Update Marginal | `475.1 ms` | `388.0 ms` | `391.6 ms` | **`213.5 ms`** | `7.8` | `Struct - Exact`: `+174.6 +/- 13.2 ms` (`p=9.56e-12`); `Resid - Struct`: `p=0.4577` |
| `2D-61sq-BroadWarm6` (`6`) | Post-Update Marginal | `472.1 ms` | `285.7 ms` | `280.5 ms` | **`204.6 ms`** | `15.3` | `Struct - Exact`: `+81.1 +/- 12.2 ms` (`p=1.51e-08`); `Resid - Struct`: `p=0.3695` |
| `3D-21cubed-ZeroWarm0` (`0`) | Post-Update Marginal | `1605.7 ms` | `1586.8 ms` | `1525.4 ms` | **`1333.1 ms`** | `0.0` | `Struct - Exact`: `+253.7 +/- 45.6 ms` (`p=9.37e-08`); `Resid - Struct`: `p=0.1303` |
| `3D-21cubed-PartialWarm2` (`2`) | Post-Update Marginal | `1661.6 ms` | `1500.9 ms` | `1592.3 ms` | **`1453.3 ms`** | `91.0` | `Struct - Exact`: `+47.6 +/- 119.5 ms` (`p=0.3997`); `Resid - Struct`: `p=0.1240` |
| **`3D-21cubed-BroadWarm6` (`6`)** | **Post-Update Marginal** | `1553.5 ms` | **`1111.7 ms`** | `1375.2 ms` | `1305.1 ms` | `198.2` | **`Struct - Exact`: `-193.4 +/- 76.8 ms` (`p=0.0002`); `Resid - Struct`: `p=0.0001`** |
| `3D-21cubed-BroadWarm6` (`6`) | From-Zero Full Lifecycle | `3024.1 ms` | `2544.3 ms` | `2890.4 ms` | `2580.8 ms` | `198.2` | `Struct - Exact` (from zero): `-36.4 +/- 160.3 ms` (`p=0.6269`, tied) |

  - Note: At `K = 1` in `3D-BroadWarm6`, `Residual` vs `ExactRing` is `+16.3 +/- 111.4 ms` (`p = 0.754`, non-significant). Thus `ExactRing + Subset-DP` remains the cold-start default, `Structure-Memory-Fresh-Exact` wins marginal post-update streams when a broad 3D cache is already warm, and `Residual-Audited-Reuse` is retained strictly as an optional mechanism.

#### Exp 4C Batch B — Development `2 x 2` Mechanism Factorial (`32` Revealed Maps `10300..10415`, Chronologically Deferred Evaluation)
- Evaluates `q-only vs q+b` Green value sensitivity $\times$ `Unconditioned vs Sequentially Conditioned` decision probes (`max_alt_branches = 0`), holding pending-conditioned `(q + 0.25 b)` sentinels strictly fixed across all 4 factorial arms, alongside `Global-CondMaxVar-qb-14`, repaired `True-OnPolicy-11+CondSentinel-qb-3` (with off-grid `pending_X` conditioning), and `True-OnPolicy-14` (`0.0` Ep-1 spread, `0` exact zero-drift kinks observed across all episodes; `Sim(excl)` reports online SDE rollout simulation time excluded from algorithm timers):

| Arm (`32` Dev Maps `10300..10415`, Deferred Eval) | Standard `16` (`Ep 2–6`) | Competing `16` (`Ep 2–6`) | Pooled `32` (`Ep 2–6`) | Pooled `FactD - Arm` (`95% CI`, `p`) | Acq / Operational / Sim(excl) ms |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Global-CondMaxVar-qb-14` | `11.159` | `8.287` | `9.723` | **`-0.267 +/- 0.091`** (`p=1.19e-06`) | `386.8` / `1532.8` / `1854.0` |
| `True-OnPolicy-14` | `11.098` | `8.121` | `9.609` | **`-0.153 +/- 0.109`** (`p=0.0075`) | `324.1` / `1454.8` / `1906.1` |
| `True-OnPolicy-11+CondSentinel-qb-3` | `11.188` | `8.183` | `9.686` | **`-0.230 +/- 0.111`** (`p=0.0002`) | `415.4` / `1559.7` / `1967.5` |
| `FactA-GreenVal-qOnly-Uncond` | `11.069` | `8.132` | `9.601` | `-0.145 +/- 0.066` (`p=9.19e-05`) | `791.5` / `1890.2` / `1797.3` |
| **`FactB-GreenVal-qOnly-Cond`** | `10.931` | **`7.988`** | **`9.460`** | `-0.004 +/- 0.035` (`p=0.8295`) | `820.9` / `1962.5` / `1904.0` |
| `FactC-GreenVal-qb-Uncond` | `11.068` | `8.162` | `9.615` | `-0.159 +/- 0.073` (`p=0.0001`) | `1194.0` / `2319.8` / `1867.7` |
| **`FactD-GreenVal-qb-Cond`** | **`10.900`** | `8.012` | **`9.456`** | — | `1159.7` / `2261.3` / `1871.3` |

- **Exact `2 x 2` Factorial Attribution**:
  1. **Main effect of sequential Schur conditioning (`0.5 * [(B - A) + (D - C)]`)**: **`-0.150 +/- 0.067` (`p = 7.63e-5`)** (`B - A = -0.141, p = 1.47e-4`; `D - C = -0.159, p = 1.09e-4`). Without conditioning (`FactA = 9.601`, `FactC = 9.615`), Green ties `True-OnPolicy-14` (`9.609`), explaining v3's tie from first principles!
  2. **Main effect of drift-`b` adjoint (`0.5 * [(C - A) + (D - B)]`)**: **`+0.005 +/- 0.023` (`p = 0.643`, null)**, interaction **`-0.018 +/- 0.039` (`p = 0.353`, null)**, and `Global-CondMaxVar-qb-14` (`9.723`) performs worst among active arms—proving the gain comes from **sequentially conditioned `q`-channel task-response sensitivity** rather than drift-`b` sensitivities or global `(q, b)` variance!

#### Exp 4C Batch C — Single Locked Fresh Confirmation on `64` Untouched Maps (`20300..20331` Standard + `20400..20431` Competing-Corridor, Chronologically Deferred Evaluation)
- Evaluates the single pre-declared candidate `Green-ValueOnly-qb-Cond-11+3` (`max_alt_branches = 0`) once on `64` untouched maps (`0.0` Ep-1 spread, `100%` tour completion, `0` zero-drift kinks, full replayable coordinate/observation/index tapes saved in `exp4_acquisition_tapes.json`, SHA-256 `956b048b55f6bddb...`):

| Arm (`64` Untouched Maps `20300..20431`, Deferred Eval) | Standard `32` (`Ep 2–6`) | Competing `32` (`Ep 2–6`) | Pooled `64` (`Ep 2–6`) | Pooled `GreenVal - Arm` (`95% CI`) | `p_nom` / `p_holm` (`3`-Ref Family) | Acq / Operational / Sim(excl) / Eval ms |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Frozen-GP-28` | `11.942` | `8.707` | `10.325` | `-1.209 +/- 0.241` | `1.05e-14` (anchor) | `0.0` / `376.6` / `1890.2` / `773.3` |
| `Global-CondMaxVar-qb-14` | `10.526` | `8.172` | `9.349` | **`-0.234 +/- 0.091`** | `3.01e-06` / **`9.03e-06`** | `395.5` / `1618.6` / `2045.1` / `4765.9` |
| `True-OnPolicy-11+CondSentinel-qb-3` | `10.453` | `8.041` | `9.247` | **`-0.131 +/- 0.084`** | `0.0028` / **`0.0056`** | `448.0` / `1707.4` / `2163.6` / `4733.1` |
| `True-OnPolicy-14` | `10.340` | `8.002` | `9.171` | `-0.056 +/- 0.076` | `0.1470` / **`0.1470`** | `331.9` / `1543.6` / `2072.6` / `4606.3` |
| **`Green-ValueOnly-qb-Cond-11+3`** | **`10.338`** | **`7.892`** | **`9.115`** | — | — | `1222.9` / `2452.9` / `2061.5` / `4809.9` |

- **Balanced Confirmatory Findings & Regime Boundary**:
  1. **Pooled `64`-Map Primary Endpoint (`Ep 2–6`)**: Under equal coordinate-oracle budgets (`28 -> 98` physical probes), `Green-ValueOnly-qb-Cond-11+3` **significantly beats `Global-CondMaxVar-qb-14` (`p_holm = 9.03e-6`; `32`-pair `p_holm = 8.36e-5`) and equal-quota `True-OnPolicy-11+CondSentinel-qb-3` (`p_holm = 0.0056`; `32`-pair `p_holm = 0.0082`)**, but is **not statistically significant against pure `True-OnPolicy-14` on pooled `Ep 2–6` mean (`-0.056 +/- 0.076, p_holm = 0.147`)**, separating from `True-OnPolicy-14` primarily at the final `98`-probe checkpoint (`Ep 6`: `-0.108 +/- 0.080, p_nom = 0.0092`, exploratory).
  2. **Sharp Regime Dichotomy (`Standard-32` vs `Competing-Corridor-32`)**:
     - **Standard Narrow-Barrier (`32` maps `20300..20331`)**: `Green` (`10.338`) beats `Global-CondMaxVar-qb-14` (`10.526`, `p_holm = 0.0346`) **but ties pure `True-OnPolicy-14` (`10.340`, `-0.002 +/- 0.127, p = 0.977`)**, because when a single corridor dominates, realized on-policy trajectories already sample that corridor densely while global sentinels dilute early-episode corridor focus (`OnPolicy-11+CondSent-3 = 10.453`).
     - **Competing-Corridor Bifurcation (`32` maps `20400..20431`)**: **`Green-ValueOnly-qb-Cond-11+3` (`7.892`) beats ALL THREE external baselines after Holm–Bonferroni correction**: vs `Global-CondMaxVar-qb-14` (`-0.280 +/- 0.120, p_holm = 0.000122`), vs `True-OnPolicy-11+CondSentinel-qb-3` (`-0.148 +/- 0.086, p_holm = 0.00279`), and **vs pure `True-OnPolicy-14` (`-0.110 +/- 0.086, p_holm = 0.0143`)**—demonstrating that goal-oriented Green response sensing adds clear value specifically when competing passages create exploration lock-in for on-policy rollouts, at `1.59x` higher recorded operational compute (`2,452.9` vs `1,543.6 ms`) under coordinate-oracle access.

---

## 4. Reproducible Execution Commands

```bash
# 1. Run all 22 independent audit & counterexample suites (single-threaded)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/verify_audit_closure.py

# 2. Run Experiments 1–4 (8-core map-parallel with per-worker single-thread BLAS pinning)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp1_3d_and_macro_tours.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp2_nonlmdp_kkt.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp3_highd_and_kinetic.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp4_fidelity_and_continual.py
```
