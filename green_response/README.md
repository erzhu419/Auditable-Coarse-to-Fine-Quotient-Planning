# `green_response`: Auditable Coarse-to-Fine Green Response Planning & Physics-Mean Value Distillation

Canonical modular library and benchmark suite closing all findings from the `v4` audit (`7087ec3`) while upgrading multi-waypoint planning from $m!$ suffix enumeration to **Subset-Bellman-Guided Interval Branch-and-Bound (`m = 5..8`)** and **Genuine $O(m^2 2^m)$ Adaptive Subset-State Macro-Planning (`m = 5..9`)**.

Historical snapshots (`green_kriging_mvp/`, `green_kriging_v2/`, `green_kriging_v3/`, `green_kriging_v4/`) remain untouched for reproducibility; all active solvers, regression probes, and benchmarks live in this single canonical package (`green_response/`).

---

## 1. Module Architecture

- `core.py`: `ProblemSpec` with explicit capability guards (`validate_cole_hopf_lmdp`), exact box & kinetic specular reflection (`reflect_into_box`, `reflect_kinetic_into_box`), Same-GP Matérn-5/2 world model (`KrigingWorldModel`), closed-loop CRN rollout with immediate $t = 0$ goal absorption (`simulate_closed_loop_crn`), and scale-equivariant paired relative non-inferiority testing (`paired_relative_noninferiority`).
- `port_solvers.py`:
  - `SchurPortPlanner`: Canonical string-keyed nested partition tree (`"L1" -> "L4" -> "L8" -> "EXACT"`) unified across 2D and 3D (zero eager/lazy mismatch, zero wasted LU backsolves), repaired single-query value-bound log shifts (`+lam * log(gamma_lo)`, `+lam * log(gamma_hi)`), explicit `value_bound_scope`, and cached `(wp_id, level)` ring operators.
  - `ClassicalFDSolver`: Multi-resolution fresh FD (`13^3..25^3`), repaired lazy `Cached-Target-FD` (checks `len(active_h) <= 45` *before* factoring base `A0_{II}`), and repaired `Warm-ILU-BiCGSTAB` (genuine non-constant warm-starts + tight `rtol=1e-12, atol=1e-15` resolving $Z \sim 10^{-14}$ dynamic range).
  - `solve_anisotropic_constrained_kkt_action` & `solve_monotone_anisotropic_constrained_hjb_2d`: Exact anisotropic constrained KKT minimizer $u^*(g) = -(R + \eta I)^{-1} g$ (`56`-step vectorized bisection to float64 precision) shared between HJB policy evaluation and continuous policy readout, plus exact `sweeps_used` linear-solve accounting.
  - `solve_exact_continuous_ball_robust_hjb_2d`: Closed-form 4-quadrant continuous-disk robust HJB (`< 1e-13` exact residual).
- `macro_planning.py`:
  - Unified immediate $t = 0$ and leg-switch ball absorption (`wp_masks[b][x]`) across continuous CRN simulation, port planners, and independent sparse-LU references (`independent_exact_ball_tour_scores`, `independent_exact_macro_bellman_reference`).
  - Zero silent interval clamping (`numeric_invalid` detection; `0` invalid intervals across all benchmarks).
  - `MacroTourPlanner.plan_subset_macro_policy`: Genuine $O(m^2 2^m)$ backward interval Bellman solver on `(ring_node, subset_bitmask S)` certifying $\varepsilon$-optimality over **all Markov macro-policies**.
  - `MacroTourPlanner.plan_fixed_tour_bnb`: Frontier-controlled interval branch-and-bound using `F_lo(., S_rem)` from the $O(m^2 2^m)$ Subset-Macro DP as an exact admissible heuristic over all $m!$ permutations.
- `highd_solvers.py`:
  - `BoxNeumannBesselBaseGuide`: Even-reflected $C^2$ collar Helmholtz/Bessel physics mean prior supporting isotropic scalar $R = r I$ ($r > 0$) consistently across $\lambda = r\sigma^2$, $\kappa = \sqrt{2 q_0 / r}/\sigma^2$, $u = -\nabla V / r$, collar Laplacian residual, and stochastic Girsanov increment; rejects finite `u_max` and anisotropic `R` at entry.
  - `EikonalConeMeanGuide` & `fit_gp_value_with_prior`: Smooth reflecting geometric distance-cone control prior and zero-drift frozen-label refit API.
  - `solve_kinetic_underactuated_greenres`: Scoped 4D damped double-integrator empirical extension (`6` continuation rounds) replacing hardcoded `0.0` jump fields with an independent floating-point path-action vs endpoint-telescoping check (`measured_telescoping_discrepancy`).

---

## 2. Explicit Claim-Scope & Evidence Grading Table

| Component / Claim | Claim Grade | Scope & Mathematical Guarantee | Empirical / Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Sector-Local Positive-Column M-Matrix Barrier (`bound_harmonic_batch`)** | **Model-Exact Theorem (`0` violations)** | Exact upper/lower enclosures of discrete harmonic extension $H_b F$ on $\Omega \setminus \Gamma_b$ for signed $F$ without probability clipping | `0` violations across 32 signed asymmetric-drift probes (`L1..EXACT`), `144` `m=5` tours, and `m=7` (`5,040` perms) |
| **Single-Query Ring Value Bounds (`solve_query`)** | **Model-Exact Theorem (`0` violations)** | $\hat{V} + \lambda\log\gamma_{\text{lo}} \le V_{\text{op}} \le \hat{V} + \lambda\log\gamma_{\text{hi}}$ w.r.t. solved discrete operator (`exact` or `lumped`) | `0 / 27` violations on GPT6's coarse 1-goal sign probe + `0 / 27` on 2-goal adversarial near-overlap probes |
| **Adaptive Subset-Macro Planner (`plan_subset_macro_policy`)** | **Model-Scoped $\varepsilon$-Certified ($O(m^2 2^m)$)** | Certifies $F_{\text{lo}}(x_0, T) \le F^*(x_0, T) \le J^{\hat{\mu}}(x_0, T) \le F_{\text{hi}}(x_0, T)$ over all discrete Doob Markov macro-policies | `100%` certified (`eps=0.25`), `0` bound/regret violations across `144` `m=5` tasks and `m = 5, 7, 8, 9` (`362,880` perm scale in `1.87s/map`) |
| **Fixed-Order Interval Branch-and-Bound (`plan_fixed_tour_bnb`)** | **Model-Scoped $\varepsilon$-Certified** | Admissible `F_lo(., S_rem)` prefix pruning over $m!$ permutations (`LB(P) > U_inc` zero-loss pruning) | `100%` certified, `0` violations; prunes `86.5%` (`m=5`), `97.7%` (`m=7`), and **`99.64%`** (`m=8`, `40,320` perms) |
| **3D Task-Stream Reuse & Port Compression (`Exp 1A`)** | **Empirical + Scale-Equivariant NI** | Isolates single-LU separator-ring reuse vs. local-hazard lumping vs. `r=1/8` port compression across `K = 1..40` | `SchurPort-r1-LumpedHaz` `+0.38%` excess vs `Fresh-FD-25` (`p_NI = 2.4e-8` at `+3.5%` margin), `16.1x` faster than `FD-25` and `1.44x` faster than repaired `Warm-ILU-BiCGSTAB` at `K=40` |
| **Non-LMDP Anisotropic Constrained KKT (`Exp 2`)** | **Exact Discrete HJB (`<= 1e-8`)** | Exact KKT readout $u^*(g) = -(R + \eta I)^{-1} g$ + `56`-step inner bisection | `0 / 800` tolerance misses on `35^2` & `51^2`; `1.30x` equal-tol speedup and `2.18x` speedup at `<= +0.5%` cost NI (`p_NI = 2.0e-8`) |
| **4D/6D Helmholtz-Bessel Physics-Mean GP Distillation (`Exp 3A/3B`)** | **Analytical Collar Identity + Empirical Prior Gain** | Exact $C^2$ even collar PDE residual ($R = r I$, unconstrained); GP with analytical physics mean prior $m(x) = V_0(x)$ | On identical frozen FK labels, `HelmholtzBessel` beats `ZeroMean` (`-3.40` in 4D, `-4.03` in 6D) AND statistically beats smooth `EikonalCone` on unseen starts (`p=0.021` 4D, `p=0.0074` 6D) & wall/corner OOD shift (`p=0.0043` 4D, `p=0.0049` 6D) |
| **4D Kinetic Double-Integrator (`Exp 3C`)** | **Exploratory Empirical Extension** | Exact discrete path telescoping (`measured_telescoping_discrepancy < 1e-13`), but velocity-cap boundary & specular GP trace remain uncoupled approximations | `92.5%` reach (`93.1%` held-out) at 6 continuation rounds vs `70.6%` Pure-LQR & `28.3%` Kinetic-PIMC; `2.35%` execution `u<=4.5` clipping |

---

## 3. Verification & Benchmark Summary (`ALL_PASSED: true`)

### 3.1 Independent 10-Suite Audit Regression (`verify_audit_closure.py`)
Reproduces and closes every counterexample from `markdown/green_kriging_v4_audit/checks/`:
1. **Single-Query Sign Probe (`54` cases)**: `0 / 27` violations on GPT6's 1-goal sign probe (`port_v4_sign_probe.py`) + `0 / 27` on 2-goal near-overlap probes (`worst_raw_min_Z = 1.03e-5`).
2. **3D Nested Tree Invariance**: Eager vs. lazy initialization across `"L1", "L4", "L8", "EXACT"` in 3D (`17^3` with drift) achieves `max_eager_vs_lazy_column_diff = 2.22e-16` and `0` wasted LU backsolves (`12 == |R_0|`).
3. **Signed Barrier Probe (`32` cases)**: `0` violations across all levels without interval clamping.
4. **Tour $t = 0$ Absorption & `m = 7` (`5,040` perms) BnB**: Immediate ball absorption selects initial-inside target first with `0` violations; `m = 7` BnB evaluates only `65 / 5,040` leaves (`98.7%` pruned), `0` violations, `0.0` regret.
5. **Subset-Macro Bellman `m = 8` Audit**: Coarse `[7.907, 17.187]` -> final `[12.84612567, 12.84612572]` enclosing exact `12.84612570` (`0.0` regret, `478 ms`).
6. **Anisotropic KKT Readout & `51^2` `6101/q6` Stall**: Matches `brentq`/`SLSQP` to `4.44e-16` Hamiltonian excess; `6101/q6` hits `5.65e-13 <= 1e-8` in `7` linear solves.
7. **3D Classical Reuse Accounting**: `Cached-Target-FD` performs `0` double factorizations (`18.83` mean across 12 maps vs `24.08` in `v4`); `Warm-ILU-BiCGSTAB` uses genuine warm-start (`ptp(x0) = 0.278`) with `20/20` `info == 0`.
8. **High-D Capability Guard & Scalar $R = 2 I$**: Rejects anisotropic `R` and finite `u_max` with `ValueError`; supports scalar `R = 2 I` to `1.48e-9` HJB residual (`0.65` error in `v4` eliminated); proves `0.0` algebraic difference between `GP(y; prior=V0)` and `V0 + GP(y - V0)`.
9. **Collar Trace & Continuous-Disk Robust HJB**: `near4` unclipped raw RMS `0.00267`, gradient-policy mismatch `3.58e-9`, continuous-disk residual `1.02e-14`.
10. **Kinetic Independent Telescoping, Adjoint, & PIMC**: `seed=14500` measured telescoping discrepancy `4.97e-14`, round-6 continuation diff `0.0130`, killed-adjoint diff `5.36e-10` (`0.0` goal mass), free-world PIMC variance `5.30e-32`.

---

### 3.2 Key Quantitative Results Across Experiments 1–3

#### Experiment 1A: 3D Structural Reuse & Amortization (`12` Maps, `25^3`, `r_goal = 0.28`)
| Method (`25^3` unless noted) | Mean Cost (12 Maps) | Per-Map `%` Excess vs `FD-25` | `+3.5%` Rel. NI `p` | `K=1` ms | `K=5` ms | `K=20` ms | `K=40` ms | LU Facts (`K=20`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Fresh-FD-17` | `3.526` | `+3.73%` | `0.652` (Fail) | `86` | `341` | `1,289` | — | `20.0` |
| `Fresh-FD-21` | `3.437` | `+1.13%` | `6.0e-8` (Pass) | `316` | `1,414` | `5,353` | — | `20.0` |
| `Fresh-FD-25` | `3.399` | `0.00%` | — | `1,027` | `4,688` | `18,557` | `38,552` | `20.0` |
| `Cached-Target-FD-25` (Repaired) | `3.399` | `0.00%` | `0.0` (Pass) | `1,133` | `4,828` | `17,594` | `32,351` | `18.83` |
| `Warm-ILU-BiCGSTAB-25` (Repaired) | `3.399` | `+0.001%` | `5.4e-36` (Pass) | **`518`** | **`777`** | **`1,744`** | `3,449` | `0.58` |
| `SingleLU-ExactRing-ExactHaz-25` | `3.398` | `-0.02%` | `4.4e-19` (Pass) | `1,206` | `4,947` | `11,391` | `16,782` | `1.0` |
| `SingleLU-ExactRing-LumpedHaz-25` | `3.414` | `+0.45%` | `3.0e-12` (Pass) | `1,183` | `2,021` | `2,966` | `3,509` | `1.0` |
| `SchurPort-Lazy8-LumpedHaz-25` | `3.414` | `+0.44%` | `8.1e-12` (Pass) | `1,106` | `1,581` | `2,302` | `2,844` | `1.0` |
| **`SchurPort-r1-LumpedHaz-25`** | **`3.412`** | **`+0.38%`** | **`2.4e-8` (Pass)** | `1,095` | `1,331` | `1,873` | **`2,388`** | **`1.0`** |

- **Clean Attribution**: Reusing `splu(A_0)` with exact ring + exact 420-node hazard Woodbury cuts `K=40` time `2.30x` (`38.6s -> 16.8s`); stride-2 local-hazard lumping cuts rank-420 Woodbury overhead `4.78x` (`16.8s -> 3.51s` at only `+0.45%` cost); and `r=1` port compression cuts another `32%` (`3.51s -> 2.39s`), crossing below repaired `Warm-ILU-BiCGSTAB` (`3.45s`) between `K = 20` and `K = 40` while also beating `Fresh-FD-21` in closed-loop cost (`-0.025, p = 0.029`).

#### Experiment 1B: Certified Tours (`144` Official Tasks, $t=0$ Fixed) & Scalability (`m = 5..9`)
- On the 144 official tours (`113` strictly exterior + `31` initial-inside starts, all evaluated under unified $t=0$ immediate ball absorption):
  - **`0` bound violations and `0` certified regret violations** across all certified methods;
  - `Certified-Subset-MacroMDP` ($O(m^2 2^m)$) achieves the **lowest closed-loop cost** (`10.193` all / `10.470` exterior vs `10.845` / `11.108` Euclidean, `p = 0.00028`, and `10.205` / `10.482` fixed-order `Full-ExactRing`) at `100%` certification (`967 ms` vs `901 ms` eager `Full-ExactRing`, `-13.6%` LU backsolves);
  - `Certified-BnB-FixedTour` prunes `86.5%` of `m=5` permutations and saves `28.8%` of LU backsolves (`274.7` vs `386.1`).
- **Scalability (`m = 5 -> 7 -> 8 -> 9`, Strictly Exterior Starts)**:
  - `m = 7` (`5,040` perms): `BnB` prunes **`97.7%`** (`100%` certified, `0` violations vs exact `5,040` oracle); `Subset-Macro` takes `1,049 ms` (`100%` certified).
  - `m = 8` (`40,320` perms): `BnB` prunes **`99.64%`** (`2,807 ms`, `100%` certified); `Subset-Macro` takes **`1,477 ms`** (`100%` certified).
  - `m = 9` (`362,880` perms): `Subset-Macro` ($2^9 = 512$ states) certifies `100%` of tasks in **`1,873 ms/map`**.

#### Experiment 2: Repaired Non-LMDP Anisotropic Constrained KKT (`35^2` & `51^2`)
- **Zero tolerance misses (`0 / 800`)**: `max_bellman_residual <= 9.81e-9 <= 1e-8` across all 100 queries per grid; exact KKT policy readout lowers converged `51^2` closed-loop cost from `3.671` (`v4` radial clip) to **`3.534`**.
- **Equal-Tolerance (`<= 1e-8`)**: `SchurPort` reduces `51^2` linear solves from `9.00` to `6.18` (`963.9 ms -> 743.2 ms`, **`1.30x` speedup**).
- **Equal Control-Cost Margin (`<= +0.5%` Relative NI)**: `SchurPort-3Step` passes on both `35^2` (`+0.18%`, `p_NI = 0.0010`, **`2.08x` speedup**) and `51^2` (`+0.038%`, `p_NI = 2.0e-8`, **`2.18x` speedup**), whereas `Zero-3Step` (`+3.44%`) and `Geodesic-3Step` (`+2.23%`) fail.

#### Experiment 3: High-D Frozen-Label Physics-Mean Attribution & Scoped 4D Kinetic
- **Frozen-Label Prior Attribution (`4D` & `6D`, Identical `(X_all, y_total_v)`)**:
  - **4D**: `ZeroMean` (`7.715` train / `12.624` wall-corner shift) -> `EikonalCone` (`4.486` / `5.605`) -> **`HelmholtzBessel` (`4.310` / `5.177`)**, beating `EikonalCone` on train (`-0.176, p = 0.0155`), unseen in-dist (`-0.172, p = 0.0206`), and true wall/corner OOD shift (`-0.428, p = 0.0043`).
  - **6D**: `ZeroMean` (`8.579` train / `13.075` wall-corner shift) -> `EikonalCone` (`4.598` / `5.519`) -> **`HelmholtzBessel` (`4.544` / `5.228`)**, statistically beating `EikonalCone` on unseen in-dist (`-0.127, p = 0.0074`) and true wall/corner OOD shift (`-0.291, p = 0.0049`), while standalone `Pure-Bessel` (`5.504`) outperforms `Pure-Eikonal` (`12.412`) by `-6.908` (`p = 2.9e-6`).
- **Scoped 4D Kinetic Double-Integrator (`10` Maps, `6` Continuation Rounds)**:
  - Independent floating-point path-vs-endpoint telescoping discrepancy `<= 6.39e-14`; `FK-AnisoKernel-InwardBnd-BrakingAnch` achieves **`92.5%` all-map (`93.1%` held-out) reach** (`11.78` total score vs `32.35` Pure-LQR and `20.00` Kinetic-PIMC), with `2.35%` execution action-cap fraction and explicit velocity-cap / specular-wall boundary RMS diagnostics reported.

---

## 4. Reproduction Commands

```bash
# 1. Run all 10 independent audit & counterexample checks (~18s, single-threaded)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/verify_audit_closure.py

# 2. Run Experiments 1, 2, and 3 sequentially
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp1_3d_and_macro_tours.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp2_nonlmdp_kkt.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp3_highd_and_kinetic.py
```
