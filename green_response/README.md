# `green_response`: Auditable Coarse-to-Fine Green Response Planning & Goal-Oriented World-Model Sensing

Canonical modular library and benchmark suite closing all findings across `7087ec3`, `85e2323`, `ddd19c5`, `d1b926a`, `29fa7c6`, `57e5912`, and `c2c499e` (`greed_kriging_v6` closure + `Exp 5` falsifiable cross-task response-subspace diagnostic). All active solvers, independent counterexample regression probes (`23` suites), replayable acquisition tapes, and reproducible benchmarks (`Experiments 1–5`) live in `green_response/`; historical snapshots (`green_kriging_mvp/`, `green_kriging_v2/`, `green_kriging_v3/`, `green_kriging_v4/`) remain frozen for provenance.

---

## 1. Module Architecture, Hardened Contracts, & Provenance Manifests

- `core.py`:
  - `ProblemSpec`: Enforces explicit LMDP capability guards (`validate_cole_hopf_lmdp`) at solver entry and constructs `as_isotropic_unconstrained_surrogate()` warm-starts.
  - `IntervalCertificate`: Machine-auditable fail-closed certificate contract (`__post_init__` validates allowed `status`, finite ordered `lower_bound <= upper_bound`, `gap <= epsilon_tol` on `"epsilon_certified"`, non-negative `operator_epoch`, explicit `certificate_kind` in `{"policy_and_value_enclosure", "value_only_enclosure"}`, strict `_validate_typed_policy_entry` rejecting `None`, empty `{}` / `()` / empty `ndarray`, and non-callables when `certified=True` unless `allow_value_only=True`, and blocks `extras` from overriding protected fields).
  - `compute_source_manifest` & `collect_runtime_metadata`: Embeds `git_head_sha`, `git_dirty_green_response`, `package_py_sha256`, and `per_file_sha256` across every result JSON alongside explicit per-block `"block_provenance"` and `"generating_commit"` tags (`"85e2323"`, `"ddd19c5"`, `"29fa7c6"`, `"57e5912"`, `"c2c499e"`).
  - `save_lossless_acquisition_tape_npz` & `load_and_verify_lossless_acquisition_tape_npz` (`schema = "lossless_f64_acquisition_tape_v2"`): Lossless binary `.npz` tape contract binding SHA-256 directly to `<f8` dtype, shape, and raw IEEE-754 float64 bytes with fail-closed integrity verification (`0.0` round-trip error and 1-ULP bit-flip tamper rejection verified in `Suite 23`), complementing the compact 5-decimal provenance archive `exp4_acquisition_tapes.json` (`schema = "compact_5dec_provenance_tape_v1"`).
  - `KrigingWorldModel`:
    - Smooth-branch ReLU chain-rule mask $\mathbf{1}[\mu_{q,\text{raw}}(X_{\text{grid}}) > 0]$ (`predict_q_raw_latent_mean`) and dual-channel `(q, b)` posterior cross-covariance projection (`_build_channel_posterior_cov_and_proj`, including exact block-Cholesky Schur conditioning across all 3 channels `(q, b_x, b_y)` on arbitrary off-grid `pending_X` coordinates, verified to `3.55e-15` in `Suite 22`).
    - `select_sequential_conditional_maxvar_probes`: Explicitly separates already-trained `existing_X` from not-yet-fitted `pending_X` (conditioning both `q` and optional `b` channels on `pending_X` before selecting sentinels).
    - `select_sequential_kg_voi_probes`: Supports clean $2 \times 2$ factorial toggles (`include_drift_sensitivity` $\times$ `condition_decision_probes`) while keeping `n_sentinel` `(q + 0.25 b)` sentinels conditioned on all `n_decision` pending probes. Explicitly distinguishes `"value_only_linear_functional_std"` (`max_alt_branches = 0`) from `"pairwise_local_linear_kg_proxy"` (sum-of-pairwise Gaussian opportunity proxy under frozen batch means/branches).
  - `paired_stats`, `welch_two_sample_stats`, & `holm_bonferroni_adjust`: Paired within-unit tests, independent two-sample Welch $t$-tests (for between-regime interactions), and step-down Holm–Bonferroni family-wise error rate adjustment.
- `port_solvers.py`:
  - `SchurPortPlanner`:
    - Unified string-keyed nested partition tree (`"L1" -> "L4" -> "L8" -> "EXACT"`) across 2D and 3D with per-column `operator_epoch` tagging.
    - **Continuous Reciprocal `log1p` Single-Query Enclosure**: Derives continuous $d \ge 0$ value bounds from
      $$0 < \frac{\widetilde{Z}(x) - d}{\gamma_{\text{hi}}} \le Z^*(x) \le \frac{\widetilde{Z}(x) + d}{\gamma_{\text{lo}}},$$
      yielding additive shifts on $\widetilde{V}(x) = -\lambda \log \widetilde{Z}(x)$:
      $$s_{\text{lo}}(x) = \lambda \log \gamma_{\text{lo}} - \lambda \operatorname{log1p}\!\left(\frac{d}{\widetilde{Z}(x)}\right), \qquad s_{\text{hi}}(x) = \lambda \log \gamma_{\text{hi}} - \lambda \operatorname{log1p}\!\left(-\frac{d}{\widetilde{Z}(x)}\right).$$
- `macro_planning.py`:
  - **Recommended Default Macro-Planner (`plan_exact_subset_dp`)**: Single-pass `ExactRing + Subset-DP` is the recommended cold-start default across 2D and 3D (`25^2..31^3`), whereas `plan_economical_hybrid` is scoped to warm micro-perturbation streams (`Suite 19`).
  - **Scatter-Add, True `max_alt_branches = 0`, Bellman-Tie Scope, & Zero-Drift Upwind Kink Contract (`compute_exact_macro_q_sensitivities`)**:
    - Accumulates transition weights via `np.add.at` on `eval_nodes` and `wp_rings` (`5.49e-10` vs central FD on `start_on_ring` & `overlapping_rings`, `Suite 20`).
    - Supports true `max_alt_branches = 0` (`n_alt = 0`), solving **zero extra runner-up transpose RHS columns** (`50%` reduction on 2-branch tasks) while reporting exact `runner_up_wp` and `action_gap` from `Q_root` (`0.0` discrepancy, `Suite 22`).
    - Separates Bellman action ties (`action_tie_detected`, `derivative_kind = "active_branch"`) from upwind operator sign kinks at exact `b == 0` (`upwind_drift_kink_detected`, `n_zero_drift_kink_components`). `zero_drift_mode = "strict_smooth"` guards exact `b == 0` upwind operator kinks only; callers requiring a unique two-sided value-function gradient must also check `not action_tie_detected` (`Suite 23`).
- `highd_solvers.py` & `exp3_highd_and_kinetic.py`:
  - `LOCKED_6D_METHOD_CONFIGS` & `execute_locked_6d_method`: Single canonical factory shared across quality, serial latency, and batch makespan entry points (`0.0` discrepancy verified against frozen `57e5912` records).
- `exp5_response_subspace_diagnostic.py`:
  - Standalone 8-core falsifiable diagnostic (`Exp 5A/5B/5C`) testing cross-task unseen-target Green operator compressibility, reciprocal portal SVD action-ranking preservation, and continual evolving-world Petrov–Galerkin reduced-basis reuse with certified M-matrix fallback against a pre-declared `>= 20%` net wall-clock Go/No-Go gate.

---

## 2. Explicit Claim-Scope, Evidence Grading, & `C2-01..C2-10` Decision Ledger

### 2.1 Claim-Scope & Evidence Grading Table

| Component / Claim | Claim Grade | Scope & Mathematical Guarantee | Empirical / Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Positive-Column M-Matrix Barrier & Continuous `log1p` Residual Enclosure** | **Model-Exact Theorem (`0` violations)** | Discrete M-matrix comparison bounds on $\Omega \setminus \Gamma_b$ + $L_\infty$ residual bound with continuous reciprocal `log1p` shift (`Suite 17`) | `0` violations across `54` sign/overlap probes, `32` signed barrier probes, `625`-node `d1_noop` + `40`-seed `L1/L4/L8` probes, `144` `75^2` tours, `160` crossover tasks, `3,456` `Exp 4B` checks, and `7,200` `Exp 5B` test-task checks |
| **Subset-Macro DP & Cold-vs-Warm Routing (`plan_exact_subset_dp`)** | **Model-Scoped $\varepsilon$-Certified ($O(m^2 2^m)$)** | Certifies $F_{\text{lo}} \le F^* \le J^{\hat{\mu}} \le F_{\text{hi}}$ on learned discrete model; `ExactRing + Subset-DP` is cold-start default | `0 / 37,303` `m=9` 4-way table violations; `ExactRing` wins cold-start `31^3` (`18,691 ms` vs `21,269 ms` `Hybrid`, `p = 0.00438`) |
| **Continual Partition-Structure Memory vs. Residual Column Reuse (`Exp 4B`)** | **Model-Exact Bound + Reused `10250..10261` `0/2/6` Attribution** | Mandatory `cols_retained` contract across `ZeroWarm0`, `PartialWarm2`, `BroadWarm6` under `+16` real observations (`c2c499e`) | `Residual` retains `91.0` (`PartialWarm2`) & `198.2` (`BroadWarm6`) hierarchy level-cols in 3D, yet still needs `1.0` post-update `splu`; **`Structure-Memory` beats `ExactRing` (`-193.4 ms, p = 1.75e-4`) & `Residual` (`p = 1.16e-4`) on warm 3D marginal (`K=12`)**, while tying `ExactRing` from zero (`p = 0.627`) |
| **2x2 Mechanism Factorial (`Exp 4C` Batch B, `32` Revealed Dev Maps)** | **Controlled Causal Mechanism Attribution** | Fixes pending-conditioned `(q + 0.25 b)` sentinels; crosses `q-only vs q+b` decision adjoint $\times$ `Uncond vs Cond` (`10300..10415`) | **Sequential conditioning main effect: `-0.150 +/- 0.067` (`p = 7.63e-5`)**; **incremental `b` decision-sensitivity contrast: `+0.005 +/- 0.023` (`p = 0.643`, unresolved incremental effect; all arms still measure/fit/plan with `b`)** |
| **Locked Fresh Confirmation (`Exp 4C` Batch C, `64` Untouched Maps)** | **Pre-Declared Single-Candidate Confirmation** | `Green-ValueOnly-qb-Cond-11+3` (`max_alt_branches=0`), deferred post-Ep-6 evaluation (`20300..20431`, frozen `c2c499e` run) | **Pooled `64` maps (`Ep 2–6`)**: beats `Global-CondMaxVar-qb` (`-0.234, p_holm = 9.03e-6`) & `OnPolicy-11+CondSentinel-qb-3` (`-0.131, p_holm = 0.0056`), **not confirmed superior to pure `True-OnPolicy-14` (`-0.056, p_holm = 0.147`)**; within Competing-Corridor (`32` maps) `p_holm = 0.0143`, but **direct interaction `Competing - Standard = -0.108` (`p = 0.165` paired / `0.158` Welch) is non-significant** |
| **6D Helmholtz-Bessel Physics-Mean GP Prior (`Exp 3A/3B/3D`)** | **Supporting Analytical Collar Prior + `+5%` NI** | Exact $C^2$ even collar PDE residual ($R = r I$, unconstrained); locked `M1/M2/M3` pipelines (`57e5912`) | `M1_EndToEnd_Bessel24` passes `+5%` Lin-NI vs `M2` (`p_NI <= 0.0107`) & `M3` (`p_NI <= 0.0412`) at **`5.70x` / `14.92x` query-cold serial speedup** (`2.38x` / `5.09x` incl. shared `449.5 ms` world GP) |
| **Cross-Task & Cross-World Low-Rank Response Subspaces (`Exp 5A/5B/5C`)** | **Falsifiable Diagnostic (`NO-GO` Gate Verdict)** | Tests unseen-target PDE source-support obstruction, portal SVD decay, & certified Petrov–Galerkin vs `>= 20%` net savings gate | **`NO-GO` across all 4 streams** (`-81.8%` to `-101.6%` in 2D vs `ExactRing`; `-21.0%` to `-25.5%` from-zero / `-27.1%` to `-34.9%` marginal in 3D vs `Structure-Memory`, `0` bound violations); permanent `ResponseMemory` machinery **not** adopted |

### 2.2 `C2-01..C2-10` Audit Closure & Project Decision Ledger

| ID | Issue / Strategic Question (`greed_kriging_v6`) | Closure & Engineering Decision |
| :--- | :--- | :--- |
| **`C2-01`** | Stale SHA-256 & `Exp 1A` `9400..9407` NI $p$-value in `README.md` | Synced `package_py_sha256 = "7f9d208b7280771642bb3f9142f15dcfd568528b4a6ced94a3df587f927ee6a9"` across all 6 JSONs + `exp4_acquisition_tapes.json` (`sha256 = "41a5b4893cfe9cba372dc615e27ada4a191680ed23d90ba02b90b525f9e57887"`); corrected `Exp 1A` `9400..9407` `SchurPort-r1-LumpedHaz-25` `+3.5%` Lin-NI to **`p_NI = 1.46e-6`** (`1.4555e-6`). |
| **`C2-02`** | Subgroup significance treated as regime dichotomy without interaction test | Added `between_regime_interaction_tests_competing_minus_standard` to `exp4_results.json`: `(G - O)_Competing - (G - O)_Standard = -0.108 +/- 0.155` (`p = 0.165` paired; Welch `p = 0.158`). Reframed exploration lock-in strictly as a **mechanism hypothesis**, not an established between-regime dichotomy. |
| **`C2-03`** | Batch B `b`-sensitivity null (`p = 0.643`) overstated as "proven zero" | Reframed as **unresolved incremental effect** (`q`-only arms still measure `b`, fit `b` GPs, plan upwind `b`, and condition `(q + 0.25 b)` sentinels); `FactB` (`qOnly-Cond`) remains a Batch-B dev configuration without inheriting Batch-C confirmation. |
| **`C2-04`** | `Suite 22` Python ternary precedence bug & 1-channel off-grid check | Replaced ternary with explicit `_eval_s22_gate` (`all(checks.values())`), verified all 3 channels `(q, b_x, b_y)` on off-grid `pending_X` (`<= 3.55e-15`), and added 3 single-condition failure-injection negative controls (`cov`, `proj`, `cols_retained == 0`). |
| **`C2-05`** | 5-decimal JSON tape rounded off-grid coordinates vs 10-decimal hash | Labeled `exp4_acquisition_tapes.json` as `"compact_5dec_provenance_tape_v1"` (`1,440 / 1,440` grid-snapped hashes exact; off-grid batches provide provenance/index membership) and added lossless float64 `.npz` API (`"lossless_f64_acquisition_tape_v2"`, `Suite 23`). |
| **`C2-06`** | Right-censored `112` cap reported as "mean probes to attain" | Added censoring-free `normalized_trapezoidal_cost_auc_28_to_98` & `fraction_unattained_gt_98_probes`, and renamed `112` summary to `bounded_next_step_penalty_score_at_112` (`T > 98` indicator). |
| **`C2-07`** | `Exp 4B` `10250..10261` seed reuse & `cols_retained` hierarchy count | Tagged `cohort_origin = "reused_10250_10261_cohort_with_zero_partial2_broad6_controls"`; documented that `cols_retained = 198.2` counts cached hierarchy level-entries (`L1 + L4 + L8 + EXACT`) on retained waypoints, whereas `Structure-Memory` refreshes `217.7` RHS columns across all remembered waypoints. |
| **`C2-08`** | `strict_smooth` scope vs nonzero-drift Bellman ties & kink-stage count | Documented in `macro_planning.py` and verified in `Suite 23` that `strict_smooth` guards exact `b == 0` upwind kinks (`action_tie_detected` guards Bellman ties separately); tagged Batch B/C kink counts (`0`) as `five_acquisition_stages_ep1_to_ep5_online_adjoint_calls_ep6_has_no_acquisition`. |
| **`C2-09`** | Active-sensing stopping rule (`0` reruns of `c2c499e`) | Frozen `c2c499e` 96-map campaign (`0` reruns, zero tuning on `20300..20431`); claims strictly bounded to confirmed wins vs `Global-CondMaxVar-qb-14` (`p_holm = 9.03e-6`) and `OnPolicy-11+CondSentinel-qb-3` (`p_holm = 0.0056`), unresolved pooled `True-OnPolicy-14` (`p_holm = 0.147`), and `+0.91 s/map` (`1.59x`) coordinate-oracle compute cost. |
| **`C2-10`** | Falsifiable cross-task response-subspace diagnostic before new machinery | Executed `Exp 5` (`16` maps fixed-world + `12` maps $\times$ `4` evolving streams, `0` bound violations): falsified net compute benefit across all 4 streams (`NO-GO` on `>= 20%` gate); **closed response-basis compression line cleanly** in favor of `ExactRing + Subset-DP` (cold) and `Structure-Memory-Fresh-Exact` (warm 3D). |

---

## 3. Verification & Benchmark Summary (`23/23 ALL_PASSED: true`)

All linear-algebra and benchmark runs enforce single-thread BLAS/OpenMP execution per worker (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR = 1`). Every JSON artifact (`audit_closure_results.json`, `exp1_results.json`..`exp5_results.json`, `exp4_acquisition_tapes.json`) embeds synchronized `package_py_sha256 = "7f9d208b7280771642bb3f9142f15dcfd568528b4a6ced94a3df587f927ee6a9"` and explicit `"generating_commit"` provenance tags on inherited blocks. All tables below are populated directly from the JSON artifacts.

### 3.1 Independent 23-Suite Audit Closure Regression (`verify_audit_closure.py`)
- **Suites 1–21**: Full enclosure, epoch, continuous `log1p`, typed `IntervalCertificate`, stale-`EXACT` work-descriptor, `np.add.at` duplicate-node scatter (`5.49e-10`), piecewise-reflected polyline hit (`tau = 0.0861`), rank-1 Schur covariance (`1.55e-15`), and single-step planner-object isolation (`0.0` probe diff) checks pass.
- **Suite 22 (`c2c499e` + `C2-04` Gate Hardening)**:
  - Single-goal exact zero-drift counterexample: `action_tie_detected = False`, `upwind_drift_kink_detected = True` (`562` components), half-ray Richardson FD error **`3.79e-11`** (right), **`2.12e-10`** (left), **`9.12e-11`** (Clarke midpoint), **`6.92e-11`** (mixed-sign direction), and `"strict_smooth"` fails closed (`True`).
  - True `max_alt_branches = 0`: `0.0` gradient/gap discrepancy vs `max_alt_branches = 1` while cutting SuperLU transpose RHS columns from `52` to `26`.
  - Off-grid `pending_X` 3-channel `(q, b_x, b_y)` Schur conditioning: selects candidate `2` on GPT6's 3-candidate SPD counterexample and matches full augmented Cholesky across all 3 channels to **`[3.55e-15, 7.81e-18, 3.38e-17]`** (`cov`) and **`[3.55e-15, 1.04e-17, 7.89e-17]`** (`proj`).
  - Explicit `_eval_s22_gate` (`all(checks.values())`) verified with 3 single-condition failure-injection negative controls (`cov_err -> False`, `proj_err -> False`, `pos_cols_retained == 0 -> False`).
- **Suite 23 (`C2-05` & `C2-08` Lossless `.npz` Tape & Bellman-Tie Scope Audit)**:
  - Lossless float64 `.npz` tape (`lossless_f64_acquisition_tape_v2`): `0.0` round-trip discrepancy on both grid and irrational off-grid trajectory batches (`offgrid_indices_exact_match = True`) and fail-closed rejection of a 1-ULP float64 bit-flip (`one_ulp_tamper_rejected = True`).
  - Symmetric nonzero-drift Bellman tie (`b != 0`): verifies `upwind_drift_kink_detected = False`, `action_tie_detected = True`, and `derivative_kind = "active_branch"`.

---

### 3.2 Experiments 1 & 2 (Frozen Supporting Provenance Blocks)
- **Exp 1A (`ddd19c5`)**: On the locked fresh confirmation cohort `9400..9407` (`25^3`, `K = 40`), `SchurPort-r1-LumpedHaz-25` (`2,078.6 ms`, `+3.5%` Lin-NI **`p_NI = 1.46e-6`**; 12-map development cohort `p_NI = 3.5e-4`) is `14.86x` faster than `Fresh-FD-25` (`30,888 ms`) and `1.42x` faster than matched `Warm-ILU-LumpedHaz` (`2,957 ms`, `p = 0.0218`).
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

### 3.4 Experiment 4: Fidelity Bridge, Genuine GP Lifecycle, `2x2` Mechanism Factorial, & `64`-Map Confirmation (`exp4_results.json`)

#### Exp 4A — Coupled-Wiener Fidelity Bridge (`72` Tours on `9900..9911`, `generating_commit = "29fa7c6"`)
- `0 / 72` bound violations, `100%` root-action agreement; mean `|ΔJ|`: `L1` port (`0.0056`) << `L2c` `dt=0.005` piecewise-reflected polyline hit (`0.3432`, coupled `dt` effect `-0.2687, p < 1e-6`) < `L3` True-world vs GP mismatch (`0.8598`).

#### Exp 4B — Genuine `+16` Physical-Probe GP Refit Lifecycle (`12` Reused Maps `10250..10261`, `generating_commit = "c2c499e"`)
- Appends `+16` real `(q, b)` observations (`64 -> 80` in 2D, `80 -> 96` in 3D) and refits Kriging posteriors across `0`, `2`, and `6` warmup tasks on the reused `10250..10261` 12-map cohort (`0 / 3,456` bound violations across all maps/methods/tasks).
- **Hierarchy Level-Entry Accounting (`cols_retained`)**: `u_inf["cols_retained"]` counts retained column entries across all cached hierarchy levels (`L1 + L4 + L8 + EXACT`) on retained waypoints (`7.8` / `15.3` in 2D, `91.0` / `198.2` in 3D for `PartialWarm2 / BroadWarm6`), whereas `Structure-Memory-Fresh-Exact` batch-solves `217.7` leaf RHS columns across all remembered waypoints under `splu(A_new)` and reconstructs coarser levels by summation:

| Regime (`N_warm` Tasks, `K = 12`) | Scope | `Scratch-Rebuild` | `Structure-Memory-Fresh-Exact` | `Residual-Audited-Reuse` | `ExactRing-Rebuild` | Retained Hierarchy Entries (`Resid`) | Key Paired Contrast (`K = 12`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `2D-61sq-ZeroWarm0` (`0`) | Post-Update Marginal | `483.7 ms` | `475.1 ms` | `486.9 ms` | **`220.4 ms`** | `0.0` | `Struct - Exact`: `+254.8 +/- 17.7 ms` (`p=3.62e-12`); `Resid - Struct`: `p=0.2774` |
| `2D-61sq-PartialWarm2` (`2`) | Post-Update Marginal | `475.1 ms` | `388.0 ms` | `391.6 ms` | **`213.5 ms`** | `7.8` | `Struct - Exact`: `+174.6 +/- 13.2 ms` (`p=9.56e-12`); `Resid - Struct`: `p=0.4577` |
| `2D-61sq-BroadWarm6` (`6`) | Post-Update Marginal | `472.1 ms` | `285.7 ms` | `280.5 ms` | **`204.6 ms`** | `15.3` | `Struct - Exact`: `+81.1 +/- 12.2 ms` (`p=1.51e-08`); `Resid - Struct`: `p=0.3695` |
| `3D-21cubed-ZeroWarm0` (`0`) | Post-Update Marginal | `1605.7 ms` | `1586.8 ms` | `1525.4 ms` | **`1333.1 ms`** | `0.0` | `Struct - Exact`: `+253.7 +/- 45.6 ms` (`p=9.37e-08`); `Resid - Struct`: `p=0.1303` |
| `3D-21cubed-PartialWarm2` (`2`) | Post-Update Marginal | `1661.6 ms` | `1500.9 ms` | `1592.3 ms` | **`1453.3 ms`** | `91.0` | `Struct - Exact`: `+47.6 +/- 119.5 ms` (`p=0.3997`); `Resid - Struct`: `p=0.1240` |
| **`3D-21cubed-BroadWarm6` (`6`)** | **Post-Update Marginal** | `1553.5 ms` | **`1111.7 ms`** | `1375.2 ms` | `1305.1 ms` | `198.2` | **`Struct - Exact`: `-193.4 +/- 76.8 ms` (`p=0.0002`); `Resid - Struct`: `p=0.0001`** |
| `3D-21cubed-BroadWarm6` (`6`) | From-Zero Full Lifecycle | `3024.1 ms` | `2544.3 ms` | `2890.4 ms` | `2580.8 ms` | `198.2` | `Struct - Exact` (from zero): `-36.4 +/- 160.3 ms` (`p=0.6269`, tied) |

#### Exp 4C Batch B — Development `2 x 2` Mechanism Factorial (`32` Revealed Maps `10300..10415`, `generating_commit = "c2c499e"`)
- Evaluates `q-only vs q+b` Green decision sensitivity $\times$ `Unconditioned vs Sequentially Conditioned` decision probes (`max_alt_branches = 0`), holding pending-conditioned `(q + 0.25 b)` sentinels fixed across all 4 factorial arms (`0.0` Ep-1 spread; `0` exact zero-drift kinks across the `5` online acquisition stages `Episodes 1–5`, as `Episode 6` executes no acquisition):

| Arm (`32` Dev Maps `10300..10415`, Deferred Eval) | Standard `16` (`Ep 2–6`) | Competing `16` (`Ep 2–6`) | Pooled `32` (`Ep 2–6`) | Pooled `FactD - Arm` (`95% CI`, `p`) | Acq / Operational / Sim(excl) ms |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Global-CondMaxVar-qb-14` | `11.159` | `8.287` | `9.723` | **`-0.267 +/- 0.091`** (`p=1.19e-06`) | `386.8` / `1532.8` / `1854.0` |
| `True-OnPolicy-14` | `11.098` | `8.121` | `9.609` | **`-0.153 +/- 0.109`** (`p=0.0075`) | `324.1` / `1454.8` / `1906.1` |
| `True-OnPolicy-11+CondSentinel-qb-3` | `11.188` | `8.183` | `9.686` | **`-0.230 +/- 0.111`** (`p=0.0002`) | `415.4` / `1559.7` / `1967.5` |
| `FactA-GreenVal-qOnly-Uncond` | `11.069` | `8.132` | `9.601` | `-0.145 +/- 0.066` (`p=9.19e-05`) | `791.5` / `1890.2` / `1797.3` |
| **`FactB-GreenVal-qOnly-Cond`** | `10.931` | **`7.988`** | **`9.460`** | `-0.004 +/- 0.035` (`p=0.8295`) | `820.9` / `1962.5` / `1904.0` |
| `FactC-GreenVal-qb-Uncond` | `11.068` | `8.162` | `9.615` | `-0.159 +/- 0.073` (`p=0.0001`) | `1194.0` / `2319.8` / `1867.7` |
| **`FactD-GreenVal-qb-Cond`** | **`10.900`** | `8.012` | **`9.456`** | — | `1159.7` / `2261.3` / `1871.3` |

- **Exact `2 x 2` Factorial Attribution & Scope**:
  1. **Main effect of sequential Schur conditioning (`0.5 * [(B - A) + (D - C)]`)**: **`-0.150 +/- 0.067` (`p = 7.63e-5`)** (`B - A = -0.141, p = 1.47e-4`; `D - C = -0.159, p = 1.09e-4`).
  2. **Incremental `b` decision-sensitivity contrast (`0.5 * [(C - A) + (D - B)]`)**: **`+0.005 +/- 0.023` (`p = 0.643`, unresolved incremental effect)**; interaction **`-0.018 +/- 0.039` (`p = 0.353`)**. Note that `q`-only arms still measure `b`, fit `b` GPs, plan upwind drift `b`, and weight `(q + 0.25 b)` sentinels; `FactB` (`820.9 ms` acq vs `1,159.7 ms` `FactD`) remains a Batch-B development configuration and does not inherit Batch-C fresh confirmation.

#### Exp 4C Batch C — Locked Fresh Confirmation on `64` Untouched Maps (`20300..20331` Standard + `20400..20431` Competing-Corridor, `generating_commit = "c2c499e"`)
- Evaluates the single pre-declared candidate `Green-ValueOnly-qb-Cond-11+3` (`max_alt_branches = 0`) once on `64` untouched maps (`0.0` Ep-1 spread, `100%` tour completion, `0` zero-drift kinks across `Episodes 1–5`; compact 5-decimal provenance archive in `exp4_acquisition_tapes.json`, `schema = "compact_5dec_provenance_tape_v1"`, SHA-256 `41a5b4893cfe9cba...`):

| Arm (`64` Untouched Maps `20300..20431`, Deferred Eval) | Standard `32` (`Ep 2–6`) | Competing `32` (`Ep 2–6`) | Pooled `64` (`Ep 2–6`) | Pooled `GreenVal - Arm` (`95% CI`) | `p_nom` / `p_holm` (`3`-Ref Family) | Trap. Cost AUC (`28..98`) / Attained `>=6%` by `98` (`Pen@112`) | Acq / Oper / Sim(excl) / Eval ms |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Frozen-GP-28` | `11.942` | `8.707` | `10.325` | `-1.209 +/- 0.241` | `1.05e-14` (anchor) | `10.325` / `0.0%` (`112.0`) | `0.0` / `376.6` / `1890.2` / `773.3` |
| `Global-CondMaxVar-qb-14` | `10.526` | `8.172` | `9.349` | **`-0.234 +/- 0.091`** | `3.01e-06` / **`9.03e-06`** | `9.481` / `79.7%` (`71.1`) | `395.5` / `1618.6` / `2045.1` / `4765.9` |
| `True-OnPolicy-11+CondSentinel-qb-3` | `10.453` | `8.041` | `9.247` | **`-0.131 +/- 0.084`** | `0.0028` / **`0.0056`** | `9.384` / `81.2%` (`67.8`) | `448.0` / `1707.4` / `2163.6` / `4733.1` |
| `True-OnPolicy-14` | `10.340` | `8.002` | `9.171` | `-0.056 +/- 0.076` | `0.1470` / **`0.1470`** | `9.318` / `89.1%` (`63.0`) | `331.9` / `1543.6` / `2072.6` / `4606.3` |
| **`Green-ValueOnly-qb-Cond-11+3`** | **`10.338`** | **`7.892`** | **`9.115`** | — | — | **`9.273`** / **`92.2%`** (`60.8`) | `1222.9` / `2452.9` / `2061.5` / `4809.9` |

*(Note: `Pen@112` is `bounded_next_step_penalty_score_at_112`, encoding unattained maps `T > 98` at `112` as a bounded penalty score rather than expected probe count; `Attained >=6% by 98` and `Trap. Cost AUC (28..98)` are completely uncensored.)*

- **Disciplined Confirmatory Conclusions & Direct Interaction Test (`C2-02`, `C2-09`)**:
  1. **Pooled `64`-Map Primary Endpoint (`Ep 2–6`)**: Under equal coordinate-oracle budgets (`28 -> 98` physical probes), `Green-ValueOnly-qb-Cond-11+3` **significantly beats `Global-CondMaxVar-qb-14` (`p_holm = 9.03e-6`) and equal-quota `True-OnPolicy-11+CondSentinel-qb-3` (`p_holm = 0.0056`)**, and **does not establish pooled superiority over pure `True-OnPolicy-14` (`-0.056 +/- 0.076, p_holm = 0.147`; exploratory `Ep 6` `98`-probe contrast `-0.108 +/- 0.080, p_nom = 0.0092`)**, while incurring `+909.3 ms/map` (`2,452.9` vs `1,543.6 ms`, `1.59x`) higher operational compute.
  2. **Subgroup Contrasts & Gelman–Stern Direct Interaction Test**:
     - Within `Standard Narrow-Barrier` (`32` maps `20300..20331`), `Green` (`10.338`) beats `Global-CondMaxVar-qb-14` (`10.526`, `p_holm = 0.0346`) and ties `True-OnPolicy-14` (`10.340`, `-0.002 +/- 0.127, p = 0.977`).
     - Within `Competing-Corridor` (`32` maps `20400..20431`), `Green` (`7.892`) beats all 3 baselines after within-stratum Holm adjustment (`vs Global-CondMaxVar: -0.280, p_holm = 1.22e-4`; `vs OnPolicy-11+CondSent-3: -0.148, p_holm = 0.00279`; `vs Pure OnPolicy-14: -0.110 +/- 0.086, p_holm = 0.0143`).
     - **Direct Between-Regime Interaction (`Competing - Standard`)**: For `Green - Pure OnPolicy-14`, the direct difference-of-differences is **`-0.108 +/- 0.155` (`95% CI [-0.263, +0.047]`, `p = 0.165` across `32` shared-noise pairs; independent Welch `t`-test `df = 54.5, p = 0.158`)** (`vs Global-CondMaxVar: -0.093, p = 0.293`; `vs OnPolicy-11+CondSent-3: -0.034, p = 0.693`). Because the interaction itself is not statistically significant at `n = 32 + 32`, between-regime heterogeneity is **not** statistically confirmed, and exploration lock-in on competing passages is reported strictly as a **plausible mechanism hypothesis** rather than an established dichotomy.

---

### 3.5 Experiment 5: Falsifiable Cross-Task & Cross-World Response-Subspace Diagnostic (`exp5_results.json`, `exp5_response_subspace.png`)

Answers `C2-10` under identical world models, task specifications, strict M-matrix positivity (`U_stored - err_ub > 0`), 4-way Subset-DP `eps_tol = 0.25` certification (`0` bound violations across all `1,440` audited test tasks per method), and 100% from-zero compute accounting against a pre-declared **`>= 20%` net wall-clock savings Go/No-Go gate**:

#### Exp 5A — Fixed-World Unseen-Target Obstruction & Reciprocal Portal SVD (`16` Maps: `30100..30107` Standard + `30200..30207` Competing, `2D 51^2`)
1. **Seen-Catalog Subsets vs. Unseen Target Locations**:
   - On new subset combinations of already-cataloged waypoints, `ExactRing` column caching already solves `12` `m = 4` tours in **`14.3 ms` total** (`~1.2 ms/task`, vs **`40.5 ms`** from zero on `12` genuinely unseen targets), leaving no compute bottleneck for approximate compression on seen targets.
   - **Elliptic PDE Source-Support Obstruction**: Historical Green columns $\phi_k = A_0^{-1} e_j$ ($j \in \Gamma_{\text{train}}$) satisfy $(A_0 \phi_k)_i = 0$ on $\Omega \setminus \Gamma_{\text{train}}$. Consequently, projecting any disjoint unseen target $\Gamma_{\text{new}}$ onto historical interior-harmonic columns yields **`min ||E_{Gamma_new} - A_0 U_hat||_inf = 1.000`** (**`0.0%` M-matrix certification** across all `16` maps).
2. **Reciprocal Evaluation-Portal Green Operator (`G_portal = (A_0^{-1})[portal_nodes, :]`) Spectral Decay**:
   - Because elliptic Green's functions exhibit localized diagonal boundary singularities, singular values decay slowly: capturing `90%`, `99%`, and `99.9%` of Frobenius energy requires **`r = 54.6`**, **`114.2`**, and **`127.1`** out of **`128.6`** full-rank portals (offline portal solve `29.7 ms`).
   - Low-rank truncation suffers substantial root optimal-action disagreement—especially on near-tie tasks (`action_gap < 0.25`):

| Subspace Rank `r` (`16` Maps, `192` Unseen-Target `m=4` Tours) | `Standard POD` Root `||ΔQ||_inf` | `Task-Weighted SVD` Root `||ΔQ||_inf` | `Standard POD` Top-1 / Near-Tie Agree | `Task-Weighted SVD` Top-1 / Near-Tie Agree | `Standard POD` Mean Regret | `Task-Weighted SVD` Mean Regret |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `r = 4` | `12.43` | `13.09` | `35.9%` / `38.9%` | `32.3%` / `21.1%` | `1.233` | `1.327` |
| `r = 8` | `14.13` | `14.12` | `37.0%` / `40.4%` | `38.5%` / `37.1%` | `1.069` | `1.124` |
| `r = 16` | `15.05` | `14.93` | `38.5%` / `20.7%` | `36.5%` / `26.1%` | `0.943` | `1.003` |
| `r = 32` | `15.19` | `15.20` | `50.0%` / `16.8%` | `58.3%` / `41.8%` | `0.595` | `0.466` |
| `r = 64` | `14.14` | `14.11` | `64.1%` / `40.4%` | `68.2%` / `24.6%` | `0.336` | `0.255` |

#### Exp 5B & 5C — Continual Evolving-World Certified Petrov–Galerkin vs. Classical Baselines (`12` Maps `30300..30311`, `0` Bound Violations)
- Compares pooled `POD-Galerkin-Certified` (`L_2` SVD) and per-column $L_\infty$-IRLS `TaskWeighted-Galerkin-Certified` (assembling `A_new` lazily without upfront `splu`, enforcing `U_stored - err_ub > 0`, and feeding `err_ub = (lam / q_min) ||E - A_new U_stored||_inf` into 4-way Subset-DP `eps_tol = 0.25` certification with automatic `ExactRing` fallback) against `ExactRing-Rebuild`, `Structure-Memory-Fresh-Exact`, and `Residual-Audited-Rank0` across both **Realistic `+12` GP-Probe Streams** (`1` init + `5` test updates) and **Low-Dim `2`-Mode Parametric Hazard Streams** (`3` calibration + `5` test updates):

| Stream Regime (`12` Maps `30300..30311`, `0` Bound Viols) | `ExactRing-Rebuild` (From-Zero / Test Marg) | `Structure-Memory` (From-Zero / Test Marg) | `Residual-Rank0` (From-Zero / Test Marg) | `POD-Galerkin+Cert` (From-Zero / Test Marg / Pre-DP Cert%) | `TaskWt-Galerkin+Cert` (From-Zero / Test Marg / Pre-DP Cert%) | `>= 20%` Net Go/No-Go Verdict (vs Best Classical) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `2D-51sq_RealisticGPStream` | **`349.2`** / **`284.8 ms`** | `636.5` / `420.5 ms` | `664.5` / `440.9 ms` | `800.1` / `741.8 ms` (`16.7%`) | `634.9` / `571.6 ms` (`45.2%`) | **`NO-GO`** (`-81.8%` fz / `-100.7%` marg) |
| `2D-51sq_LowDimParametricStream` | **`419.1`** / **`250.1 ms`** | `725.6` / `350.7 ms` | `821.0` / `432.4 ms` | `1106.0` / `893.2 ms` (`100.0%`) | `845.0` / `648.8 ms` (`100.0%`) | **`NO-GO`** (`-101.6%` fz / `-159.4%` marg) |
| `3D-21cubed_RealisticGPStream` | `10009.8` / `8365.0 ms` | **`9418.1`** / **`7669.1 ms`** | `10165.5` / `8365.6 ms` | `12788.4` / `11132.5 ms` (`0.0%`) | `11395.2` / `9747.6 ms` (`73.1%`) | **`NO-GO`** (`-21.0%` fz / `-27.1%` marg) |
| `3D-21cubed_LowDimParametricStream` | `12999.8` / `8183.8 ms` | **`11755.5`** / **`7086.4 ms`** | `13181.4` / `8187.9 ms` | `17989.2` / `12563.5 ms` (`22.1%`) | `14747.5` / `9557.0 ms` (`100.0%`) | **`NO-GO`** (`-25.5%` fz / `-34.9%` marg) |

- **Why Low-Rank Certified Subspaces Fail the Net-Benefit Gate (`C2-10` Diagnostic Conclusion)**:
  1. Per-column $L_\infty$-IRLS Petrov–Galerkin (`TaskWeighted-Galerkin-Certified`) genuinely raises **pre-DP column positivity certification** from `0.0% -> 73.1%` (`3D Realistic GP`) and `22.1% -> 100.0%` (`3D Low-Dim Parametric`) with `0` bound violations.
  2. **However**, any nonzero M-matrix column error bound `err_ub > 0` gets multiplied by `|P_pinv @ F|` (`m_b ~ 80` ring nodes in 3D), amplified by `-lam * log(Z_bar_lo)`, and compounded across `m = 4` Bellman legs—exceeding `eps_tol = 0.25` on `~21.2–22.2 / 30` test tasks per map and forcing automatic `ExactRing` `splu` fallback (`5.0 / 5.0` test-epoch LU factorizations). Charging `1.11s–1.73s` (`TaskWt`) or `2.72s–4.47s` (`POD`) of subspace/residual-audit overhead on top of fallback makes low-rank response memory **strictly net-negative across all four regimes**.
  3. Conversely, **zero-residual `Structure-Memory-Fresh-Exact`** (`col_err == 0` by batch-solving only the remembered `L1/L4/L8/EXACT` partition layout under `splu(A_new)`) beats `ExactRing-Rebuild` in 3D on both streams (`+5.9%` / `+9.6%` from zero; `+8.3%` / `+13.4%` post-calibration marginal, `0` bound violations, `< 9e-5` regret). Per the pre-declared stopping rule, **no permanent low-rank `ResponseMemory` solver layer is added**.

---

## 4. Reproducible Execution Commands

```bash
# 1. Run all 23 independent audit & counterexample suites (single-threaded)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/verify_audit_closure.py

# 2. Run Experiments 1–5 (8-core map-parallel with per-worker single-thread BLAS pinning)
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp1_3d_and_macro_tours.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp2_nonlmdp_kkt.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp3_highd_and_kinetic.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp4_fidelity_and_continual.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 green_response/exp5_response_subspace_diagnostic.py
```
