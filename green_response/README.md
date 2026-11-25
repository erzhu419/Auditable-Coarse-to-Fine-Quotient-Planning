# `green_response`: Auditable Coarse-to-Fine Green Response Planning & Physics-Mean Value Distillation

Canonical modular library and benchmark suite closing all findings from both the `v4` audit (`7087ec3`) and the `green_response` audit (`85e2323`). All active solvers, independent regression probes (`15` suites), and single-threaded benchmarks (`Experiments 1–4`) live in this single package (`green_response/`); historical snapshots (`green_kriging_mvp/`, `green_kriging_v2/`, `green_kriging_v3/`, `green_kriging_v4/`) remain frozen for provenance.

---

## 1. Module Architecture

- `core.py`:
  - `ProblemSpec`: Explicit capability guards (`validate_cole_hopf_lmdp`) enforced at solver entry and `as_isotropic_unconstrained_surrogate()` for warm-start construction.
  - `IntervalCertificate`: Standardized machine-auditable certificate record (`status`, `certified`, `certificate_scope`, `epsilon_tol`, `lower_bound`, `upper_bound`, `stop_reason`, `work`, `extras`).
  - `simulate_closed_loop_crn`: Closed-loop common-random-numbers SDE rollout with immediate $t = 0$ ball absorption, optional fine `dt_override`, and continuous segment-to-union ball hit detection (`substep_segment_hit`).
  - `paired_relative_noninferiority`: Declares scale-equivariant `primary_estimand = "linearized_contrast_vs_0"` ($E[C_{\text{method}} - (1 + \delta) C_{\text{ref}}] < 0$) alongside secondary per-map `%` excess.
- `port_solvers.py`:
  - `SchurPortPlanner`:
    - Unified string-keyed nested partition tree (`"L1" -> "L4" -> "L8" -> "EXACT"`) across 2D and 3D with full `EXACT` dispatch across disjoint, nearby/overlapping union, and ad-hoc target branches (`requested_level`, `effective_level`, `ring_nodes`, `ports_used`, `hazard_rank` logged per query).
    - Separate positive-column M-matrix interval projections (`C_lo = P_pinv @ F_lo`, `C_hi = P_pinv @ F_hi`) in `bound_harmonic_batch`, eliminating multi-leg midpoint width compounding with `0` midpoint-repair fallbacks.
    - `update_world_with_residual_audit`: Continual GP world-transition reuse via the exact M-matrix row-sum residual bound $\|U_{\text{new}} - U_{\text{old}}\|_\infty \le (\lambda / q_{\min}) \|B - A_{\text{new}} U_{\text{old}}\|_\infty$.
  - `ClassicalFDSolver`: Shared `compute_hazard_diagonal_perturbation` supporting matched `solve_warm_ilu_krylov(..., hazard_mode="exact" | "lumped")`, lazy `Cached-Target-FD`, and multi-grid fresh FD (`13^3..25^3`).
  - `solve_monotone_anisotropic_constrained_hjb_2d`: Exact 56-step KKT action bisection $u^*(g) = -(R + \eta I)^{-1} g$, optional stencil-consistent `upwind_min` readout, and `compute_discrete_fixed_policy_residual_2d` separating grid-value vs. deployed-readout Bellman residuals.
- `macro_planning.py`:
  - **Gauge-Normalized Leg Operators**: Normalizes boundary desirability to $\bar{g}_b = \mathbf{1}$ ($\bar{Z}_b = H_b \mathbf{1}$, $c_{0,b} = -\lambda \log \bar{Z}_b$, $P_b f = H_b f / \bar{Z}_b$) and factors deterministic terminal-cost sums $\Phi(S) = \sum_{b \in S} \phi_b$ out of backward DP, making interval widths machine-invariant to arbitrary signed shifts in $\phi_b$ and preventing exponential underflow.
  - **Fail-Closed Auditing**: Checks numeric validity *before* any refinement (`status="numeric_invalid", policy_action_idx=None` at `max_refine_steps=0`) and enforces strict fail-closed interval intersections (`0` midpoint repairs).
  - `MacroTourPlanner`:
    - `plan_subset_macro_policy`: $O(m^2 2^m)$ interval Bellman solver supporting `"uniform_width"` and dual-occupancy `"decision_guided"` (`0.5` incumbent + `0.5` optimistic contender, cost-normalized by missing ring backsolves).
    - `plan_exact_subset_dp` & `plan_exact_fixed_tour`: Matched-policy-class operational `Full-ExactRing` baselines without interval multi-round overhead.
    - `plan_fixed_tour_bnb`: Interval branch-and-bound with admissible `F_lo(., S_rem)` heuristic over $m!$ permutations.
- `highd_solvers.py`:
  - `BoxNeumannBesselBaseGuide`: Even-reflected $C^2$ collar Helmholtz/Bessel physics mean prior for $R = r I$ ($r > 0$, unconstrained), rejecting anisotropic `R` and finite `u_max` at entry.
  - `EikonalConeMeanGuide` & `fit_gp_value_with_prior`: Supports raw `"eikonal_cone"`, `"matched_smooth_cone"`, and `"matched_sharp_cone"` (`smooth_tau = 0` exact finite tip slope + 36-point per-goal NNLS slope/offset + $C^2$ collar matching).
  - `make_antithetic_centered_pimc_policy`: Exact control-weighted Cole-Hopf path-integral drift tilt $\delta u = (\sigma / \Delta t) E_w[\Delta W_0]$ consistent across arbitrary scalar $R = r I$.
  - `solve_kinetic_underactuated_greenres`: Scoped 4D damped double-integrator empirical extension (`6` continuation rounds) with independent path-vs-endpoint telescoping verification.

---

## 2. Explicit Claim-Scope & Evidence Grading Table

| Component / Claim | Claim Grade | Scope & Mathematical Guarantee | Empirical / Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Positive-Column M-Matrix Interval Barrier (`bound_harmonic_batch`)** | **Model-Exact Theorem (`0` violations)** | Exact upper/lower enclosures of discrete harmonic extension $H_b [F_{\text{lo}}, F_{\text{hi}}]$ on $\Omega \setminus \Gamma_b$ with `0` midpoint repairs | `0` violations across 32 signed probes, `144` `75^2` tours, `96` `m=5..9` tasks (`37,376` `m=9` entries), `128` 2D/3D crossover tasks, and `200` continual tasks |
| **Gauge-Invariant Subset-Macro DP (`plan_subset_macro_policy`)** | **Model-Scoped $\varepsilon$-Certified ($O(m^2 2^m)$)** | Certifies $F_{\text{lo}}(x_0, T) \le F^*(x_0, T) \le J^{\hat{\mu}}(x_0, T) \le F_{\text{hi}}(x_0, T)$ invariant to $\phi_b$ shifts; fail-closed on invalid inputs | `7.1e-14` width ptp across $\phi \in [-50, +200]$; `Full-ExactRing + Subset-DP` fastest in 2D (`14..161 ms`), while `DecisionGuided` cuts backsolves up to `27.4%` and reaches parity (`1.013x`) at `31^3` (`ring ~ 89`) |
| **M-Matrix Residual-Audited Continual Reuse (`Exp 4B`)** | **Model-Exact Bound (`0 / 200` violations)** | Audits cached columns under $A_{\text{new}}$ via $\|U_{\text{new}} - U_{\text{old}}\|_\infty \le (\lambda / q_{\min}) \|B - A_{\text{new}} U_{\text{old}}\|_\infty$ | `0 / 200` violations (`0.00052` regret) and **`1.37x` cumulative speedup** vs `Scratch-Rebuild`, whereas `Blind-Stale-Cache` suffers **`86 / 200` (`43%`)** violations |
| **3D Single-Query Stream Reuse & Port Compression (`Exp 1A`)** | **Empirical + Linearized Relative NI** | Separates single-LU reuse, stride-2 local-hazard lumping, and `r=1/8` port compression across full `K = 40` streams + locked fresh maps | `SingleLU-ExactRing-ExactHaz` matches `FD-25` to `7.99e-15`; `SchurPort-r1-LumpedHaz` achieves **`16.19x`** (`12` maps) & **`14.86x`** (`8` fresh maps) vs `FD-25` and **`1.34x–1.64x`** vs `Warm-ILU` (`p_NI <= 3.5e-4`) |
| **Non-LMDP Anisotropic Constrained KKT Warm-Start (`Exp 2`)** | **Exact Discrete HJB (`<= 1e-8`)** | Isotropic Cole-Hopf surrogate warm-start (`IsoFD` / `SchurPort`) for 2D anisotropic constrained policy iteration | `0 / 800` tol misses; `1.28x` equal-tol speedup (`1.03x` incremental `SchurPort` over `IsoFD`); `1.98x–2.02x` 3-step speedup passing `+0.5%` NI (`p_NI <= 0.0010`) |
| **4D/6D Helmholtz-Bessel Physics-Mean GP Prior (`Exp 3A/3B`)** | **Analytical Collar Identity + Sample Efficiency** | Exact $C^2$ even collar PDE residual ($R = r I$, unconstrained) used as GP mean prior $m(x) = V_0(x)$ | Beats NNLS-matched sharp cone on `8/8` 4D & `8/8` 6D maps (`p <= 0.0029`, held-out 6D `p = 0.049`); on locked fresh 6D maps, **`24`-anchor `Bessel` beats `108`-anchor `SharpCone` (`4.5x` sample efficiency)** |
| **4D Kinetic Double-Integrator (`Exp 3C`)** | **Exploratory Empirical Extension** | Exact discrete path telescoping (`6.39e-14`), uncoupled velocity-cap & specular trace approximations | `92.5%` reach (`93.1%` held-out) vs `70.6%` Pure-LQR & `28.3%` Kinetic-PIMC |

---

## 3. Verification & Single-Threaded Benchmark Summary (`ALL_PASSED: true`)

All timings were recorded under strict single-thread pinning (`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, verified via `threadpoolctl`).

### 3.1 Independent 15-Suite Audit Closure Regression (`verify_audit_closure.py`)
1–10. **Full `v4` (`7087ec3`) Regression**: `0 / 54` single-query sign/overlap violations; `2.22e-16` 3D eager-vs-lazy invariance; `0 / 32` signed barrier violations; `t = 0` ball absorption & `m = 7` BnB (`98.7%` pruned); `m = 8` Subset-Macro certified to `[12.790, 12.902]` (`width = 0.111 <= 0.25`, `0.0` regret); `51^2` `6101/q6` KKT residual `5.65e-13`; classical reuse accounting; `R = 2 I` Bessel residual `1.48e-9`; continuous-disk HJB `1.02e-14`; kinetic telescoping `4.97e-14`.
11. **Full `EXACT` Branch Dispatch (`Bug 2.1`)**: On `map401/q2` (`nearby_union`), `effective_level == "EXACT"` uses all `57 / 57` ring nodes and matches `Fresh-FD-25` to **`1.78e-15`** (`1.07e-14` across all `5` queries).
12. **Terminal-Cost Gauge Invariance (`Bug 2.2`)**: Across uniform shifts $\Delta\phi \in \{-50, 0, +50, +200\}$, interval width peak-to-peak variation is **`7.11e-14`** (`max_policy_mismatch = 0`).
13. **Zero-Budget `numeric_invalid` & Fail-Closed Intersections (`Bugs 2.3 & 2.4`)**: Under genuine float64 underflow (`sigma = 0.02, q0 = 1e6`) with `max_refine_steps = 0`, returns `status == "numeric_invalid"`, `policy_action_idx is None`, `refinement_steps == 0`; synthetic `1e-12` reversed bounds trigger `ValueError` (`0` midpoint repairs).
14. **Scalar-$R$ Centered PIMC Consistency (`Bug 2.5`)**: Across $r \in \{0.5, 1.0, 2.0, 4.0\}$ in an obstacle-free quadratic problem, `PIMC / Analytical` drift ratio stays in **`[0.9992, 0.9997]`** (`0.0` goal-absorption drift).
15. **Exhaustive `m = 9` Entry Check & Continual Epoch Audit**: `0 / 37,376` row-mask bound violations on `m = 9` (`2^9 = 512` subsets) and `0` single-query / macro-DP violations after localized obstacle shift under `update_world_with_residual_audit`.

---

### 3.2 Experiment 1: 3D Task-Stream Amortization & Matched-Class Macro-Tours

#### Exp 1A — 3D `25^3` Full `K = 40` Stream (`12` Maps: `6` Dev + `6` Held-Out) & `8` Locked Fresh Maps (`9400..9407`)
- `SingleLU-ExactRing-ExactHaz-25` matches `Fresh-FD-25` across all `480` benchmark queries to **`max |ΔV| = 7.99e-15`** and across all `320` fresh confirmation queries to **`1.07e-14`**.

| Method (`25^3` unless noted) | `K=20` Cost (12M) | `K=40` Cost (12M / Held6) | `+3.5%` Lin-NI `p` (12M / Held6) | `K=1` ms | `K=5` ms | `K=20` ms | `K=40` ms (12M) | Fresh-8 `K=40` ms (Cost) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Fresh-FD-21` (`first_20`) | `3.437` | — | — | `283` | `1,269` | `4,890` | — | — |
| `Fresh-FD-25` | `3.399` | `3.402` / `3.422` | — | `914` | `4,267` | `17,033` | `35,330` | `30,888` (`3.517`) |
| `Cached-Target-FD-25` | `3.399` | `3.402` / `3.422` | `2.3e-14` / `5.7e-7` | `931` | `4,267` | `15,937` | `29,498` | — |
| `Warm-ILU-ExactHaz-25` | `3.399` | `3.402` / `3.422` | `2.2e-14` / `5.5e-7` | **`474`** | **`713`** | **`1,639`** | `3,188` | `2,791` (`3.517`) |
| `Warm-ILU-LumpedHaz-25` | `3.415` | `3.424` / `3.442` | `4.8e-11` / `3.3e-5` | `479` | `745` | `1,907` | `3,571` | `2,957` (`3.537`) |
| `SingleLU-ExactRing-ExactHaz-25` | `3.399` | `3.402` / `3.422` | `2.3e-14` / `5.7e-7` | `1,075` | `4,386` | `9,976` | `13,941` | `13,555` (`3.517`) |
| `SingleLU-ExactRing-LumpedHaz-25` | `3.415` | `3.424` / `3.442` | `4.8e-11` / `3.3e-5` | `1,074` | `1,731` | `2,473` | `2,932` | `2,862` (`3.537`) |
| `SchurPort-Lazy8-LumpedHaz-25` | `3.414` | `3.422` / `3.442` | `4.5e-10` / `6.0e-5` | `1,025` | `1,459` | `2,133` | `2,623` | — |
| **`SchurPort-r1-LumpedHaz-25`** | **`3.412`** | **`3.420` / `3.442`** | **`8.1e-9` / `3.5e-4`** | `986` | `1,199` | `1,708` | **`2,183`** | **`2,079` (`3.540`)** |

- **Matched-Hazard & Fresh-Confirmation Attribution**:
  - `SingleLU` + `ExactRing` cuts `FD-25` time `2.53x` (`35.3s -> 13.9s`); stride-2 local-hazard lumping cuts rank-420 Woodbury overhead `4.76x` (`13.9s -> 2.93s` at `+0.64%` cost); and `r=1` port compression cuts another `25.5%` (`2.93s -> 2.18s`), beating `Warm-ILU-ExactHaz` (`1.46x` on 12 maps, `1.34x` on 8 fresh maps) and matched-operator `Warm-ILU-LumpedHaz` (`1.64x` on 12 maps, `1.42x` on 8 fresh maps).
  - Against coarse `Fresh-FD-21` (`first_20`), `SchurPort-r1-LumpedHaz` improves pooled 12-map cost by `-0.0250` (`p = 0.0291`), while on the `n = 6` held-out subset the difference is `-0.0210` (`95% CI [-0.069, +0.027], p = 0.313`).

#### Exp 1B — `144` Official Tours, Matched-Class `m = 5..9` Scaling, & Operator-Cost Crossover (`9800..9807`)
- **Zero certified bound violations (`0`)** across all certified methods on all `144` `75^2` tours, all `96` `m = 5..9` `65^2` tasks, and all `128` fresh crossover tasks.
- **Matched-Class Crossover (`8` Fresh Maps `9800..9807`, `m = 6`, `4` Tasks/Map)**:

| Regime `[Grid DOF, Mean Ring Nodes]` | `Full-ExactRing + Subset-DP` | `UniformWidth Port + Subset-DP` | `DecisionGuided Port + Subset-DP` | Speedup (`Decision` vs `ExactSubDP`) | Mean Backsolves (`Exact` / `Unif` / `Dec`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Cheap-2D-25sq` `[625, ring ~ 8.0]` | **`14.3 ms`** | `212.8 ms` | `235.6 ms` | `0.061x` | `92.3` / `86.1` / **`82.1`** |
| `Fine-2D-85sq` `[7,225, ring ~ 33.9]` | **`161.0 ms`** | `398.2 ms` | `458.9 ms` | `0.351x` | `389.8` / `340.3` / **`282.9`** (`-27.4%`) |
| `3D-Spherical-25cubed` `[15,625, ring ~ 29.5]` | **`2,266.0 ms`** | `2,356.1 ms` | `2,430.8 ms` | `0.932x` | `320.1` / `301.4` / **`298.5`** |
| **`Fine-3D-31cubed` `[29,791, ring ~ 89.1, eps=0.35]`** | `14,379.1 ms` | `14,412.7 ms` | **`14,201.2 ms`** | **`1.013x` (`-178 ms`, `p = 0.43`)** | `1024.1` / `972.6` / **`942.3`** (`-8.0%`) |

- **Scientific Takeaway**: On 2D grids (`25^2..85^2`), single-pass `Full-ExactRing + Subset-DP` is the fastest exact solver (`70.7..119.0 ms` across `m = 5..9` on `65^2`), because multi-round Python DP re-solves exceed the saved 2D LU backsolves. As operator factorization/backsolve cost and ring cardinality grow (`25^3 -> 31^3`), `DecisionGuided` port refinement eliminates that overhead and reaches wall-clock parity (`1.013x`) at `100%` certification (`0.0016` regret), while `Certified-BnB-FixedTour` prunes `79.5%` (`m=5`), `97.9%` (`m=7`), and **`99.74%`** (`m=8`, `40,320` permutations).

---

### 3.3 Experiment 2: Non-LMDP Anisotropic Constrained KKT (`35^2` & `51^2`, `10` Maps Each)
- **Zero tolerance misses (`0 / 800`)**: Discrete Bellman residual `<= 9.81e-9 <= 1e-8` across all queries; grid-value residual (`<= 9.81e-9`) vs. continuous bilinear central-gradient readout residual (`2.97` on `35^2`, `2.52` on `51^2`) explicitly separated.
- **Equal-Tolerance (`51^2`, `<= 1e-8`)**: `Zero` `9.00` solves (`926.5 ms`) -> `Geodesic` `8.18` (`880.7 ms`, `1.05x`) -> `IsoFD` `6.18` (`747.9 ms`, `1.24x`) -> **`SchurPort` `6.18` (`725.1 ms`, `1.28x` vs `Zero`, `1.031x` incremental over `IsoFD`)**.
- **Fixed-Budget Empirical Polish (`<= +0.5%` Linearized NI)**: `SchurPort-3Step` passes on both `35^2` (`1.98x` speedup, `p_NI = 0.0010` all-10 / `0.00059` held-5) and `51^2` (`2.02x` speedup, `p_NI = 1.39e-7` all-10 / `0.00042` held-5), matching `IsoFD-3Step` (`1.93x`, `p_NI = 2.90e-9`) while `Zero-3Step` (`p_NI >= 0.996`) and `Geodesic-3Step` (`p_NI >= 0.911`) fail.

---

### 3.4 Experiment 3: NNLS-Matched Sharp Cone Attribution, 6D Anchor-Budget Efficiency, & Scoped 4D Kinetic
- **Frozen-Label Prior Attribution (Identical `(X_all, y_total_v)` Labels)**:
  - **4D (`8` Maps: `4` Dev + `4` Held-Out)**: `ZeroMean` (`7.715` train / `8.658` unseen / `12.624` wall-corner shift) -> `MatchedSmoothCone` (`4.495` / `4.217` / `5.662`) -> `MatchedSharpCone` (`4.514` / `4.221` / `5.624`) -> **`HelmholtzBessel` (`4.310` / `4.054` / `5.177`)**, beating `MatchedSharpCone` on unseen (`-0.166, p = 0.0101`) and wall/corner shift (`-0.447, p = 0.00169`, winning `8/8` maps; held-out `n=4`: `-0.445, p = 0.083`).
  - **6D (`8` Maps: `4` Dev + `4` Held-Out)**: `ZeroMean` (`8.579` / `8.805` / `13.075`) -> `MatchedSmoothCone` (`4.603` / `4.303` / `5.565`) -> `MatchedSharpCone` (`4.604` / `4.306` / `5.529`) -> **`HelmholtzBessel` (`4.544` / `4.180` / `5.228`)**, beating `MatchedSharpCone` on unseen (`-0.126, p = 0.0121`) and wall/corner shift (`-0.301, p = 0.00285` all-8 AND **`-0.321, p = 0.0489` held-out-4**).
- **Locked Fresh 6D Anchor-Budget Efficiency (`8` Fresh Maps `9600..9607`, `N_anchors in {24, 54, 108}`)**:

| Anchor Budget (`N_fk = 128` paths/anchor) | `ZeroMean` (Unseen / Wall-Shift) | `NNLS-Matched Sharp Cone` (Unseen / Wall-Shift) | `HelmholtzBessel` (Unseen / Wall-Shift) | Plan Time (`Bessel`) | Independent FK-Seed Grad RMS Diff (`Zero` / `Sharp` / `Bessel`) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **`N = 24` (`3,072` paths)** | `13.374` / `13.797` | `5.550` / `6.063` | **`4.659` / `5.233`** | **`181.9 ms`** | `0.352` / `0.204` / **`0.090`** |
| `N = 54` (`6,912` paths) | `12.060` / `13.699` | `5.023` / `5.682` | `4.515` / `5.199` | `343.2 ms` | `0.311` / `0.177` / `0.092` |
| `N = 108` (`13,824` paths) | `10.156` / `13.093` | `4.773` / `5.430` | **`4.514` / `5.089`** | `719.7 ms` | `0.277` / `0.149` / **`0.083`** |

  - **`4.5x` Sample & Compute Reduction**: `24`-anchor `HelmholtzBessel` (`4.659` unseen / `5.233` OOD, `181.9 ms`) outperforms **`108`-anchor `NNLS-Matched Sharp Cone` (`4.773` / `5.430`, `723.7 ms`)** while cutting independent Monte-Carlo seed policy-gradient sensitivity by more than half.
- **Scoped 4D Kinetic Double-Integrator (`10` Maps)**: Independent telescoping discrepancy `<= 6.39e-14`; `92.5%` reach (`93.1%` held-out) vs `70.6%` Pure-LQR & `28.3%` Kinetic-PIMC.

---

### 3.5 Experiment 4: Model-to-Execution Fidelity Decomposition & Continual Residual Reuse
- **Exp 4A — 5-Layer Model-to-Execution Bridge (`72` Fresh Tours on `12` Locked Maps `9900..9911`)**:
  - `0 / 72` bound violations; **`100%` root-action agreement** between `DecisionGuidedPort` and `ExactMacro` (`mean discrete model regret = 0.00011`).
  - Mean `|ΔJ|` decomposition: `L1` port compression (`0.0068`) << `L2` discrete-grid to continuous GP SDE rollout (`0.7108` at `dt = 0.015`, dropping **43%** to `0.4080` at `dt = 0.005` and `0.4218` with upwind+segment-hit) < `L3` True-world vs GP-posterior model mismatch (`0.8259`, vs rollout MC SE `0.3364`).
  - **Real Continuous Policy Regret**: `DecisionGuidedPort` (`9.6534`) matches `ExactMacro` (`9.6552`, difference **`-0.0018`, `95% CI [-0.0085, +0.0049], p = 0.560`**) while beating `Euclidean` (`10.3598`) by **`-0.7064` (`p = 0.00688`)**.
- **Exp 4B — 4-Epoch Continual GP World Updates (`200` Tasks across `10` Maps `9950..9959`)**:
  - `Blind-Stale-Cache`: `409.0 ms` cumulative, **`86 / 200` (`43.0%`) certified bound violations**, `0.3143` true-epoch regret.
  - `Scratch-Rebuild`: `1,055.4 ms` cumulative, `0 / 200` violations, `0.00036` regret.
  - **`Residual-Audited-Reuse`**: **`770.5 ms` cumulative (`1.370x` speedup over `Scratch-Rebuild`), `0 / 200` certified bound violations, `0.00052` regret**.

---

## 4. Single-Threaded Reproduction Commands

```bash
# 1. Run all 15 independent audit & counterexample suites (~18s)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/verify_audit_closure.py

# 2. Run Experiments 1, 2, 3, and 4 sequentially (single-threaded)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp1_3d_and_macro_tours.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp2_nonlmdp_kkt.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp3_highd_and_kinetic.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  python3 green_response/exp4_fidelity_and_continual.py
```
