# `green_response`: Auditable Coarse-to-Fine Green Response Planning & Physics-Mean Value Distillation

Canonical modular library and benchmark suite closing all findings across the `v4` audit (`7087ec3`), `85e2323`, `ddd19c5` (`green_response_v2`), and `d1b926a` (`green_response_v3`). All active solvers, independent counterexample regression probes (`20` suites), and reproducible benchmarks (`Experiments 1–4`) live in `green_response/`; historical snapshots (`green_kriging_mvp/`, `green_kriging_v2/`, `green_kriging_v3/`, `green_kriging_v4/`) remain frozen for provenance.

---

## 1. Module Architecture, Audit-Hardened Contracts, & Provenance Manifests

- `core.py`:
  - `ProblemSpec`: Enforces explicit LMDP capability guards (`validate_cole_hopf_lmdp`) at solver entry and constructs `as_isotropic_unconstrained_surrogate()` warm-starts.
  - `IntervalCertificate`: Machine-auditable fail-closed certificate contract (`__post_init__` validates allowed `status`, finite ordered `lower_bound <= upper_bound`, `gap <= epsilon_tol` on `"epsilon_certified"`, non-negative `operator_epoch`, **mandatory non-null actionable policy reference on `certified=True`** unless `allow_value_only=True`, and blocks `extras` from overriding protected certificate fields).
  - `compute_source_manifest` & `collect_runtime_metadata`: Embeds `git_head_sha`, `git_dirty_green_response`, `package_py_sha256`, and `per_file_sha256` across every result JSON alongside explicit per-block `"block_provenance"` (`"fresh_computed_in_current_run"` vs. `"inherited_from_commit_..."`).
  - `run_map_parallel`: Map/seed-level `ProcessPoolExecutor` (`max_workers = 8`) with per-worker single-thread BLAS/OpenMP pinning (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR = 1`); single-process isolated latency checks (`max_workers = 1`) are reported separately where per-query wall-clock timing is interpreted.
  - `KrigingWorldModel`: Includes closed-form 1-step Gaussian posterior variance reduction `project_q_linear_functional_variance_reduction(cand_pts, grid_pts, weights_mat)` on linear functionals $\langle w_k, q(X_{\text{grid}})\rangle$.
  - `simulate_closed_loop_crn` & `_eval_reflected_step_goal_union_hit_tau`: Supports $t = 0$ ball absorption, hierarchical 3x Brownian coupling (`dW_pregenerated`), **exact piecewise-reflected polyline sphere-entry intersection** across specular box bounces $(2m - 1)L$ (eliminating both `false_chord_hit` and `missed_pre_reflection_hit`, explicitly scoped as piecewise-linear reflected path stopping rather than Brownian-bridge exit), optional `record_visited_states=True`, and causal sequential world probing (`observe_world_at_points`).
- `port_solvers.py`:
  - `SchurPortPlanner`:
    - Unified string-keyed nested partition tree (`"L1" -> "L4" -> "L8" -> "EXACT"`) across 2D and 3D with per-column `operator_epoch` tagging (`Bug 3.1` closure).
    - **Continuous Reciprocal `log1p` Single-Query Enclosure (`d1b926a P0` Closure)**: Replaces split `dz == 0` / `dz > 0` shift branches in `solve_query` with a single continuous $d \ge 0$ enclosure derived directly from $\gamma_{\text{lo}}(Z_{\text{raw}} - d) \le Z_{\text{exact}} \le \gamma_{\text{hi}}(Z_{\text{raw}} + d)$:
      $$s_{\text{lo}}(x) = \lambda \log \gamma_{\text{lo}} - \lambda \operatorname{log1p}\!\left(\frac{d}{\widetilde{Z}(x)}\right), \qquad s_{\text{hi}}(x) = \lambda \log \gamma_{\text{hi}} - \lambda \operatorname{log1p}\!\left(-\frac{d}{\widetilde{Z}(x)}\right),$$
      restoring exact continuity as $d \downarrow 0^+$ and eliminating reciprocal-inversion violations on multi-node / off-center / drifted rings (`0 / 625` on `d1_core_gamma_noop` and `0` across all `40` `L1/L4/L8` random seeds in `Suite 17`).
    - **Epoch-Aware Exact Work Descriptors (`d1b926a P1` Closure)**: `marginal_backsolves_to_refine(..., require_current_exact=None)` (defaulting `require_current_exact = (tgt == "EXACT")`) and `estimate_current_exact_route_work(target_wp_ids)` distinguish current-epoch exact columns from residual-valid stale-`EXACT` columns and report `requires_new_lu_factorization` explicitly.
- `macro_planning.py`:
  - **Gauge-Normalized Fail-Closed Macro Operators**: Factors terminal-cost sums $\Phi(S) = \sum_{b \in S} \phi_b$ out of backward DP; rejects float64 underflow (`zbar_raw <= 1e-285`) or non-finite inputs with `status="numeric_invalid", certified=False`.
  - **Incremental Subset-DP & Conservative Hybrid Router**: `_step_incremental_subset_macro_dp` updates only masks $S$ containing refined waypoints (matching scratch DP up to BLAS batch-width float64 rounding). `plan_economical_hybrid` uses `estimate_current_exact_route_work`, routes warm residual-valid tasks to incremental port DP without triggering unnecessary `splu` rebuilds (`Suite 19`), defaults to single-pass `plan_exact_subset_dp` whenever port savings are ambiguous, and includes `router_ms` inside `planning_ms`.
  - **Target-Permutation-Invariant Green-Adjoint Fréchet Sensitivities (`compute_exact_macro_q_sensitivities`)**: Canonicalizes `target_wp_ids` as `sorted(unique)` (`0.0` input-order sensitivity) and computes exact Reverse-Mode AD / SuperLU transpose gradients $\nabla_q F^*(s_0, S)$ and root action-gap sensitivity $\nabla_q (Q_{\text{runner-up}} - Q_{\text{incumbent}})$ in one batched $A_0^{-\top}$ solve (`max_err = 9.34e-10` vs. central FD in `Suite 20`).
- `highd_solvers.py`:
  - `BoxNeumannBesselBaseGuide` & `EikonalConeMeanGuide`: Analytical $C^2$ even-reflected collar Helmholtz/Bessel prior vs. `"matched_smooth_cone"` and `"matched_sharp_cone"` (`36`-point per-goal positive mode-weight NNLS).
  - `solve_highd_fk_distillation`: Supports **`teacher_mode="cone_girsanov_independent"`** (100% Bessel-free teacher using Cone-guided Girsanov Radon-Nikodym weights + Cone tail continuation) alongside `"bessel_guided"`, and separates physical world observations (`n_physical_world_observations = 100`) from posterior surrogate evaluations (`n_model_q_evals`, `n_model_b_evals`) and independent vs. antithetic FK streams (`mc_independent_streams_per_anchor = 24`, `mc_paths_per_anchor_effective = 48`).

---

## 2. Explicit Claim-Scope & Evidence Grading Table

| Component / Claim | Claim Grade | Scope & Mathematical Guarantee | Empirical / Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Positive-Column M-Matrix Barrier & Continuous `log1p` Residual Enclosure (`bound_harmonic_batch`, `solve_query`)** | **Model-Exact Theorem (`0` violations)** | Discrete M-matrix comparison bounds on $\Omega \setminus \Gamma_b$ + $L_\infty$ residual bound $(\lambda / q_{\min}) \|B - A_{\text{new}} U_{\text{old}}\|_\infty$ with continuous `log1p` shift (`Suite 17`) | `0` violations across `54` sign/overlap probes, `32` signed barrier probes, `625`-node `d1_noop` + `40`-seed `L1/L4/L8` multi-node post-update probes (`Suite 17`), `144` `75^2` tours, `96` `m=5..9` tasks, `160` crossover tasks, and `200` + `192` continual tasks |
| **Epoch-Consistent Incremental Subset-Macro DP & Hybrid Router (`plan_subset_macro_policy`, `plan_economical_hybrid`)** | **Model-Scoped $\varepsilon$-Certified ($O(m^2 2^m)$)** | Certifies $F_{\text{lo}} \le F^* \le J^{\hat{\mu}} \le F_{\text{hi}}$ on all non-empty `(row, mask)` entries; fail-closed policy & epoch guards (`Suites 16, 18, 19`) | `0 / 37,303` `m=9` 4-way table violations; `Exact` & `Hybrid` win in 2D (`19..165 ms`); `DecisionGuided` approaches `Exact` at `25^3–31^3` (`0.98x–0.94x`); `Hybrid` avoids `splu` (`0` new LUs) on warm micro-updates (`Suite 19`) |
| **Continual Partition-Structure Memory vs. Residual Column Reuse (`Exp 4B` & `4B-Crossover`)** | **Model-Exact Bound + Lifecycle Attribution** | Separates partition-structure memory (`Structure-Memory-Fresh-Exact`) from residual column reuse (`Residual-Audited-Reuse`) across cold/warm catalogs & 2D/3D scales | `0 / 200` (`4B`) & `0 / 192` (`4B-Cross`) violations (`Blind-Stale`: `92 / 200`); under realistic `+16` GP updates, **`Structure-Memory` beats `Scratch` (`1.31x–2.06x`) and beats `ExactRing-Rebuild` in warm `3D 21^3` (`798 vs 953 ms`, `p = 0.00048`)**, while `Residual-Audited` cuts `update_ms` `2.5x–11.3x` but defers `splu` unless updates are micro-scale |
| **Unconfounded Online GP Sensing & Held-Out Future Transfer (`Exp 4C`)** | **Causal Coordinate-Oracle Loop (`16` New Maps)** | Identical `ExactRing + Subset-DP` planner & `min_repel = 0.24` across all 5 arms; permutation-invariant Green-Fréchet sensitivity; disjoint held-out future tour bank | `0.0` Ep-1 spread; `100%` verified visited states on `True-OnPolicy`; **`Green-Frechet-Active` (`10.163`) significantly beats `Global-MaxVariance` (`10.491`, `-0.329, p = 0.0378`) and `Uniform-Random` (`10.444`, `-0.281, p = 0.0217`)**, while **statistically tying realized `True-OnPolicy-Trajectory` (`10.189`, `-0.026, p = 0.671`)** |
| **3D Single-Query Stream Reuse & Port Compression (`Exp 1A`)** | **Empirical + Linearized Relative NI** | Separates single-LU reuse, stride-2 local-hazard lumping, and `r=1/8` port compression across `K = 40` streams (`12` maps + `8` locked fresh maps) | `ExactRing` matches `FD-25` to `7.99e-15`; `SchurPort-r1-LumpedHaz` achieves **`16.19x`** (`12` maps) & **`14.86x`** (`8` fresh maps, `p = 8.0e-13`) vs. `FD-25` and **`1.42x` (`p = 0.0218`)** vs. matched `Warm-ILU-LumpedHaz` |
| **Non-LMDP Anisotropic Constrained KKT Warm-Start (`Exp 2`)** | **Supporting Exact Discrete HJB (`<= 1e-8`)** | Isotropic Cole-Hopf surrogate warm-start (`IsoFD` / `SchurPort`) for 2D anisotropic constrained policy iteration | `0 / 800` tol misses; `1.28x` equal-tol speedup (`1.031x` over `IsoFD`); `1.98x–2.02x` 3-step speedup passing `+0.5%` NI (`p_NI <= 0.0010`) |
| **3D/4D/6D Helmholtz-Bessel Physics-Mean GP Prior (`Exp 3A/3B/3D`)** | **Analytical Collar Identity + Independent Teachers** | Exact $C^2$ even collar PDE residual ($R = r I$, unconstrained) used as GP mean prior $m(x) = V_0(x)$; tested under **3D Exact FD** & **6D Bessel-Free Cone-Girsanov** teachers | Beats `NNLS-SharpCone` on **new `8` 6D maps `9608..9615`** (`-1.006, p = 2.67e-4` unseen; `+5%` NI vs `Cone-108` `p_NI <= 0.00227`, **`8.54x` isolated 1-worker speedup**), under **3D Exact FD teacher** (`val_rmse` `-0.082, p = 2.0e-6`), and under **6D Cone-Girsanov teacher** (`-1.385, p = 9.63e-4` unseen; `-0.957, p = 0.00507` shift) |
| **4D Kinetic Double-Integrator (`Exp 3C`)** | **Exploratory Empirical Extension** | Exact discrete path telescoping (`6.39e-14`), uncoupled velocity-cap & specular trace approximations | `92.5%` reach (`93.1%` held-out) vs. `70.6%` Pure-LQR & `28.3%` Kinetic-PIMC |

---

## 3. Verification & Benchmark Summary (`20/20 ALL_PASSED: true`)

All linear-algebra / benchmark runs enforce single-thread BLAS/OpenMP execution per worker (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR = 1`, verified via `threadpoolctl`). Multi-map throughput suites use `run_map_parallel(..., max_workers=8)`, while single-process per-query latency claims (`Exp 3D`) are measured in isolated `max_workers = 1` runs with randomized call order. Every JSON artifact embeds a synchronized `source_manifest` (`package_py_sha256`) and explicit per-block `"block_provenance"`.

### 3.1 Independent 20-Suite Audit Closure Regression (`verify_audit_closure.py`)
1–16. **Full `v4`, `85e2323`, & `ddd19c5` Regression**: `0 / 54` sign/overlap violations; `2.22e-16` 3D eager-vs-lazy invariance; `0 / 32` signed barrier violations; `t = 0` ball absorption & `m = 7` BnB (`4,974 / 5,040` pruned); `m = 8` Subset-Macro certified (`0.0` regret); `51^2` `6101/q6` KKT residual `5.65e-13`; classical reuse accounting; `R = 2 I` Bessel residual `1.48e-9`; continuous-disk HJB `1.02e-14`; kinetic telescoping `4.97e-14`; full `EXACT` dispatch `1.78e-15`; terminal-cost gauge shift ptp `1.42e-14`; zero-budget `numeric_invalid` & fail-closed intersections; scalar-$R$ centered PIMC drift ratio `[0.9992, 0.9997]`; `m = 9` `37,303`-entry 4-way table check (`0` violations); cross-waypoint operator-epoch contamination check (`0` violations).
17. **Continuous `log1p` Single-Query Post-Update Enclosure (`d1b926a P0` Closure)**: `0 / 81` violations on `dq = 1e-3`, `0 / 81` (`lu_skipped = True`) on `dq = 1e-5`, `0 / 81` with active local hazards, **`0 / 625` violations on GPT6's `d1_core_gamma_noop.py`** (`noop_shift_continuity_diff = 4.29e-11`), and **`0` violations across all `40` random multi-node `L1/L4/L8` seeds** (`d1_core_gamma_probe.py`).
18. **Fail-Closed Exact Baselines & Mandatory Policy Guard**: Rejects underflow (`q in {1e8..1e20}`), `phi = NaN`, forged `extras`, and **`certified=True` certificates missing a concrete policy reference**.
19. **Stale-`EXACT` Work-Descriptor & Hybrid Router Audit (`d1b926a P1` Closure)**: `estimate_current_exact_route_work` predicts `29 == 29` missing current-epoch exact backsolves and `requires_new_lu = True` (`observed = 1`); `plan_economical_hybrid` routes warm residual-valid tasks to `"incremental_decision_port_dp"` with **`0` new LU factorizations** and charges `router_ms` inside `planning_ms`.
20. **Green-Adjoint Fréchet Permutation Invariance & Piecewise-Reflected Hit Audit**: `compute_exact_macro_q_sensitivities` achieves **`0.0` target-permutation difference** on both `grad_q_optimal` and `grad_q_top_gap`, matches central FD across grid nodes to **`9.34e-10`**, and `_eval_reflected_step_goal_union_hit_tau` eliminates both `false_chord_hit` (`False`) and `missed_pre_reflection_hit` (`True`, `tau = 0.0861`).

---

### 3.2 Experiment 1: 3D Task-Stream Amortization & Unconfounded Macro-Tour Economics

#### Exp 1A — 3D `25^3` Full `K = 40` Stream (`12` Maps + `8` Locked Fresh Maps `9400..9407`, Inherited Block `ddd19c5`)
- `SingleLU-ExactRing-ExactHaz-25` matches `Fresh-FD-25` across all `480` benchmark queries to **`max |ΔV| = 7.99e-15`** and across all `320` fresh confirmation queries to **`1.07e-14`**.
- On `9400..9407` (`K = 40`), `SchurPort-r1-LumpedHaz-25` (`2,078.6 ms`, cost `3.540`, `+3.5%` Lin-NI `p = 3.5e-4` on held-out) is **`14.86x` faster than `Fresh-FD-25` (`30,888 ms`, `p = 8.0e-13`)**, **`1.38x` faster than `SingleLU-ExactRing-LumpedHaz` (`2,862 ms`, `p = 5.1e-7`)**, **`1.42x` faster than matched-operator `Warm-ILU-LumpedHaz` (`2,957 ms`, `p = 0.0218`)**, and `1.34x` faster in point mean than `Warm-ILU-ExactHaz` (`2,791 ms`, `p = 0.105`).

#### Exp 1B — `144` Official Tours, `m = 5..9` Full-Table Scaling, & Fixed-Geometry Crossover (`Fresh Run`)
- **Zero certified bound violations (`0`)** across all certified methods on all `144` `75^2` tours, all `96` `m = 5..9` `65^2` tasks (full 4-way `(row, mask)` table verified), and all `160` crossover tasks.
- **Official `144` Tours (`75^2`, `18` Maps x `8` Tours)**: `Full-ExactRing-SubsetDP` (`207.9 ms`, cost `10.194`) and updated `Hybrid-Economical-SubsetDP` (`201.0 ms`, cost `10.194`, `planning_ms` inclusive of `router_ms`) achieve `0.0` model regret, beating `Euclidean-Heuristic` (`10.845`) while `DecisionGuided-Port-SubsetDP` (`513.0 ms`, cost `10.201`, `0.00070` regret) cuts LU backsolves (`325.1` vs. `378.9`).
- **`65^2` Scaling `m = 5..9`**: `ExactRing + Subset-DP` (`127.1..172.9 ms`) and `Hybrid-Economical` (`126.0..164.5 ms`) dominate 2D wall-clock time; on `4` tasks/map in 2D, `Incremental-DP Decision-Port` (`324.0..1,353.7 ms`) and `Scratch-DP Decision-Port` (`314.0..1,317.5 ms`) are tied within ~3% because `col_solve_ms + occupancy_ms` and Python workspace bookkeeping balance mask-skipping at small refinement counts.
- **Unconfounded Fixed-Geometry Crossover (`8` Fresh Maps `9800..9807`, `m = 6`, `4` Tasks/Map, strictly fixed `r_wp = 0.28, eps_tol = 0.25`)**:

| Regime `[Grid DOF, Mean Ring Nodes]` | `Full-ExactRing + Subset-DP` | `UniformWidth Port + Subset-DP` | `DecisionGuided Port + Subset-DP` | `Hybrid-Economical Router` | `Decision` vs. `Exact` (`p`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Cheap-2D-25sq` `[625, ring ~ 9.4]` | `22.1 ms` | `219.2 ms` | `220.7 ms` | **`19.0 ms`** | `0.100x` (`p = 2.3e-9`) |
| `Fine-2D-65sq` `[4,225, ring ~ 28.6]` | `146.5 ms` | `369.5 ms` | `361.9 ms` | **`141.2 ms`** | `0.405x` (`p = 8.0e-9`) |
| `Coarse-3D-21cubed` `[9,261, ring ~ 18.6]` | `1,632.8 ms` | `1,857.1 ms` | `1,947.9 ms` | **`1,565.6 ms`** | `0.838x` (`p = 3.8e-4`) |
| `3D-Spherical-25cubed` `[15,625, ring ~ 29.5]` | `4,193.6 ms` | `4,265.9 ms` | `4,281.3 ms` | **`3,708.0 ms`** | `0.980x` (`p = 0.364`) |
| `Fine-3D-31cubed` `[29,791, ring ~ 50.1]` | **`18,691.1 ms`** | `18,778.6 ms` | `19,895.0 ms` | `21,268.5 ms` | `0.939x` (`p = 0.070`) |

---

### 3.3 Experiment 2: Non-LMDP Anisotropic Constrained KKT (`35^2` & `51^2` — Supporting Inherited Block `85e2323`)
- `0 / 800` tolerance misses (`<= 9.81e-9 <= 1e-8`); `SchurPort` achieves `1.28x` equal-tolerance speedup on `51^2` (`725.1 ms` vs. `926.5 ms` `Zero`, `1.031x` over `IsoFD`) and `1.98x–2.02x` 3-step speedup passing `+0.5%` Linearized NI (`p_NI <= 0.0010`).

---

### 3.4 Experiment 3: High-D Physics-Mean Priors, Split Confirmation, Independent Teachers, & Isolated Latency
- **Frozen-Label Prior Attribution (`Exp 3A/3B`, Inherited Block `ddd19c5`)**: On identical `(X_all, y_total_v)` labels, `HelmholtzBessel` beats `NNLS-Matched Sharp Cone` in 4D (`-0.166, p = 0.0101` unseen; `-0.447, p = 0.00169` shift) and 6D (`-0.126, p = 0.0121` unseen; `-0.301, p = 0.00285` all-8 / `-0.321, p = 0.0489` held-out-4 shift).
- **6D Anchor-Budget Efficiency & Explicit `8` Replication (`9600..9607`) vs. `8` New Confirmation (`9608..9615`) Split (`Exp 3B-Confirm`, Fresh Run)**:
  - Native counters explicitly separate **`n_physical_world_observations = 100.0`** (shared across all budgets) from posterior surrogate evaluations (`n_model_q_evals = 24,657 / 50,719 / 98,259`) and record `mc_independent_streams_per_anchor = 24.0` (`mc_paths_per_anchor_effective = 48.0`):

| Nominal `N` [Actual Int / GP Rows / FK Paths] | `ZeroMean` (Unseen / Shift) | `NNLS Sharp Cone` (Unseen / Shift) | `HelmholtzBessel` (Unseen / Shift) | All-16 `Bessel - Sharp` `p` | **New-8 (`9608..9615`) `Bessel - Sharp` (`p`)** |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **`N = 24` [`26.5` / `154.5` / `1,270.5`]** | `13.007` / `14.011` | `5.599` / `6.339` | **`4.643` / `5.346`** | `1.0e-6` / `1.0e-6` | **`-1.006` (`2.67e-4`) / `-1.191` (`2.75e-4`)** |
| `N = 54` [`55.7` / `183.7` / `2,674.5`] | `11.518` / `13.864` | `4.960` / `5.826` | `4.472` / `5.246` | `5.0e-6` / `1.0e-6` | `-0.479` (`0.00589`) / `-0.624` (`1.16e-4`) |
| `N = 108` [`108.3` / `236.3` / `5,197.5`] | `9.658` / `13.154` | `4.699` / `5.491` | **`4.435` / `5.158`** | `6.74e-4` / `4.10e-5` | `-0.239` (`0.00209`) / `-0.377` (`0.00168`) |

  - **Cross-Budget `+5%` Linearized NI (`Bessel-24` vs. `SharpCone-108`)**: Passes on **all `16` maps** (`p_NI = 1.98e-4` unseen, `1.10e-5` shift), on **`replication_8_maps_9600_9607`** (`p_NI = 0.00832` unseen, `0.00209` shift), **AND independently on `new_confirmation_8_maps_9608_9615`** (`p_NI = 0.00220` unseen, `0.00227` shift) using **`4.09x` fewer FK paths** (`1,270.5` vs. `5,197.5`).
  - **Fixed-Design Variance Algebra**: Because `MirrorNeumannMatern52GP` uses fixed kernel parameters under fixed anchor design $X$, $\Delta \nabla V(x)$ across `mc_seed` is an exact algebraic invariant of deterministic prior mean $m(x)$ (`0.018573` across all priors at `N = 24`), isolating `HelmholtzBessel`'s **`2.25x` lower full-reconstruction seed sensitivity** (`0.0934` vs. `0.2103`) to anchor-design interpolation/extrapolation stability.
- **Independent Non-Bessel Teachers & Isolated `1`-Worker Latency (`Exp 3D`, Fresh Run)**:
  1. **3D (`25^3`) Exact Deterministic FD Teacher (`8` Fresh Maps `9700..9707`, `0%` Bessel/FK in teacher labels)**: At `N = 24`, `HelmholtzBessel` achieves **`0.4173` value RMSE** vs. Exact FD (beating `MatchedSharpCone` `0.4997` by **`-0.0824 +/- 0.0136, p = 2.0e-6`** and `ZeroMean` `1.0210` by `-0.6038, p < 1e-6`) and **`0.5097` policy RMSE** (beating `MatchedSharpCone` `0.5602` by **`-0.0505 +/- 0.0128, p = 3.4e-5`**), with lower point closed-loop costs (`3.593` vs. `3.778` unseen, `p = 0.258`; `2.994` vs. `3.257` shift, `p = 0.136`).
  2. **6D Bessel-Free Cone-Girsanov Teacher (`8` Confirmation Maps `9608..9615`, `192` paths x `150` steps, `0%` Bessel guide in teacher)**: Even when training labels are generated by a pure **Cone-guided Girsanov teacher** (`survivor_frac = 0.388`), fitting the student GP at `N = 24` with **`HelmholtzBessel` (`4.402` unseen / `5.387` shift) decisively beats `MatchedSharpCone` (`5.788` / `6.344`)** by **`-1.385 +/- 0.602` (`p = 0.000963`)** on unseen starts and **`-0.957 +/- 0.563` (`p = 0.00507`)** on wall/corner shift starts, ruling out circular Bessel-teacher bias.
  3. **Isolated `1`-Worker Cold Query Latency (`9608..9613`, randomized order)**: `Bessel-24` takes **`199.3 ms`** vs. `Cone-108` **`1,701.8 ms`** (**`8.54x` isolated single-process speedup**, `-1,502.5 +/- 205.7 ms, p = 8.0e-6`; descriptive 8-worker throughput ratio: `3.60x`, `319.7` vs. `1,152.5 ms`).
- **Scoped 4D Kinetic (`Exp 3C`, Inherited Exploratory Block)**: Telescoping `<= 6.39e-14`; `92.5%` reach (`93.1%` held-out) vs. `70.6%` Pure-LQR & `28.3%` Kinetic-PIMC.

---

### 3.5 Experiment 4: Piecewise-Reflected Fidelity Bridge, Cache Warmth Crossover, & Unconfounded Online Learning (`Fresh Run`)

#### Exp 4A — Coupled-Wiener Fidelity Bridge (`72` Tours on `9900..9911`, Piecewise-Reflected Polyline Hit)
- `0 / 72` bound violations, **`100%` root-action agreement**, `0.00004` discrete model regret, `100%` completion (`0.0` timeouts/clips across all 7 arms).
- Mean `|ΔJ|` decomposition: `L1` port compression (`0.0056`) << `L2a` GP SDE `dt=0.015` endpoint (`0.5762`) -> `L2b` coupled `dt=0.005` endpoint (`0.3526`, **coupled `dt` effect `-0.2687 +/- 0.0290, p < 1e-6`**) -> `L2c` `dt=0.005` piecewise-reflected polyline hit (`0.3432`) < `L3` True-world vs. GP mismatch (`0.8598`, vs. rollout MC SE `0.2831`).
- **Continuous Policy Regret**: `DecisionGuidedPort` (`9.6011`) matches `ExactMacro` (`9.5993`, **`+0.0017 +/- 0.0040, p = 0.358`**) while beating `Euclidean` (`10.3628`) by **`-0.7617 +/- 0.4728` (`p = 0.00459`)**.

#### Exp 4B — Orthogonal Transition Stream (`200` Tasks on `9950..9959`) & `Warm vs. Cold` Crossover (`192` Tasks on `10200..10207`)
- **4-Epoch `61^2` Stream (`200` Tasks)**: `Blind-Stale-Cache` (`472.8 ms`) suffers **`92 / 200` (`46%`) certified bound violations**; `Structure-Memory-Fresh-Exact` (`686.0 ms`, `1.705x` vs. `Scratch` `1,169.6 ms`, `0 / 200` viols) and `Residual-Audited-Reuse` (`665.0 ms`, `1.759x` vs. `Scratch`, `update_ms = 50.9` vs. `201.9 ms`, `0 / 200` viols) are statistically tied end-to-end (`-21.0 +/- 42.0 ms, p = 0.288`).
- **2x2 Cache Warmth x Scale Full-Lifecycle Crossover (`8` Fresh Maps `10200..10207`, realistic `+16` GP probe transition, `6` post-update tasks/map, `0 / 192` bound violations)**:

| Regime (`+16` GP Obs, `K = 6` Tasks) | `Scratch-Rebuild` | `Structure-Memory-Fresh-Exact` | `Residual-Audited-Reuse` | `ExactRing-Rebuild` | Key Paired Finding (`update + solves + DP`) |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `2D-61sq-ColdPartial` | `332.3 ms` | `242.1 ms` | `242.4 ms` | **`101.2 ms`** | `ExactRing` fastest in 2D (`p = 2.0e-6`); `Reuse` ties `Structure` (`p = 0.94`) |
| `2D-61sq-WarmAll` | `228.5 ms` | `110.9 ms` | `115.4 ms` | **`67.1 ms`** | `ExactRing` fastest in 2D (`p = 7.5e-5`); `Reuse` ties `Structure` (`p = 0.53`) |
| `3D-21cubed-ColdPartial` | `1,385.0 ms` | **`1,190.5 ms`** | `1,206.3 ms` | `1,249.3 ms` | `Structure` & `Reuse` beat `Scratch` (`p = 0.0017`); tie `ExactRing` (`p = 0.39`) |
| **`3D-21cubed-WarmAll`** | `1,045.2 ms` | **`798.4 ms`** | `922.0 ms` | `952.6 ms` | **`Structure-Memory` beats BOTH `Scratch` (`-246.9 ms, p = 2.1e-5`) & `ExactRing` (`-154.2 ms, p = 4.8e-4`)!** |

- **Mechanistic Takeaway**: Under realistic `+16`-probe GP updates (`|\Delta q| \sim O(0.1)`), residual error bounds widen coarse intervals enough to trigger `1` deferred `splu` during `eps = 0.25` certification, so `Residual-Audited-Reuse` cuts upfront `update_ms` by **`2.5x–11.3x`** (`64.0 vs. 722.9 ms` in `3D-WarmAll`) but shifts that `splu` into `deferred_col_solve_ms` (`804.7 ms`); **partition-structure memory (`Structure-Memory-Fresh-Exact`) is the true driver of warm 3D continual speedups**, while residual value reuse yields net lifecycle wins specifically under micro-scale perturbations (`\Delta q \lesssim 10^{-4}`, `Suites 17 & 19`).

#### Exp 4C — Unconfounded 5-Arm Online GP Learning & Held-Out Future Transfer (`16` Brand-New Maps `10100..10115`)
- **Strict Protocol Parity**: All 5 arms use **`ExactRing + Subset-DP`** (residual cache disabled), `min_repel = 0.24`, `+14` probes/episode (`28 -> 98` under a coordinate-observation oracle), **`episode1_max_cost_spread_across_all_5_arms = 0.0`**, and **`all_onpolicy_probes_verified_realized_rollout_states = True`** (`100%` completion, `0.0` timeouts/clips). Evaluated at every checkpoint on a **strictly disjoint fixed held-out future tour bank** (`6` `m = 5` tours/map with coupled CRN noise, never seen by acquisition):

| Acquisition Arm (Same `ExactRing + Subset-DP`) | Ep 1 (`28`) | Ep 3 (`56`) | Ep 5 (`84`) | Ep 6 (`98`) | **Primary Held-Out `Ep 2–6` Mean** | **`Green-Frechet - Arm` (`Ep 2–6` 95% CI, `p`)** | Cumul Acq ms |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Frozen-GP-28` | `11.371` | `11.371` | `11.371` | `11.371` | `11.371` | **`-1.208 +/- 0.401` (`p = 1.1e-5`)** | `0.0 ms` |
| `Global-MaxVariance` | `11.371` | `10.883` | `10.128` | `9.780` | `10.491` | **`-0.329 +/- 0.308` (`p = 0.0378`)** | `29.4 ms` |
| `Uniform-Random` | `11.371` | `10.676` | `10.157` | `10.074` | `10.444` | **`-0.281 +/- 0.234` (`p = 0.0217`)** | `0.1 ms` |
| `True-OnPolicy-Trajectory` (visited `(x_t)` states) | `11.371` | **`10.350`** | `9.943` | `9.764` | `10.189` | `-0.026 +/- 0.130` (`p = 0.6710`) | `401.1 ms` |
| **`Green-Frechet-Active` (`11` Green + `3` Sentinel)** | `11.371` | `10.450` | **`9.774`** | **`9.634`** | **`10.163`** | — | `1,209.3 ms` |

- **Balanced Scientific Conclusion**:
  1. **Coordinate-Query Advantage over Non-Task Baselines**: Holding planner and diversity repulsion strictly identical, target-permutation-invariant **`Green-Frechet-Active` significantly reduces held-out future tour cost vs. `Global-MaxVariance` (`-0.329, p = 0.0378`) and `Uniform-Random` (`-0.281, p = 0.0217` on `Ep 2–6`; `-0.439, p = 3.91e-4` at `Ep 6`)**.
  2. **Parity with Genuine Realized `True-OnPolicy-Trajectory`**: Once `True-OnPolicy-Trajectory` subsamples diversity-filtered coordinates strictly from **realized optimal closed-loop SDE states**, trajectory visitation already focuses probes on low-cost corridors and **statistically ties `Green-Frechet-Active` over `Ep 2–6` (`10.189` vs. `10.163`, `p = 0.671`)** at `3.0x` lower acquisition overhead (`401 ms` vs. `1,209 ms`), with `Green-Frechet-Active` pulling modestly ahead only at late checkpoints (`Ep 6`: `9.634` vs. `9.764`, `-0.130, p = 0.0962`) via explicit root-gap bifurcation gradients and sentinel exploration.

---

## 4. Reproducible Execution Commands

```bash
# 1. Run all 20 independent audit & counterexample suites (~28s, single-threaded)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/verify_audit_closure.py

# 2. Run Experiments 1–4 (8-core map-parallel with per-worker single-thread BLAS pinning)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp1_3d_and_macro_tours.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp2_nonlmdp_kkt.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp3_highd_and_kinetic.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp4_fidelity_and_continual.py
```
