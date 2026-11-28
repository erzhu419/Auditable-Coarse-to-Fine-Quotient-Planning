# `green_response`: Auditable Coarse-to-Fine Green Response Planning & Goal-Oriented World-Model Sensing

Canonical modular library and benchmark suite closing all findings across `7087ec3`, `85e2323`, `ddd19c5`, `d1b926a`, `29fa7c6`, `57e5912`, `c2c499e`, `efde60c`, and `314a88b` (`green_kriging_v8` final release-freeze closure `R314-01..R314-05`). All active solvers, independent counterexample regression probes (`24` suites), replayable acquisition tapes, and reproducible benchmarks (`Experiments 1–5`) live in `green_response/`; historical snapshots (`green_kriging_mvp/`, `green_kriging_v2/`, `green_kriging_v3/`, `green_kriging_v4/`) remain frozen for provenance.

---

## 1. Module Architecture, Hardened Contracts, & Provenance Manifests

- `core.py`:
  - `ProblemSpec`: Enforces explicit LMDP capability guards (`validate_cole_hopf_lmdp`) at solver entry and constructs `as_isotropic_unconstrained_surrogate()` warm-starts.
  - `IntervalCertificate`: Machine-auditable fail-closed certificate contract (`__post_init__` validates allowed `status`, finite ordered `lower_bound <= upper_bound`, `gap <= epsilon_tol` on `"epsilon_certified"`, non-negative `operator_epoch`, explicit `certificate_kind` in `{"policy_and_value_enclosure", "value_only_enclosure"}`, strict `_validate_typed_policy_entry` rejecting `None`, empty `{}` / `()` / empty `ndarray`, and non-callables when `certified=True` unless `allow_value_only=True`, and blocks `extras` from overriding protected fields).
  - `compute_source_manifest` & `collect_runtime_metadata`: Embeds `git_head_sha`, `git_dirty_green_response`, `package_py_sha256`, and `per_file_sha256` across every result JSON alongside explicit per-block `"block_provenance"` and `"generating_commit"` tags (`"85e2323"`, `"ddd19c5"`, `"29fa7c6"`, `"57e5912"`, `"c2c499e"`, `"314a88b"`).
  - `save_lossless_acquisition_tape_npz` & `load_and_verify_lossless_acquisition_tape_npz` (`schema = "lossless_f64_acquisition_tape_v2"`): Full record-level lossless binary `.npz` tape contract enforcing schema whitelist, `(X:(n,d), q:(n,), b:(n,d))` row/dimension consistency, `len(onpolicy_traj_indices) <= n` leading-row convention with fail-closed `onpolicy_index_row_convention` validation (`"ordered_step_indices_for_leading_onpolicy_rows_0_to_k_minus_1"` when indices are present else `"none"`, rejecting mismatched conventions such as `"trailing_rows"`, `R314-05`), and exact `<f8` / `<i8` byte SHA-256 digests across `X`, `q`, `b`, and `onpolicy_traj_indices` (`Suite 23`), complementing the compact 5-decimal provenance archive `exp4_acquisition_tapes.json` (`schema = "compact_5dec_provenance_tape_v1"`).
  - `KrigingWorldModel`:
    - Smooth-branch ReLU chain-rule mask $\mathbf{1}[\mu_{q,\text{raw}}(X_{\text{grid}}) > 0]$ (`predict_q_raw_latent_mean`) and dual-channel `(q, b)` posterior cross-covariance projection (`_build_channel_posterior_cov_and_proj`, including exact block-Cholesky Schur conditioning across all 3 channels `(q, b_x, b_y)` on arbitrary off-grid `pending_X` coordinates, verified to `3.55e-15` in `Suite 22`).
    - `select_sequential_conditional_maxvar_probes` & `select_sequential_kg_voi_probes`: Separates trained `existing_X` from unfitted `pending_X` and supports clean $2 \times 2$ factorial toggles (`include_drift_sensitivity` $\times$ `condition_decision_probes`).
  - `paired_stats`, `welch_two_sample_stats`, & `holm_bonferroni_adjust`: Paired within-unit tests, independent two-sample Welch $t$-tests, and step-down Holm–Bonferroni FWER adjustment.
- `port_solvers.py`:
  - `SchurPortPlanner`:
    - Unified string-keyed nested partition tree (`"L1" -> "L4" -> "L8" -> "EXACT"`) across 2D and 3D with per-column `operator_epoch` tagging.
    - **Continuous Reciprocal `log1p` Single-Query Enclosure**: Derives continuous $d \ge 0$ value bounds from
      $$0 < \frac{\widetilde{Z}(x) - d}{\gamma_{\text{hi}}} \le Z^*(x) \le \frac{\widetilde{Z}(x) + d}{\gamma_{\text{lo}}},$$
      yielding additive shifts on $\widetilde{V}(x) = -\lambda \log \widetilde{Z}(x)$:
      $$s_{\text{lo}}(x) = \lambda \log \gamma_{\text{lo}} - \lambda \operatorname{log1p}\!\left(\frac{d}{\widetilde{Z}(x)}\right), \qquad s_{\text{hi}}(x) = \lambda \log \gamma_{\text{hi}} - \lambda \operatorname{log1p}\!\left(-\frac{d}{\widetilde{Z}(x)}\right).$$
- `macro_planning.py`:
  - **Recommended Default Macro-Planner (`plan_exact_subset_dp`)**: Single-pass `ExactRing + Subset-DP` is the recommended cold-start and 2D default across `25^2..31^3`. `plan_economical_hybrid` includes terminal operational same-cache `plan_exact_subset_dp` closure whenever `plan_subset_macro_policy` stops with `status == "unresolved"` (`Suite 24`), preserving disaggregated `port_stage_work` and `exact_stage_work` sub-stage dicts and computing explicit additive two-stage `work_done` totals (`col_solve_ms`, `dp_ms`, `occupancy_ms`, `selection_ms`, `controller_ms`, `dp_calls`, `new_lu_backsolves`, `planning_ms`) without summing non-additive memory/table-size fields (`R314-02`), while keeping `numeric_invalid` strictly fail-closed.
  - **Scatter-Add, True `max_alt_branches = 0`, Bellman-Tie Scope, & Zero-Drift Upwind Kink Contract (`compute_exact_macro_q_sensitivities`)**:
    - Accumulates transition weights via `np.add.at` on `eval_nodes` and `wp_rings` (`5.49e-10` vs central FD, `Suite 20`).
    - Supports true `max_alt_branches = 0` (`n_alt = 0`), solving zero extra runner-up transpose RHS columns (`50%` reduction on 2-branch tasks, `Suite 22`).
    - Separates Bellman action ties (`action_tie_detected`, `derivative_kind = "active_branch"`) from upwind operator sign kinks at exact `b == 0` (`upwind_drift_kink_detected`); `zero_drift_mode = "strict_smooth"` guards exact `b == 0` upwind kinks only (`Suite 23`).
- `highd_solvers.py` & `exp3_highd_and_kinetic.py`:
  - `LOCKED_6D_METHOD_CONFIGS` & `execute_locked_6d_method`: Single canonical factory shared across quality, serial latency, and batch makespan entry points (`0.0` discrepancy verified against frozen `57e5912` records).
- `exp5_response_subspace_diagnostic.py`:
  - Standalone 8-core falsifiable diagnostic (`Exp 5A/5B/5C`, `v7` `A1–A3` + `v8` `R314-01..R314-04` hardened) testing fixed-source algebraic support obstruction, known-portal SVD truncation with exact-portal unclipped sanity control (`max |ΔQ| = 7.11e-15`), separate raw vs clipped `Z > 1` row diagnostics, an oracle-assisted exact-self-block ablation of global portal SVD (`LocalExactSelf_CrossPortalSVD`), and continual evolving-world `POD-SharedRank-Galerkin` vs `Colwise-RegIRLS-Galerkin` under `100%` (`1,440 / 1,440`) $\varepsilon$-certification against a pre-declared `>= 20%` net planner-lifecycle savings gate.

---

## 2. Explicit Claim-Scope, Evidence Grading, & Final Decision Ledgers

### 2.1 Claim-Scope & Evidence Grading Table

| Component / Claim | Claim Grade | Scope & Mathematical Guarantee | Empirical / Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Positive-Column M-Matrix Barrier & Continuous `log1p` Residual Enclosure** | **Model-Exact Theorem (`0` violations)** | Discrete M-matrix comparison bounds on $\Omega \setminus \Gamma_b$ + $L_\infty$ residual bound with continuous reciprocal `log1p` shift (`Suite 17`) | `0` violations across `54` sign/overlap probes, `32` signed barrier probes, `625`-node `d1_noop` + `40`-seed `L1/L4/L8` probes, `144` `75^2` tours, `160` crossover tasks, `3,456` `Exp 4B` checks, and `7,200` `Exp 5B` test-task checks |
| **Subset-Macro DP & Cold-vs-Warm Routing (`plan_exact_subset_dp`)** | **Model-Scoped $\varepsilon$-Certified ($O(m^2 2^m)$)** | Certifies $F_{\text{lo}} \le F^* \le J^{\hat{\mu}} \le F_{\text{hi}}$ on learned discrete model; `ExactRing + Subset-DP` is cold-start default | `0 / 37,303` `m=9` 4-way table violations; `ExactRing` wins cold-start `31^3` (`18,691 ms` vs `21,269 ms` `Hybrid`, `p = 0.00438`) |
| **Continual Partition-Structure Memory vs. Residual Column Reuse (`Exp 4B`)** | **Model-Exact Bound + Reused `10250..10261` `0/2/6` Attribution** | Mandatory `cols_retained` contract across `ZeroWarm0`, `PartialWarm2`, `BroadWarm6` under `+16` real observations (`c2c499e`) | `Residual` retains `91.0` (`PartialWarm2`) & `198.2` (`BroadWarm6`) hierarchy level-cols in 3D, yet still needs `1.0` post-update `splu`; **`Structure-Memory` beats `ExactRing` (`-193.4 ms, p = 1.75e-4`) & `Residual` (`p = 1.16e-4`) on warm 3D marginal (`K=12`)**, with an inconclusive from-zero lifecycle difference (`−36.4 ms, 95% CI [−196.7, +123.9], p = 0.627`) |
| **2x2 Mechanism Factorial (`Exp 4C` Batch B, `32` Revealed Dev Maps)** | **Controlled Causal Mechanism Attribution** | Fixes pending-conditioned `(q + 0.25 b)` sentinels; crosses `q-only vs q+b` decision adjoint $\times$ `Uncond vs Cond` (`10300..10415`) | **Sequential conditioning main effect: `-0.150 +/- 0.067` (`p = 7.63e-5`)**; **incremental `b` decision-sensitivity contrast: `+0.005 +/- 0.023` (`p = 0.643`, unresolved incremental effect; all arms still measure/fit/plan with `b`)** |
| **Locked Fresh Confirmation (`Exp 4C` Batch C, `64` Untouched Maps)** | **Pre-Declared Single-Candidate Confirmation** | `Green-ValueOnly-qb-Cond-11+3` (`max_alt_branches=0`), deferred post-Ep-6 evaluation (`20300..20431`, frozen `c2c499e` run) | **Pooled `64` maps (`Ep 2–6`)**: beats `Global-CondMaxVar-qb` (`-0.234, p_holm = 9.03e-6`) & `OnPolicy-11+CondSentinel-qb-3` (`-0.131, p_holm = 0.0056`), **not confirmed superior to pure `True-OnPolicy-14` (`-0.056, p_holm = 0.147`)**; within Competing-Corridor (`32` maps) `p_holm = 0.0143`, while **direct interaction `Competing - Standard = -0.108` (`p = 0.165` paired / `0.158` Welch) is non-significant** |
| **6D Helmholtz-Bessel Physics-Mean GP Prior (`Exp 3A/3B/3D`)** | **Supporting Analytical Collar Prior + `+5%` NI** | Exact $C^2$ even collar PDE residual ($R = r I$, unconstrained); locked `M1/M2/M3` pipelines (`57e5912`, incl. `100` shared probes & `1,266` internal FK paths) | `M1_EndToEnd_Bessel24` passes `+5%` Lin-NI vs `M2` (`p_NI <= 0.0107`) & `M3` (`p_NI <= 0.0412`) at **`5.70x` / `14.92x` query-cold serial speedup** (`2.38x` / `5.09x` incl. shared `449.5 ms` world GP) |
| **Tested Low-Rank Response-Subspace Prototypes (`Exp 5A/5B/5C`)** | **Falsifiable Diagnostic (`NO-GO` Gate Verdict)** | Tests fixed-source linear span + known-portal SVD + `POD-SharedRank` & `Colwise-RegIRLS` under `1,440 / 1,440` (`100%`) $\varepsilon$-certification | **`NO-GO` across all 4 streams** (`-86.8%` & `-100.8%` in 2D vs `ExactRing`; `-17.5%` & `-33.5%` planner-lifecycle / `-21.8%` & `-51.8%` test marginal in 3D vs `Structure-Memory`, `0` violations); scoped to tested constructions (does not rule out all future decision-directed or local-lifting abstractions) |

### 2.2 Final Project Decision Ledger (`C2-01..C2-10`, `EF-D01..EF-D12`, & `R314-01..R314-05`)

| ID | Governance / Scope Rule | Final Locked Resolution |
| :--- | :--- | :--- |
| **`EF-D01` (`C2-01, C2-02, C2-06, C2-09, R314-05`)** | Frozen `96`-map campaign & primary endpoint hierarchy | Frozen `c2c499e` `96`-map active-sensing campaign (`0` reruns); `Batch C` pooled `Ep 2–6` cost remains primary confirmatory endpoint (`p_holm = 9.03e-6` vs `Global-CondMaxVar`, `0.0056` vs `OnPolicy-11+Sent-3`, `0.147` unresolved vs `True-OnPolicy-14`); trapezoidal AUC, attainment rates, and interaction (`p = 0.165` paired / `0.158` Welch) are post-hoc descriptive/diagnostic analyses; `Exp 1A` cohort NI $p$-values aligned to `exp1_results.json` (`9400..9407` fresh `8`-map `p_NI = 1.46e-6`, `heldout 6` `p_NI = 3.5e-4`, `all 12` `p_NI = 8.12e-9`). |
| **`EF-D02` (`C2-10`)** | Permanent low-rank `ResponseMemory` layer | **Stopped (`NO-GO`)** for the current architecture, bounded strictly to the implemented historical-column / portal-SVD / Petrov–Galerkin candidates, task streams, `eps_tol = 0.25`, and planner-lifecycle cost model. |
| **`EF-D03` & `EF-D04` (`A1, R314-02`)** | Complete $\varepsilon$-certification terminal fallback & additive accounting | Every task requesting an $\varepsilon$-certificate executes operational same-cache `plan_exact_subset_dp` when interval DP stops at `status == "unresolved"` (charged inside operational time with disaggregated `port_stage_work` + `exact_stage_work` and additive two-stage `work_done` totals; `numeric_invalid` remains fail-closed). `GO` requires **`100%` task $\varepsilon$-certification + `0` bound violations + `>= 20%` net savings** (`1,440 / 1,440` verified across all 5 methods). |
| **`EF-D05` & `EF-D06` (`A2, R314-01, R314-04`)** | Unclipped exact-portal control, `Z > 1` split, & ablation scope | `ExactPortal_Unclipped` achieves `max |ΔQ| = 7.11e-15` (`5.33e-15` vs killed-domain Bellman) across all `192` tasks; separate `mean_raw_Z_gt1_row_frac` and `mean_clipped_Z_gt1_row_frac` counters track pre- vs post-floor row mass; `LocalExactSelf_CrossPortalSVD` is scoped strictly as an **oracle-assisted exact-self-block ablation of global portal SVD** (not a universal rank-`r` off-diagonal ceiling; cf. inverse M-matrix $G = 100 I_4 + \mathbf{1}\mathbf{1}^\top$, where $A = G^{-1}$ is an M-matrix). |
| **`EF-D07` & `EF-D08` (`A3, R314-03`)** | Capacity-honest naming & overlapping task-event attribution | Renamed `Colwise-RegIRLS-Galerkin` (`<= 4` snapshots per ring column, independent source channels, `max_rank` unused) vs `POD-SharedRank-Galerkin` (shared rank `24/28` vs 3D ring size `26..34`, mean `30.0`); documented `total_tasks_with_missing_initial_columns`, `total_tasks_with_refresh`, and `pg_missing_and_refresh_overlapping_tasks` as overlapping task-level event indicators (`REFRESH_*` triggered by either bound/positivity failure or `gap > 0.25` under `eps_tol = 0.25`). |
| **`EF-D09` (`A3, R314-03`)** | Planner-lifecycle timing scope & exact parent preservation | Scoped `Exp 5B` `"from_zero_planner_lifecycle_ms"` to planner construction + `splu` + updates + projections + DP + snapshot harvesting (excluding shared pre-fitted world GPs); calibration epochs run only exact solves + harvesting; preserved exact `efde60ce` parent floats in `exp5_results.json` (`419.11 ms` on `2D Param`, `9418.13 ms` on `3D GP`). |
| **`EF-D10` (`C2-04, C2-05, C2-08, A4, R314-05`)** | Lossless `.npz` vs compact JSON tape & kink/tie contracts | Hardened `Suite 22` explicit `all(checks.values())` + 3-channel off-grid `pending_X`; `Suite 23` verifies `.npz` schema whitelist, `(X, q, b)` row consistency, `onpolicy_index_row_convention` validation (`"trailing_rows"` rejected), `<i8` `onpolicy_traj_indices` SHA-256 tamper/truncation rejection, mixed `11+3` / empty round-trip, and `strict_smooth` vs `action_tie_detected` scope; synced `compact_5dec_provenance_tape_v1` tag. |
| **`EF-D11` & `EF-D12` (`C2-03, C2-07`)** | Production defaults & stopping discipline | Cold-start and 2D default: `ExactRing + Subset-DP`; warm 3D catalog streams: `Structure-Memory-Fresh-Exact` as workload-conditional option; residual column reuse and low-rank subspaces disabled by default; Batch B `b`-sensitivity (`p = 0.643`) reported as unresolved incremental effect; project frozen at release closure without further rank/seed/quota tuning. |

---

## 3. Verification & Benchmark Summary (`24/24 ALL_PASSED: true`)

All linear-algebra and benchmark runs enforce single-thread BLAS/OpenMP execution per worker (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR = 1`). Every JSON artifact (`audit_closure_results.json`, `exp1_results.json`..`exp5_results.json`, `exp4_acquisition_tapes.json`) embeds synchronized `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"` (`exp4_acquisition_tapes.json` SHA-256 `4f2b5e1cc24097dc4e094afc1968e17c139844cdbfd29b44106366187e7fe04c`) and explicit `"generating_commit"` tags on all inherited blocks. All tables below are populated directly from the JSON artifacts.

### 3.1 Independent 24-Suite Audit Closure Regression (`verify_audit_closure.py`)
- **Suites 1–21**: Full enclosure, epoch, continuous `log1p`, typed `IntervalCertificate`, stale-`EXACT` work-descriptor, `np.add.at` duplicate-node scatter (`5.49e-10`), piecewise-reflected polyline hit (`tau = 0.0861`), rank-1 Schur covariance (`1.55e-15`), and single-step planner-object isolation (`0.0` probe diff) checks pass.
- **Suite 22 (`C2-04` Gate & 3-Channel Off-Grid Conditioning)**:
  - Zero-drift counterexample Richardson FD error `3.79e-11..2.12e-10` (`strict_smooth` fails closed); true `max_alt_branches = 0` cuts transpose RHS columns `52 -> 26` (`0.0` diff); off-grid `pending_X` 3-channel `(q, b_x, b_y)` Schur conditioning matches full augmented Cholesky to `<= 3.55e-15`; explicit `_eval_s22_gate` rejects all 3 single-condition failure injections.
- **Suite 23 (`C2-05` + `A4` + `R314-05` Lossless `.npz` Record Contract & Bellman-Tie Scope)**:
  - Verifies `0.0` bit round-trip on grid, irrational off-grid + indices, mixed `11+3` (`14` rows, `11` leading indices), and empty `(0, 2)` batches; fail-closed rejects 1-ULP float tamper, index mutation (`[17,4,29,8,12] -> [18,4,29,8,12]`), index truncation (`-> [17]`), unknown schema (`unsupported_future_schema_v999`), mismatched index convention (`"trailing_rows"`), and `(X:(3,2), q:(1,), b:(3,2))` row mismatches on both `save` and `load`; verifies nonzero-drift Bellman tie (`upwind_drift_kink_detected = False`, `action_tie_detected = True`).
- **Suite 24 (`A1` + `A2` + `R314-01/02` Same-Cache Exact-DP Fallback, Additive Hybrid Accounting, & Exact-Portal Control)**:
  - Reproduces real counterexample `seed = 30309` (`2D Param, start = [-1.0204, 0.9748], targets = (0, 2, 5, 7)`): verifies interval DP returns `status == "unresolved"` (`width = 0.3956 > 0.25`) after populating current-epoch `"EXACT"` columns for all 4 targets, and verifies immediate terminal same-cache `plan_exact_subset_dp` closes to `status == "epsilon_certified"` with **`0` terminal-stage added LU factorizations, `0` terminal-stage added backsolves, and `0.0` error** vs `independent_exact_macro_bellman_reference`, while `plan_economical_hybrid` preserves `port_stage_work` + `exact_stage_work` with exact additive two-stage `work_done` totals (`natural_hybrid_fallback_additive_accounting_ok = True`) and fails closed on `numeric_invalid` (`hybrid_numeric_invalid_fail_closed_ok = True`).
  - Verifies `ExactPortal_Unclipped` readout matches `compute_exact_macro_q_sensitivities` to **`1.78e-15`**, flags rank-4 unphysical responses (`H < 0` / `Z > 1`) as `physically_valid = False`, and verifies on a hand-calculated 2-leg probe that `raw_Z_gt1_row_frac = 0.0` and `clipped_Z_gt1_row_frac = 1.0` are tracked independently (`two_leg_raw_vs_clipped_Z_gt1_counter_ok = True`).

---

### 3.2 Experiments 1, 2, & 3 (Frozen Supporting Provenance Blocks)
- **Exp 1A (`ddd19c5`)**: On locked fresh confirmation `9400..9407` (`25^3`, `K = 40`), `SchurPort-r1-LumpedHaz-25` (`2,078.6 ms`, `+3.5%` Lin-NI **`p_NI = 1.46e-6`**; heldout 6-map `1400..1405` full `K = 40` `p_NI = 3.5e-4`; all 12-map full `K = 40` `p_NI = 8.12e-9`) is `14.86x` faster than `Fresh-FD-25` (`30,888 ms`) and `1.42x` faster than matched `Warm-ILU-LumpedHaz` (`2,957 ms`, `p = 0.0218`).
- **Exp 1B (`29fa7c6`)**: `0` bound violations across `144` `75^2` tours, `96` `m = 5..9` tasks, and `160` crossover tasks; `ExactRing + Subset-DP` wins cold-start `31^3` (`18,691.1 ms` vs `Hybrid` `21,268.5 ms, p = 0.00438`).
- **Exp 2 (`85e2323`)**: `0 / 800` KKT tolerance misses (`<= 9.81e-9`); `1.28x` equal-tolerance speedup and `1.98x–2.02x` 3-step speedup passing `+0.5%` NI (`p_NI <= 0.0010`).
- **Exp 3 (`57e5912` Locked `method_config_id` 6D Table on `9608..9615`, `100` shared physical observations, shared `mean_serial_world_gp_fit_ms = 449.5 ms`, internal response-surrogate sample/compute efficiency rather than standalone 24-sample discovery)**:

| Locked `method_config_id` | GP Rows / FK Paths / Per-Ch `q,b` Evals | Weighted Tail / Mean ESS | Closed-Loop Unseen / Shift (Reach) | `+5%` Lin-NI (`M1` vs Ref) | Query-Cold Serial (`1`-Worker) | Arithmetic `WorldGP + Query` | `8`-Worker `8`-Map Batch Makespan |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`M1_EndToEnd_Bessel24`** | `154.4` / `1266` / `22647` | `0.00078` / `23.84` | `4.374` / `5.297` (`100.0%` / `100.0%`) | — | **`187.1 ms`** (`1.00x`) | `636.7 ms` (`1.00x`) | **`914.8 ms`** (`8.74 q/s`) |
| `M2_FrozenBesselTeacher_SharpCone108` | `235.2` / `5148` / `93632` | `0.00006` / `23.54` | `4.480` / `5.367` (`100.0%` / `100.0%`) | **`0.0107` / `0.0015`** | `1067.4 ms` (`5.70x`) | `1516.9 ms` (`2.38x`) | `2583.1 ms` (`3.10 q/s`) |
| `M3_EndToEnd_IndepConeGirsanov_SharpCone108` | `235.2` / `5148` / `262091` | `0.00223` / `4.45` | `4.589` / `5.492` (`100.0%` / `99.6%`) | **`0.0166` / `0.0412`** | `2791.8 ms` (`14.92x`) | `3241.3 ms` (`5.09x`) | `6639.1 ms` (`1.20 q/s`) |

---

### 3.3 Experiment 4: Fidelity Bridge, GP Lifecycle, `2x2` Factorial, & `64`-Map Confirmation (`exp4_results.json`)

- **Exp 4A (`29fa7c6`)**: `0 / 72` bound violations, `100%` root-action agreement; mean `|ΔJ|`: `L1` port (`0.0056`) << `L2c` `dt=0.005` reflected hit (`0.3432`) < `L3` GP mismatch (`0.8598`).
- **Exp 4B (`c2c499e`, Reused `10250..10261` Cohort, `+16` Physical Observations, `0 / 3,456` Bound Violations)**:
  - `Residual-Audited-Reuse` retains `7.8` / `15.3` (2D) and `91.0` / `198.2` (3D) cached hierarchy level-entries (`L1 + L4 + L8 + EXACT`), while `Structure-Memory-Fresh-Exact` refreshes `217.7` leaf RHS columns in 3D `BroadWarm6`, beating `ExactRing` (`1,111.7` vs `1,305.1 ms`, `-193.4 ms, p = 1.75e-4`) and `Residual` (`1,375.2 ms, p = 1.16e-4`) on warm marginal (`K = 12`). The from-zero lifecycle difference was `−36.4 ms` (`2,544.3` vs `2,580.8 ms`, 95% CI `[−196.7, +123.9]`, `p = 0.627`).
- **Exp 4C Batch B (`c2c499e`, `32` Revealed Dev Maps `10300..10415`, `5` Online Acquisition Stages `Ep 1–5`)**:
  - Sequential Schur conditioning main effect: **`-0.150 +/- 0.067` (`p = 7.63e-5`)**; incremental `b` decision-sensitivity contrast: **`+0.005 +/- 0.023` (`p = 0.643`, unresolved incremental effect; all arms measure/fit/plan with `b`)**; `FactB` (`9.460`, paired `p = 8.22e-6`) and `FactD` (`9.456`, paired `p = 1.19e-6`) both improved on `Global-CondMaxVar-qb-14` (`9.723`).
- **Exp 4C Batch C (`c2c499e`, `64` Untouched Maps `20300..20331` Standard + `20400..20431` Competing-Corridor)**:

| Arm (`64` Untouched Maps `20300..20431`, Deferred Eval) | Standard `32` (`Ep 2–6`) | Competing `32` (`Ep 2–6`) | Pooled `64` (`Ep 2–6`) | Pooled `GreenVal - Arm` (`95% CI`) | `p_nom` / `p_holm` (`3`-Ref Family) | Trap. Cost AUC (`28..98`) / Attained `>=6%` by `98` (`Pen@112`) | Acq / Oper / Sim(excl) / Eval ms |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Frozen-GP-28` | `11.942` | `8.707` | `10.325` | `-1.209 +/- 0.241` | `1.05e-14` (anchor) | `10.325` / `0.0%` (`112.0`) | `0.0` / `376.6` / `1890.2` / `773.3` |
| `Global-CondMaxVar-qb-14` | `10.526` | `8.172` | `9.349` | **`-0.234 +/- 0.091`** | `3.01e-06` / **`9.03e-06`** | `9.481` / `79.7%` (`71.1`) | `395.5` / `1618.6` / `2045.1` / `4765.9` |
| `True-OnPolicy-11+CondSentinel-qb-3` | `10.453` | `8.041` | `9.247` | **`-0.131 +/- 0.084`** | `0.0028` / **`0.0056`** | `9.384` / `81.2%` (`67.8`) | `448.0` / `1707.4` / `2163.6` / `4733.1` |
| `True-OnPolicy-14` | `10.340` | `8.002` | `9.171` | `-0.056 +/- 0.076` | `0.1470` / **`0.1470`** | `9.318` / `89.1%` (`63.0`) | `331.9` / `1543.6` / `2072.6` / `4606.3` |
| **`Green-ValueOnly-qb-Cond-11+3`** | **`10.338`** | **`7.892`** | **`9.115`** | — | — | **`9.273`** / **`92.2%`** (`60.8`) | `1222.9` / `2452.9` / `2061.5` / `4809.9` |

  - **Direct Interaction Test (`Competing - Standard`)**: For `Green - True-OnPolicy-14`, `Delta_interaction = -0.108 +/- 0.155` (`95% CI [-0.263, +0.047]`, **`p = 0.165`** paired; Welch `df = 54.5, p = 0.158`). Thus between-regime heterogeneity is not statistically confirmed, and exploration lock-in on competing passages remains a mechanism hypothesis alongside the `+0.91 s/map` (`1.59x`) coordinate-oracle compute cost.

---

### 3.4 Experiment 5 (`v7` `A1–A3` + `v8` `R314-01..R314-04` Hardened): Response-Subspace Diagnostic & Complete-Certification `NO-GO` Gate (`exp5_results.json`, `exp5_response_subspace.png`)

#### Exp 5A — Algebraic Source-Support Obstruction, Exact-Portal Control, & Known-Portal SVD (`16` Maps `30100..30207`, `192` Tours Across `112` Realized Unseen Targets [`5..8`/map of `128` Requested], `2D 51^2`)
1. **Mandatory Zero-Compression Sanity Control (`ExactPortal_Unclipped`)**:
   - Feeding exact `G_portal_exact` (`mean_portals_full_rank = 128.6`) into the unclipped evaluator passes `192 / 192` physical sub-Markov checks (`H_ext >= -1e-12`, `0 < Z <= 1`) with **`max |ΔQ_root|_inf = 7.11e-15`**, **`max |ΔV*|_killed_ref = 5.33e-15`**, and **`100.0%` root-action agreement**.
2. **Fixed Old-Source Support Obstruction vs. Known-Portal Truncation Mechanisms**:
   - For any unseen target $\Gamma_{\text{new}}$ disjoint from historical rings $T$, historical columns $Y = A_0^{-1} E_T$ satisfy $(A_0 V c)|_{\Gamma_{\text{new}}} = 0$, guaranteeing **`||E_{Gamma_new} - A_0 V c||_inf >= 1.000`** (`0.0%` certification; excludes fixed old-source linear spans under global PDE residual certificates, without excluding local source lifting/particular solutions).
   - On the known evaluation portal matrix (`r_90% = 54.6`, `r_99% = 114.2`, `r_99.9% = 127.1` of `128.6`), **global SVD** (`Standard_POD_SVD`, `Start4x_Weighted_Portal_SVD`) compresses diagonal self-ring blocks (`median cond = 2.55e11..2.14e19`, `~45%..50%` negative `H_ext` entries, `22.6%..37.3%` raw `Z > 1` rows, **`54.8%..78.5%` clipped `Z > 1` rows**, and **`0.0%` strict physical validity**).
   - **Oracle-Assisted Exact-Self-Block Ablation of Global Portal SVD (`LocalExactSelf_CrossPortalSVD`)**: Scoped strictly as an ablation of the global portal-SVD construction (not a universal ceiling across all rank-`r` off-diagonal approximations; e.g., for inverse M-matrix $G = 100 I_4 + \mathbf{1}\mathbf{1}^\top$, whose inverse $A = G^{-1} = 0.01 I_4 - \frac{1}{10400}\mathbf{1}\mathbf{1}^\top$ is an M-matrix, global rank-1 SVD + exact diagonal override incurs off-diagonal error `25`, whereas direct rank-1 off-diagonal approximation achieves `0`), retaining exact `m_b x m_b` self-ring diagonal blocks restores well-conditioned rings (`median cond = 5.28`, **`0.0%` raw `Z > 1` and `0.0%` clipped `Z > 1` rows**) and raises clipped-heuristic top-1 agreement (`35.9% -> 61.5%` at `r=4`, `50.0% -> 77.6%` at `r=32`, `64.1% -> 79.2%` at `r=64`), **yet off-ring global-SVD truncation still produces `30.7%..47.2%` negative `H_ext` entries (`<= 2.1%` strict validity) and `0.290` full-policy regret at `r=64`**, while `SingleLU-ExactRing` solves all 12 unseen-target tours exactly (`0.0` regret) in **`26.0 ms` post-LU (`38.7 ms` incl. planner init + `splu`; `11.0 ms` warm seen-catalog cache)**—less than the portal transpose-solve + SVD cost alone (`20.4 + 26.3 = 46.7 ms`):

| Rank `r` (`192` Tours; `31` Near-Tie Across `14` Maps) | `Global POD` Med `cond` / Strict Valid% | `ExactSelf+CrossSVD` Med `cond` / Strict Valid% | `Global POD` Top-1 / Near-Tie (Pool `31` \| Map `14`) | `Start4x-SVD` Top-1 / Near-Tie (Pool `31` \| Map `14`) | `ExactSelf+CrossSVD` Top-1 / Near-Tie (Pool `31`) | Root / Full-Policy Regret (`POD` \| `Start4x` \| `ExactSelf`) (`Clipped Heur.`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `r = 4` | `1.4e19` / `0.0%` | `5.28` / `2.1%` | `35.9%` / `35.5%` \| `38.9%` | `32.3%` / `22.6%` \| `21.1%` | `61.5%` / `45.2%` | `1.23 / 2.45` \| `1.33 / 2.63` \| `0.47 / 0.96` |
| `r = 8` | `4.5e18` / `0.0%` | `5.28` / `0.0%` | `37.0%` / `35.5%` \| `40.4%` | `38.5%` / `35.5%` \| `37.1%` | `67.2%` / `58.1%` | `1.07 / 2.28` \| `1.12 / 2.55` \| `0.36 / 0.81` |
| `r = 16` | `1.4e18` / `0.0%` | `5.28` / `0.0%` | `38.5%` / `22.6%` \| `20.7%` | `36.5%` / `29.0%` \| `26.1%` | `70.8%` / `54.8%` | `0.94 / 1.69` \| `1.00 / 1.88` \| `0.25 / 0.59` |
| `r = 32` | `2.9e16` / `0.0%` | `5.28` / `0.0%` | `50.0%` / `25.8%` \| `16.8%` | `58.3%` / `45.2%` \| `41.8%` | `77.6%` / `58.1%` | `0.59 / 1.01` \| `0.47 / 0.92` \| `0.16 / 0.40` |
| `r = 64` | `2.6e11` / `0.0%` | `5.28` / `0.0%` | `64.1%` / `38.7%` \| `40.4%` | `68.2%` / `29.0%` \| `24.6%` | `79.2%` / `45.2%` | `0.34 / 0.53` \| `0.25 / 0.42` \| `0.13 / 0.29` |

#### Exp 5B & 5C — Continual Evolving-World Planner-Lifecycle Benchmark (`12` Maps `30300..30311`, **`1,440 / 1,440` `100%` $\varepsilon$-Certified (`314a88b` Frozen Run), `0` Unresolved, `0` Violations**)
- **Ring Geometry & Storage Scope**: Actual catalog ring node counts are **`18..20` (mean `19.28`) in `2D 51^2`** (`4`-snapshot dense catalog bank `15.31 MiB`) and **`26..34` (mean `29.98`) in `3D 21^3`** (`4`-snapshot dense catalog bank `84.72 MiB`; no persistent compressed basis storage implemented). All `120` 3D rings exceed `24` nodes, so shared-basis `POD-SharedRank-Galerkin` (`rank <= 24` on GP, `<= 28` on Param) loses ring source DOF, whereas `Colwise-RegIRLS-Galerkin` (`<= 4` historical vectors per source column, independent source channels, `max_rank` unused) preserves full ring rank—thus their screen-rate difference reflects trial-space capacity and channel independence as well as residual weighting.
- **Complete Certification & Timing Scope**: Calibration epochs (`ep < n_calib_epochs`) run exact solves + harvesting only; in test epochs, the `4 / 1,440` tiny-`Z_bar` 2D tasks (`2` in `2D GP`, `2` in `2D Param`) where interval outward padding (`~1e-12`) left `width = 0.286..0.396 > 0.25` after the upstream port stage populated current-epoch `"EXACT"` columns are closed automatically via terminal operational same-cache `plan_exact_subset_dp` (**`0` terminal-stage added LU, `0` terminal-stage added backsolves**, `360 / 360` certified in every stream; exact pre-patch `efde60ce` reference preserved in `exp5_results.json`):

| Stream (`12` Maps, `360/360` Cert, `0` Viols) | `ExactRing-Rebuild` (Lifecycle / Test Marg) | `Structure-Memory` (Lifecycle / Test Marg) | `Residual-Rank0` (Lifecycle / Test Marg) | `POD-SharedRank` (Lifecycle / Marg / Pre-DP Scr%) | `Colwise-RegIRLS` (Lifecycle / Marg / Pre-DP Scr%) | `>= 20%` Complete-Cert Go/No-Go Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `2D-51sq_RealisticGPStream` | **`239.0`** / **`194.1 ms`** | `468.4` / `314.7 ms` | `483.4` / `317.4 ms` | `564.5` / `523.1 ms` (`16.7%`) | `446.4` / `406.8 ms` (`45.0%`) | **`NO-GO`** (`-86.8%` life / `-109.6%` marg) |
| `2D-51sq_LowDimParametricStream` | **`283.1`** / **`170.8 ms`** | `533.1` / `251.7 ms` | `573.8` / `301.2 ms` | `804.1` / `679.3 ms` (`100.0%`) | `568.5` / `452.7 ms` (`100.0%`) | **`NO-GO`** (`-100.8%` life / `-165.0%` marg) |
| `3D-21cubed_RealisticGPStream` | `7520.3` / `6392.6 ms` | **`7114.0`** / **`5837.2 ms`** | `8143.5` / `6809.3 ms` | `10613.6` / `9293.2 ms` (`0.0%`) | `8355.7` / `7108.3 ms` (`73.1%`) | **`NO-GO`** (`-17.5%` life / `-21.8%` marg) |
| `3D-21cubed_LowDimParametricStream` | `9449.5` / `5677.6 ms` | **`8517.5`** / **`5167.7 ms`** | `10718.1` / `6549.6 ms` | `13105.6` / `9563.3 ms` (`22.0%`) | `11367.5` / `7847.1 ms` (`100.0%`) | **`NO-GO`** (`-33.5%` life / `-51.8%` marg) |

- **Disaggregated Task-Level Event Attribution (`360` Test Tasks per Stream; Overlapping Indicators, Not Step Counts)**:
  - `3D-21cubed_RealisticGPStream`: `POD-SharedRank` (`0 / 573` screen accepted, `6` no-history) incurs new backsolves on `267 / 360` tasks purely via initial missing-target exact solves (`267` tasks with initial missing columns, `0` tasks with `REFRESH_*`, `0` overlap); `Colwise-RegIRLS` (`419 / 573 = 73.1%` screen accepted) incurs new backsolves on `267 / 360` tasks via overlapping task-level events: `111` tasks with missing/rejected initial columns + `214` tasks containing `>= 1` mid-DP `REFRESH_*` event minus `58` tasks experiencing both (`111 + 214 - 58 = 267`, `5.0 / 5.0` test-epoch LU factorizations), where `REFRESH_*` reflects either bound/positivity failure or `gap > 0.25` under the `eps_tol = 0.25` protocol.
  - `3D-21cubed_LowDimParametricStream`: `Colwise-RegIRLS` passes `576 / 576` (`100.0%`) pre-DP diagonal screens (`0` tasks with missing initial columns), yet `254 / 360` tasks trigger `>= 1` `REFRESH_*` event inside `plan_subset_macro_policy` under `eps_tol = 0.25`, adding `1,301.4 ms` projection/audit overhead on top of `5.0 / 5.0` LU factorizations.
  - *Pure Post-Processing Reconstruction Note (`A26-D03`)*: To keep `green_response/*.py` frozen at `package_py_sha256 = "271ac8df..."` without re-running `Exp 5B`, the 4 summary alias/overlap fields in `exp5_results.json` (`total_tasks_with_missing_initial_columns`, `total_tasks_with_refresh`, `total_tasks_with_hierarchy_refine`, and `pg_missing_and_refresh_overlapping_tasks`) are deterministically reconstructed from the frozen `per_map_records` via inclusion-exclusion (`missing = sum(n_task_missing_initial_exact_solve)`, `refresh = sum(n_task_refresh_steps)`, `hierarchy = sum(n_task_hierarchy_refine_steps)`, and for PG methods where `hierarchy == 0` and `final_same_cache_exact_dp_added_backsolves == 0`, `pg_missing_and_refresh_overlapping_tasks = missing + refresh - sum(tasks_with_new_backsolves)`).

---

## 4. Reproducible Execution Commands

From the repository root, create a fresh project-local directory for the frozen scripts. They write JSON and figures alongside their own source.

```bash
mkdir -p .tmp
green_run=$(mktemp -d "$PWD/.tmp/green-response-XXXXXX")
cp -r green_response "$green_run/"
cd "$green_run" || exit 1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# Counterexamples and numerical contracts
/usr/bin/python3 -m green_response.verify_audit_closure

# Original experiments, if regenerating their measurements
/usr/bin/python3 -m green_response.exp1_3d_and_macro_tours
/usr/bin/python3 -m green_response.exp2_nonlmdp_kkt
/usr/bin/python3 -m green_response.exp3_highd_and_kinetic
/usr/bin/python3 -m green_response.exp4_fidelity_and_continual
/usr/bin/python3 -m green_response.exp5_response_subspace_diagnostic
```

---

## 5. Phase-II Follow-Up Research Specification & Isolated `quotient_phase2/` Package

With Phase-I code, contracts, and `Experiments 1–5` permanently frozen at `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"`, the contract-hardened Phase-II specification (`A26-D01..D12` closed across all 10 matrix counterexamples) is documented in [`NEXT_PHASE_RESEARCH_ROADMAP.md`](./NEXT_PHASE_RESEARCH_ROADMAP.md), and the published clean-run results and current reproduction commands are in the [Phase II package](../quotient_phase2/README.md).


