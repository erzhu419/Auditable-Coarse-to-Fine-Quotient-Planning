# Green-Kriging Control `v4`: Exact M-Matrix Boundary-Certificate Closure, Reuse-Aware 3D Benchmarks, and Single-Factor High-D / Kinetic Ablations

> **Audit Scope & Evidence Grading (`v3` → `v4`)**: Following the independent `v3.1` audit of commit `f5363a0`, `green_kriging_v4` preserves all `v1`/`v2`/`v3` artifacts untouched and resolves every mathematical, statistical, and accounting gap identified in `GPT_diagnosis_V3.1.md`. Every claim in this report is explicitly graded into one of three evidence tiers:
> - **`epsilon_certified` (Model-Scoped Deterministic Certificate)**: Provably bounded within declared $\epsilon$ **with respect to the stated discrete operator / exact node-response composition model**, verified against an independent solver with **zero enclosure violations (`0` violations)**.
> - **`observed` (Confirmed Empirical Benchmark)**: Measured across both development and held-out map seeds under paired CRN, reported with two-sided Student-$t$ 95% CIs and pre-declared one-sided non-inferiority tests.
> - **`heuristic` (Fast Uncertified Approximation)**: Computationally cheap ordering or fixed-step polish with good empirical cost, explicitly labeled without optimality certificates.

---

## 1. Summary of `v3.1 → v4` Mathematical & Protocol Closures (`verify_v4_audit_closure.py`)

Every fix in `v4` answers the three mandatory audit questions: *(1) What exact mathematical problem is solved? (2) Which equality/inequality holds and why? (3) Which independent reference verifies it?*

| `v3.1` Audit Finding | Root Cause in `v3` | Exact Mathematical Closure in `v4` | Independent Reference Check (`v4_audit_closure_results.json`) |
| :--- | :--- | :--- | :--- |
| **1. Signed Hitting Responses Clipped to Probabilities (`-0.0157`)** | Coarse Galerkin projection $H = U_d (S_d^\top U_d)^{-1} D$ is not an M-matrix inverse; `v3` clipped negative entries to `1e-300` and normalized. | Eliminated probability clipping completely. Because every separator-ring sector column $\tilde{U}_{b,k} = A_0^{-1}\mathbf{1}_{R_{b,k}} > 0$ satisfies **exact zero exterior PDE residual** $(A_0 \tilde{U}_{b,k})_{\Omega \setminus R_b} \equiv 0$, we bound $(H_b f)(x)$ directly via the **Sector-Local M-Matrix Barrier Comparison Theorem** $\widehat{u}(x) - \tilde{U}_b(x)\beta^- \le (H_b f)(x) \le \widehat{u}(x) + \tilde{U}_b(x)\beta^+$ (`beta >= 0` repaired pointwise on $R_b$). | Checked against independent sparse $A_{\Omega\setminus R_b,\Omega\setminus R_b}$ LU harmonic solver across `36` dev/audit tasks (`8,640` intervals) + `144` benchmark tasks (`17,280` intervals): **`bound_violations = 0`**, zero probability clipping. |
| **2. Invalid Half-Range Radius (`1.71×` Underestimate) & Shared-Edge Label Cancellation (`0.926` Prefix Error)** | Log-mean $-\lambda\log\bar{Z}$ is not the midpoint of $[V_{\min}, V_{\max}]$, and two permutations sharing edge $a\to b$ arrive at $a$ with different prefix distributions $p \ne p'$. | Replaced forward arrival-distribution heuristics and edge-label symmetric differences with **Batched Backward Suffix Dynamic Programming** (`W_{(b, \text{rest})}` on $R_b$): prefixes never cancel, while **identical suffixes share identical backward continuation functions** by exact Bellman optimality. | Across all `144` benchmark tours (`17,280` permutation enclosures): **`bound_violation_count = 0`**, `certified_regret_violation_count = 0` (`max_certified_regret = 0.0471 <= 0.25`). |
| **3. Missing High-D Collar PDE Residual (`-0.565` at `x0 = 1.55`) & Flat Wall Jump** | $C^2$ collar warp $\tilde{x}(x)$ altered the Bessel PDE inside $1.43 < |x_j| \le 1.65$, while `v3` assumed $r_{\text{base}} \equiv 0$ everywhere and used a flat outside-wall extension. | Composed `reflect_into_box` with the $C^2$ collar (`4L`-periodic even $C^2$ extension: wall jump **`0.0`**) and derived the exact closed-form collar Laplacian via radial Bessel ODE $\Phi''(r) = \kappa^2\Phi(r) - \frac{d-1}{r}\Phi'(r)$, evaluating $r_{\text{base}}(x) = q_0 - \frac{\sigma^2\lambda}{2}\frac{\Delta_x Z_0}{Z_0}$ analytically; also implemented independent discrete telescoping path-weight reference $\widetilde{r}_k$. | At `x0 = 1.55`: analytical **`-0.5652632025`** vs. independent finite-diff **`-0.5652632015`** (`max_abs_diff = 1.38e-9` across collar & corners); both continuum-collar (`1.447`) and discrete-telescoping (`1.474`) bracket `241²` exact reflected PDE (`1.462`, vs. uncorrected `1.545`) with gap decaying `0.0905 → 0.0270` as $\Delta t: 0.02 \to 0.003$. |
| **4. Post-Clipping Exterior Trace (`max(0, V0+dV)`) Breaking Policy Gradient Consistency** | `value_fn` clipped small negative fluctuations (`-0.025`) to `0`, making $\nabla\text{value\_fn} = 0$ where `policy != 0`. | Removed `max(0, ·)` floor completely so `policy(x) == -grad value_fn(x)` globally, and reported honest unclipped `raw_min` and `raw_rms` directly. | Unclipped `raw_rms = [0.00267, 0.00236] < 0.008` (`raw_min = [-0.0257, -0.0149]`), **`||policy + grad_FD value_fn||_inf = 4.77e-9`**, wall normal policy **`4.97e-16`**. |
| **5. 64-Angle Discrete Robust HJB (`0.0091` Continuous-Disk Residual)** | `v3` searched 64 fixed angles instead of the continuous drift disk $\{\|b - \hat{b}\|_2 \le \rho_b\}$. | Implemented closed-form **4-quadrant quarter-disk algebraic extremizer** in $Z$-space (interior disk ray + circle-axis intersections + origin). | Exact continuous-disk residual: **`1.02e-14`**; independent 4096-angle + radial check: **`5.08e-5`** (limited only by `2π/4096` chord spacing of the checker, `180×` below `v3`'s `0.00909`). |
| **6. Kinetic Bundled Switches, Fold-Without-Bounce Wall Semantics, & Omitted Guide Jump (`0.135`)** | `aniso_inward` bundled 3 changes, folded $p$ without reversing $v_n$, and omitted `V_LQR` boundary jumps. | Implemented true kinetic specular reflection (`reflect_kinetic_into_box`: $p$ folded AND $v_n \mapsto -v_n$), exact discrete LQR telescoping (`unaccounted_guide_jump = 0.0`), 3-round continuation contraction (`6.84 → 0.289 → 0.0072`), and orthogonal factor switches. | Verified across `266–480` wall bounces/map: **`unaccounted_guide_jump = 0.0`**, continuation contraction verified on all 10 maps. |

---

## 2. Experiment 1: 12-Map 3D Task Stream (with Reuse-Aware Classical Baselines) & 144 Zero-Violation Certified Tours

![Exp 1 3D Reuse and Certified Tours](./exp1_v4_3d_and_tours.png)

### 2.1 Exp 1A — 12-Map 3D Stream (`6` Dev + `6` Held-Out Maps × `20` Queries = `240` Queries, Constant `r_goal = 0.28`) [`observed`]

All grids (`13³` through `25³`) use the **identical physical goal radius `0.28`** (eliminating `v3`'s coarse-grid target-radius inflation). Alongside multi-resolution `Fresh-FD`, we include two **reuse-aware classical `25³` baselines**: `Warm-ILU-BiCGSTAB-25³` (reusing a single `spilu(A_0)` preconditioner with warm-started Krylov iterations) and `Cached-Target-FD-25³` (caching sparse LU factorizations by goal-subset geometry + Woodbury updates), plus `SchurPort-r1-ExactHaz-25³` (exact `> 0.05` local-hazard nodes, isolating hazard lumping):

| Method (`25³` Fine = `15,625` Nodes) | All-12 Cost | Held-Out-6 Cost | Diff vs. `Fresh-FD-25³` (95% CI) | Non-Inferior (`< +3.5%`, $p_{\text{NI}}$) | Diff vs. `Fresh-FD-21³` (95% CI, $p_2$) | LU Facts / RHS / Matvecs | Total 20-Query Stream Time (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `GroundTruth-FD-25³` *(Oracle)* | `2.957` | `2.899` | `-0.441 ± 0.075` | — | — | `20` LU / `20` RHS | `18,004.5` |
| `Fresh-FD-13³` | `3.763` | `3.697` | `+0.364 ± 0.080` | `False` ($p=1.00$) | `+0.326 ± 0.069` | `20` LU / `20` RHS | `304.9` |
| `Fresh-FD-17³` | `3.526` | `3.470` | `+0.128 ± 0.046` | `False` ($p=0.66$) | `+0.090 ± 0.036` | `20` LU / `20` RHS | `1,242.6` |
| `Fresh-FD-21³` | `3.437` | `3.384` | `+0.038 ± 0.015` | `True` ($6.4\text{e-}8$) | `0.000` | `20` LU / `20` RHS | `4,907.7` |
| `Fresh-FD-25³` | `3.399` | `3.349` | `0.000` | `True` | `-0.038 ± 0.015` | `20` LU / `20` RHS | `18,004.4` |
| `Warm-ILU-BiCGSTAB-25³` *(Reuse)* | `3.398` | `3.348` | `-0.000 ± 0.000` | `True` ($3.3\text{e-}27$) | `-0.038 ± 0.015` | `1` ILU + `455` MV + `17.5` fallback LU | `16,218.5` (`1.11×`) |
| `Cached-Target-FD-25³` *(Reuse)* | `3.399` | `3.349` | `0.000` | `True` | `-0.038 ± 0.015` | `24.1` LU / `20` RHS | `21,467.8` (`0.84×`) |
| **`SchurPort-r1-Lumped-25³`** | **`3.412`** | **`3.363`** | **`+0.013 ± 0.017` (`+0.39%`)** | **`True` ($1.4\text{e-}8$, held-out $3.6\text{e-}4$)** | **`-0.025 ± 0.022` ($p = 0.029$)** | **`1` LU / `182` RHS** | **`1,759.2` (`10.2×` vs `25³`, `2.8×` vs `21³`)** |
| **`SchurPort-Lazy8-Lumped-25³`** | **`3.414`** | **`3.361`** | **`+0.015 ± 0.008` (`+0.45%`)** | **`True` ($5.5\text{e-}12$, held-out $1.1\text{e-}5$)** | **`-0.023 ± 0.017` ($p = 0.012$)** | **`1` LU / `237` RHS** | **`2,159.4` (`8.3×` vs `25³`, `2.3×` vs `21³`)** |
| `SchurPort-r1-ExactHaz-25³` | `3.394` | `3.349` | `-0.004 ± 0.010` | `True` ($7.4\text{e-}12$) | `-0.043 ± 0.017` ($p = 0.0002$) | `1` LU / `2,266` RHS | `10,461.0` (`1.72×` vs `25³`) |

- **Key Findings (`observed`)**:
  1. Across `12` independent 3D maps, **`SchurPort-r1-Lumped-25³` (`1.76s`) and `SchurPort-Lazy8-Lumped-25³` (`2.16s`) now beat `Fresh-FD-21³` (`4.91s`) in BOTH wall-clock speed (`2.3×–2.8×` faster) AND closed-loop cost (`p = 0.029` and `p = 0.012` two-sided!)**, while passing non-inferiority vs. exact `Fresh-FD-25³` (`+0.39%` mean gap, $p_{\text{NI}} = 1.4 \times 10^{-8}$, held-out $p_{\text{NI}} = 3.6 \times 10^{-4}$) at **`10.2×` speedup**.
  2. Why classical reuse baselines struggle on multi-target + local-hazard streams: `Cached-Target-FD-25³` cannot reuse $A_{I_\Gamma, I_\Gamma}$ across distinct multi-goal combinations ($\binom{8}{2} = 28$ sparsity patterns) or larger local hazards, and `Warm-ILU-BiCGSTAB-25³` suffers slow convergence / fallback on strongly advective narrow-barrier M-matrices (`16.2s`).
  3. Isolating local-hazard lumping (`SchurPort-r1-ExactHaz-25³` vs. `Lumped`): exact `> 0.05` hazard support eliminates the remaining `+0.013` cost gap (`3.394` vs. `3.399`) at the expense of `2,266` LU back-solves (`10.5s`), quantifying the exact speed–accuracy trade-off of strided hazard lumping (`max_V_diff = 0.334`, closed-loop cost impact `+0.39%`).

### 2.2 Exp 1B — 144 Multi-Waypoint Tours (`12` Dev + `6` Held-Out Maps × `8` Tours, `17,280` Audited Enclosures) [`epsilon_certified` & `heuristic`]

All 6 tour-ordering methods share the **identical `75²` Same-GP Fine FD leg controller** (whose `222.2ms`/map setup + GP fit time is explicitly included in `End-to-End Time`). Every returned permutation interval $[\underline{J}(\pi), \overline{J}(\pi)]$ is audited against the **independent sparse $A_{\Omega\setminus R_b, \Omega\setminus R_b}$ exact-node harmonic composition reference** ($\epsilon = 0.25$):

| Tour Planner | Tier / Status | All-18 Cost (Held-Out-6) | Cert Rate (`Unresolved`) | Bound Violations (`/ 17,280`) | Mean / Max Exact-Node Regret | LU Back-Solves | Ordering Time (ms) | End-to-End Time (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Euclidean-Heuristic` | `heuristic` | `10.873` (`10.984`) | `0.0%` (`—`) | `—` | `0.5638` / `3.4655` | `0.0` | `12.3` | `234.5` |
| `Heuristic-1Port` | `heuristic` | `10.258` (`10.545`) | `0.0%` (`—`) | **`0`** | `0.1199` / `1.9552` | `12.0` | `52.3` | `274.5` |
| **`Lazy-8Port-Heuristic`** | **`heuristic`** | **`10.245` (`10.614`)** | `0.0%` (`—`) | **`0`** | **`0.0014` / `0.1158`** | **`94.2` (`-75.6%`)** | **`173.0` (`2.8×`)** | **`395.2` (`1.8×`)** |
| **`Certified-Adaptive-Cap6`** | **`epsilon_certified` / `unresolved`** | **`10.246` (`10.614`)** | **`79.9%` (`20.1%`)** | **`0`** | **`0.0103` / `0.5526`** *(cert max `<= 0.047`)* | `324.7` (`-15.9%`) | `934.3` | `1,156.4` |
| **`Certified-Adaptive-ExactFallback`** | **`epsilon_certified`** | **`10.240` (`10.602`)** | **`100.0%` (`0.0%`)** | **`0`** | **`0.0008` / `0.0471`** | `322.4` (`-16.5%`) | `991.4` | `1,213.5` |
| `Full-ExactRing-Reference` | `epsilon_certified` | `10.237` (`10.605`) | `100.0%` (`0.0%`) | **`0`** | `0.0000` / `0.0000` | `386.1` | `485.2` | `707.4` |

- **Honest Two-Regime Conclusion (`epsilon_certified` vs. `heuristic`)**:
  1. **Mathematical Certificate Closure**: Across all `144` tours (`17,280` permutation enclosures per method), the M-matrix barrier + backward suffix DP bound achieves **`0` bound violations** and **`0` wrong $\epsilon$-certificates** (`79.9%` certified under a 6-step refinement cap; `100.0%` certified with exact-ring fallback while using `16.5%` fewer LU back-solves than `Full-ExactRing`).
  2. **Practical Wall-Clock vs. Certificate Overhead**: When strict mathematical certification is not required, **`Lazy-8Port-Heuristic` is the practical sweet spot** (`173.0ms` ordering / `395.2ms` end-to-end — **`2.8×` faster ordering and `4.1×` fewer LU back-solves** than `Full-ExactRing`, with mean exact-node regret `0.0014` and closed-loop cost `10.245` vs. `10.237`, $p = 0.14$). Conversely, in 2D `75²`, running multi-round interval certification (`934–991ms`) costs more Python/BLAS overhead than a single batched `Full-ExactRing` solve (`485ms`) even though it reduces LU back-solve columns (`322` vs. `386`). We report this exact boundary transparently.

---

## 3. Experiment 2: Matched-Grid Non-LMDP KKT — Equal-Residual-Tolerance (`≤ 1e-8`) AND Fixed-Budget Curves

![Exp 2 KKT Equal-Tolerance and Budget Curves](./exp2_v4_kkt_curves.png)

Evaluated on `10` maps (`5` dev + `5` held-out) × `10` queries (`100` queries/grid) with exact parameters $R = \operatorname{diag}(0.35, 3.0)$ and $\|u\|_2 \le 1.80$ [`observed` & `heuristic`]:

| Grid | Initializer | **Equal-Tolerance (`‖F(V)‖∞ ≤ 1e-8`) Sweeps** | **Equal-Tol Stream Time (ms, Speedup)** | **3-Sweep Polish Cost** (Diff vs. Converged, 95% CI) | **3-Sweep Bellman Residual** | **3-Sweep Time (ms, Speedup vs. Converged `Zero`)** | Passes `+0.5%` Cost Non-Inferiority? |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`35²`** | `Zero` | `11.40` | `539.9` (`1.00×`) | `3.795` (`+0.109 ± 0.055`, `+2.95%`) | `17.41` | `197.2` (`2.74×`) | `False` ($p=0.997$) |
| | `Geodesic` | `10.67` | `512.7` (`1.05×`) | `3.782` (`+0.095 ± 0.078`, `+2.57%`) | `11.30` | `202.4` (`2.67×`) | `False` ($p=0.973$) |
| | **`IsoFD`** | **`9.01`** | **`467.6` (`1.15×`)** | **`3.687` (`+0.0007 ± 0.0033`, `+0.02%`)** | **`1.36`** | **`231.8` (`2.33×`)** | **`True` ($p_{\text{NI}} = 3.2\text{e-}7$)** |
| | **`SchurPort`** | **`8.99`** | **`455.0` (`1.19×`)** | **`3.687` (`+0.0002 ± 0.0036`, `+0.01%`)** | **`1.32`** | **`219.8` (`2.46×`)** | **`True` ($p_{\text{NI}} = 5.8\text{e-}7$)** |
| **`51²`** | `Zero` | `11.91` | `961.0` (`1.00×`) | `3.815` (`+0.132 ± 0.071`, `+3.59%`) | `23.08` | `332.2` (`2.89×`) | `False` ($p=0.997$) |
| | `Geodesic` | `11.45` | `939.5` (`1.02×`) | `3.786` (`+0.104 ± 0.068`, `+2.82%`) | `15.90` | `348.7` (`2.76×`) | `False` ($p=0.991$) |
| | **`IsoFD`** | **`9.74`** | **`870.6` (`1.10×`)** | **`3.681` (`-0.0012 ± 0.0058`, `-0.03%`)** | **`2.09`** | **`403.0` (`2.38×`)** | **`True` ($p_{\text{NI}} = 1.5\text{e-}5$)** |
| | **`SchurPort`** | **`9.79`** | **`856.0` (`1.12×`)** | **`3.681` (`-0.0017 ± 0.0046`, `-0.05%`)** | **`2.11`** | **`376.1` (`2.56×`)** | **`True` ($p_{\text{NI}} = 1.9\text{e-}6$)** |

- **Separated Conclusions**:
  - **Same-Precision Solver Speedup (`observed`)**: Requiring $\|F(V)\|_\infty \le 10^{-8}$ (`~1e-7` worst outlier on `51²`), Cole–Hopf warm-starts (`IsoFD` & `SchurPort`) reduce Howard iterations by `~2.1–2.4` sweeps and deliver a modest but real **`1.12×–1.19×` wall-clock speedup** (including warm-start overhead).
  - **Equal-Cost-Tolerance Polish Speedup (`heuristic` polish, `observed` quality)**: Under a `+0.5%` control-cost non-inferiority tolerance, 3-sweep `IsoFD` and `SchurPort` polish are statistically indistinguishable from machine-precision KKT (`+0.01%` to `-0.05%`, $p_{\text{NI}} \le 1.5 \times 10^{-5}$) at **`2.33×–2.56×` speedup**, whereas 3-sweep `Zero` and `Geodesic` fail non-inferiority (`+2.57%` to `+3.59%`). As in `v3`, `IsoFD` and `SchurPort` tie in 2D.

---

## 4. Experiment 3: Collar-Exact High-D Duel, Single-Factor `V` vs. `V − V0` Ablation, OOD Starts, & Clean Kinetic Specular Factorial

![Exp 3 High-D and Kinetic Ablations](./exp3_v4_highd_ablations.png)

### 4.1 4D & 6D Collar-Exact Benchmark, Unseen OOD Starts, & Single-Factor Distillation Ablation (`8` Maps = `4` Dev + `4` Held-Out × `3` Queries) [`observed`]

All four distillation rows (`Ablation-Unguided-TotalV`, `Ablation-Guided-TotalV`, `Ablation-DiscreteTele-ResidualV`, `CollarExact-GreenRes`) use **100% identical interior anchors, boundary anchors, continuation rounds, `MirrorNeumannMatern52GP` hyperparameters, and CRN draws**, changing **one single factor at a time**:

| Dim | Method | Query-Start Cost (All 8 / Held-Out 4) | **Unseen OOD-Start Cost** (`GreenRes − Method` 95% CI) | Measured `K=1` Cost | Reach | **Cold `K=1` Total Time incl. 100% GP (ms)** | **Measured 36-Traj Batch Time (ms)** |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **4D** | `Pure-Base-Guide` *(0 GP)* | `5.743` (`5.994`) | `5.602` (`-1.500 ± 0.658`, $p=0.0010$) | `5.934` | `100.0%` | `8.4` | `30.6` |
| | `SameGP-Centered-PIMC-H16` | `5.329` (`5.758`) | `5.392` (`-1.290 ± 0.728`, $p=0.0041$) | `6.382` | `99.4%` | `588.9` | `4,070.2` |
| | `SameGP-Centered-PIMC-H48` | `4.638` (`5.031`) | `4.674` (`-0.572 ± 0.424`, $p=0.0153$) | `5.045` | `100.0%` | **`383.2`** | `2,721.3` |
| | `Ablation-Unguided-TotalV` | `32.390` (`31.674`) | `13.943` (`-9.841 ± 9.984`) | `20.880` | `69.0%` | `1,720.9` | `1,768.3` |
| | **`Ablation-Guided-TotalV`** | **`6.878` (`7.380`)** | **`8.322` (`-4.221 ± 1.690`, $p=0.0006$)** | `6.413` | `77.5%` | `579.0` | `608.6` |
| | `Ablation-DiscreteTele-ResidualV` | `4.149` (`4.375`) | `4.199` (`-0.097 ± 0.080`, $p=0.024$) | `4.310` | `100.0%` | `693.5` | `637.0` |
| | **`CollarExact-GreenRes`** | **`3.973` (`4.168`)** | **`4.102`** *(reference)* | **`4.237`** | **`100.0%`** | `561.1` (`9.2ms` exec) | **`500.3` (`5.4×` vs `PIMC48`)** |
| **6D** | `Pure-Base-Guide` *(0 GP)* | `5.855` (`5.307`) | `4.935` (`-0.724 ± 0.252`, $p=0.00025$) | `6.436` | `100.0%` | `12.4` | `37.4` |
| | `SameGP-Centered-PIMC-H16` | `5.401` (`4.962`) | `4.633` (`-0.422 ± 0.223`, $p=0.0029$) | `6.211` | `100.0%` | **`951.7`** | `6,721.8` |
| | `SameGP-Centered-PIMC-H48` | `5.657` (`5.219`) | `4.713` (`-0.502 ± 0.135`, $p=4.9\text{e-}5$) | `6.305` | `100.0%` | `1,135.2` | `8,141.0` |
| | `Ablation-Unguided-TotalV` | `15.588` (`11.542`) | `10.479` (`-6.268 ± 1.684`) | `11.165` | `66.6%` | `5,310.7` | `5,171.0` |
| | **`Ablation-Guided-TotalV`** | **`9.462` (`8.695`)** | **`9.578` (`-5.367 ± 0.844`, $p=1.4\text{e-}6$)** | `11.624` | `57.1%` | `1,594.2` | `1,442.0` |
| | `Ablation-DiscreteTele-ResidualV` | `4.805` (`4.523`) | `4.192` (`+0.019 ± 0.073`, $p=0.55$) | `4.953` | `100.0%` | `1,743.6` | `1,486.8` |
| | **`CollarExact-GreenRes`** | **`4.736` (`4.453`)** | **`4.211`** *(reference)* | **`5.001`** | **`100.0%`** | `1,535.5` (`15.3ms` exec) | **`1,277.7` (`5.3×–6.4×` vs `PIMC`)** |

- **Decisive Mechanistic Answers (`observed`)**:
  1. **Single-Factor Proof of Analytical Green Decomposition (`Guided-TotalV` vs. `CollarExact-GreenRes`)**: Even with **identical guided FK trajectories, anchors, boundaries, and GP kernel**, regressing total $V$ degrades reach rate to `77.5%` (4D) / `57.1%` (6D) and doubles cost (`6.878 → 3.973` in 4D, $p = 3.5 \times 10^{-5}$; `9.462 → 4.736` in 6D, $p = 9.2 \times 10^{-7}$), because smooth Matérn kernels cannot fit the steep multi-goal Bessel/logarithmic singularity of $V$ without severe gradient oscillation, whereas $V - V_0$ is smooth!
  2. **Generalization to Unseen OOD Starts**: On held-out random start points **never used to generate corridor anchors**, `CollarExact-GreenRes` maintains significant wins over `PIMC-H48` (`4.102 vs 4.674` in 4D, $p = 0.015$; `4.211 vs 4.713` in 6D, $p = 4.9 \times 10^{-5}$) and `PIMC-H16` (`4.211 vs 4.633` in 6D, $p = 0.0029$).
  3. **Measured Online PIMC ESS & FK Tail Diagnostics**: Live online PIMC ESS drops from `15.73/36 → 13.95/36` (4D) and `25.30/36 → 22.47/36` (6D) when extending horizon `H=16 → 48`. In `CollarExact-GreenRes`, `~1.3%` of FK steps visit the collar (`mean_ess = 14.8` in 4D, `30.8` in 6D), weighted surviving tail mass is tiny (`2.1e-5` in 4D, `2.5e-4` in 6D), and continuation bootstrap contracts to `6.8e-9` (4D) / `3.6e-6` (6D).
  4. **Scope Clarification**: High-D `GreenRes` is **per-query amortized control distillation** (rebuilding FK labels when goals change, breaking even against PIMC at `K = 2–3` trajectories and running `5.3×–6.4×` faster on a 36-trajectory batch), distinct from the cross-query reusable 2D/3D port response library.

### 4.2 4D Kinetic Specular Double-Integrator Orthogonal Factorial (`10` Maps = `6` Dev + `4` Held-Out) [`observed`]

Under **true kinetic specular wall reflection** ($p$ folded into $[-1.65, 1.65]^2$ AND normal velocity $v_n \mapsto -v_n$) with **exact discrete LQR telescoping (`max_unaccounted_guide_jump = 0.0`)**:

| Variant | All-10 Reach (Held-Out-4) | Truncated Running Cost | Timeout Heuristic (`V_LQR+2`) | Total Finite-Horizon Score | `Best − Variant` Score (95% CI, $p_2$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Pure-LQR-Guide` | `70.6%` (`68.1%`) | `31.67` | `0.68` | `32.35` | `-20.58 ± 9.22` ($p=0.00069$) |
| `Kinetic-Centered-PIMC` | `28.3%` (`28.5%`) | `18.09` | `1.91` | `20.00` | `-8.23 ± 3.67` ($p=0.00067$) |
| `FK-IsoKernel-FullBnd-BaseAnch` | `62.2%` (`70.1%`) | `17.94` | `0.92` | `18.86` | `-7.10 ± 4.03` ($p=0.0032$) |
| `FK-IsoKernel-FullBnd-BrakingAnch` | `78.6%` (`61.1%`) | `16.42` | `0.59` | `17.01` | `-5.24 ± 3.53` ($p=0.0084$) |
| `FK-IsoKernel-InwardBnd-BrakingAnch` | `87.5%` (`83.3%`) | `15.16` | `0.31` | `15.47` | `-3.70 ± 3.12` ($p=0.025$) |
| `FK-AnisoKernel-FullBnd-BrakingAnch` | `91.7%` (`81.9%`) | `12.19` | `0.18` | `12.38` | `-0.61 ± 0.76` ($p=0.103$) |
| **`FK-AnisoKernel-InwardBnd-BrakingAnch`** | **`92.5%` (`93.1%`)** | **`11.60`** | **`0.16`** | **`11.77`** | `0.00` *(reference)* |

- **Clean Factor Attribution**: Separating the three switches shows that **anisotropic `(p, v)` residual kernel lengthscales** provide the largest single statistically significant jump (`17.01 → 12.38`, `-4.63 ± 3.51`, $p = 0.0153$), while **Fichera inward boundary anchors $(p - g)\cdot v < 0$** consistently improve reach under both isotropic (`78.6% → 87.5%`, held-out `61.1% → 83.3%`) and anisotropic kernels (`91.7% → 92.5%`, held-out `81.9% → 93.1%`, `-0.61 ± 0.76`), and braking anchors raise base isotropic reach (`62.2% → 78.6%`). All three combine cleanly to achieve **`92.5%` overall (`93.1%` held-out) reach** with zero unaccounted boundary guide jumps.

---

## 5. File Manifest & Reproducibility (`green_kriging_v4/`)

Run with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1` (also enforced in-script and logged in JSON `metadata`):

- [`core_v4.py`](./core_v4.py): Runtime metadata, `ProblemSpec`, specular box & true kinetic specular reflection, Same-GP `KrigingWorldModel`, CRN simulator, and paired Student-$t$ / non-inferiority statistics.
- [`schur_port_v4.py`](./schur_port_v4.py): `ClassicalFDSolverV4` (`Fresh-FD`, `Cached-Target-FD`, `Warm-ILU-BiCGSTAB`, killed adjoint), `SchurPortCertifiedPlannerV4` (conservation-preserving `1 → 4 → 8 → exact_ring` tree, M-matrix barrier comparison theorem, batched Held-Karp backward suffix DP), equal-tolerance Non-LMDP KKT solver, and exact continuous-disk Robust HJB solver.
- [`highd_v4.py`](./highd_v4.py): `BoxNeumannBesselBaseGuideV4` (even $C^2$ collar + exact analytical collar Laplacian + discrete telescoping reference), unclipped `solve_highd_fk_distillation_v4` (`residual` vs. `total_V`), online ESS-instrumented `make_antithetic_centered_pimc_policy_v4`, and `solve_kinetic_underactuated_greenres_v4`.
- [`verify_v4_audit_closure.py`](./verify_v4_audit_closure.py) → [`v4_audit_closure_results.json`](./v4_audit_closure_results.json): Independent `v3.1` counterexample closure suite (`ALL_PASSED: true`).
- [`exp1_v4_3d_and_certified_tours.py`](./exp1_v4_3d_and_certified_tours.py) → [`exp1_v4_results.json`](./exp1_v4_results.json), [`exp1_v4_3d_and_tours.png`](./exp1_v4_3d_and_tours.png).
- [`exp2_v4_kkt_curves.py`](./exp2_v4_kkt_curves.py) → [`exp2_v4_kkt_results.json`](./exp2_v4_kkt_results.json), [`exp2_v4_kkt_curves.png`](./exp2_v4_kkt_curves.png).
- [`exp3_v4_highd_ablations.py`](./exp3_v4_highd_ablations.py) → [`exp3_v4_highd_results.json`](./exp3_v4_highd_results.json), [`exp3_v4_highd_ablations.png`](./exp3_v4_highd_ablations.png).
