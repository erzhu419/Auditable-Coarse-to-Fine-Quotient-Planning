# `quotient_phase2`: Contract-Hardened Phase-II Certification, Dyadic Portal Quotient, & Same-Quality 3D Attribution Suite (`M2.0`–`M2.3.1`)

Isolated Phase-II research package importing the frozen Phase-I library (`../green_response/`, locked byte-for-byte at `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"`) strictly read-only.

## 0. Provenance & Non-Destructive Artifact Ledger

All historical JSON artifacts from commits `89761ff` and `ec75871` are preserved **100% byte-untouched** (`verified at startup of m231_audit_closure.py and m231_fair_ablation.py`); post-`ec75871` contract hardening (`EC-01..EC-06`), strictly nested dyadic portal refinement (`1 -> 4 -> 16 -> 64`), and same-quality adjacent-baseline experiments write exclusively to `m231_*` artifacts:

| Artifact / Package | SHA-256 / Manifest Identifier | Provenance & Scope |
| :--- | :--- | :--- |
| `../green_response/*.py` (Frozen Phase-I) | `271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d` | Byte-frozen since `a26c116` (`verified_intact = true` at startup of every script) |
| `quotient_phase2/*.py` (Final `M2.3.1` Code) | `f530c1b8d42e5693bea71b9a59d996e878432d107042e499dadae56e7c745ac9` | Identical manifest embedded in `m231_audit_closure.json` and `m231_fair_ablation_results.json` |
| `m21_ablation_results.json` (Frozen `89761ff`) | `634c15e52fb3a8181f738baef40b8d7c30e690a8600a7cf1e30b6ca17a3c4fc1` | Byte-untouched `89761ff` campaign (`generating_phase2_py_sha256 = cdd584d9...`; `8/8` streams `STOP`) |
| `m20_contract_results.json` (Frozen `ec75871`) | `bdad834622c2ab0215be84c2e3cfb4473f5b242e053d9b7bef8e792081c67004` | Byte-untouched `ec75871` 15-gate verification (`generating_phase2_py_sha256 = c3f7a8a2...`) |
| `m22_pilot_results.json` (Frozen `ec75871`) | `55d7e1ea176d2ad53d173595339c21216fc6f210857b5d28e30b98c163a3d892` | Byte-untouched `ec75871` 2D portal pilot (`generating_phase2_py_sha256 = c3f7a8a2...`) |
| `m23_m24_3d_results.json` (Frozen `ec75871`) | `8fb6fb84749dfa640e5f5394c65db71426302a365e95a512c25dd896bce30f05` | Byte-untouched `ec75871` initial 3D campaign (`generating_phase2_py_sha256 = c3f7a8a2...`; see Section 4.1 scope notes) |
| `m231_audit_closure.json` (**New `M2.3.1` WP-A**) | `4a0e2514a351ab7102dc9e54c6fce38dc9b5b8325ec8c277aa96aaa09257c4a9` | Closes `EC-01..EC-06` & strictly nested dyadic `11x11` portal checks (`0` warnings, `296.1 ms`) |
| `m231_fair_ablation_results.json` (**New `M2.3.1` WP-B/C**) | `f844a1028ec72ca7e0c26f77106b65d622412c8efb500fbe1e7f0869706cf003` | `100%` measured same-quality 6-arm attribution (`Dev 35^3` + fresh `63000..63005` `35^3 / 47^3 / 59^3` + continual `47^3`; `0` violations) |

---

## 1. Milestone `M2.0` + `WP0` + `M2.3.1 WP-A` — Mathematical Contracts & Counterexample Closure ([m20_contracts.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m20_contracts.py), [m231_audit_closure.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m231_audit_closure.py), [m231_audit_closure.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m231_audit_closure.json))

1. **15 Small-Matrix & Adequacy Gates (`C01`–`C15`)**: Separates Green source matrix $U$, killed hitting kernel $H$, survival $Z$, and normalized exit law $P$; verifies centered bilinear DWR with explicit adjoint defect (`C03, C05`); rejects `NaN/Inf` tolerances and separates `full_policy_enclosure` from single-step `receding_horizon_root_action_enclosure` (`C04, C11`); rejects `tiny-Z` exit/cost aliasing (`C12, C13`), quantifies single-option Jensen loss vs. `0.0` Cole–Hopf interface loss (`C14`), and bounds cyclic SSP resolvents via Lyapunov witnesses (`C15`).
2. **`M2.3.1` Public-API & Certificate Hardening (`ALL_EC75871_AUDIT_ISSUES_CLOSED = true`, `0` warnings)**:
   - **`EC-01` (Terminal Gauge Invariance)**: Solves in unit terminal gauge ($g_{\text{unit}} = 1$) and adds uniform $\phi_{\text{goal}}$ after $-\lambda \log$, eliminating `-lam * log(max(z, 1e-300))` zero-width fake certificates (`width = 0.044838` invariant within `7.11e-14` across $\phi_{\text{goal}} \in \{-1000, 0, 100, 135, 145, 160, 1000\}$).
   - **`EC-02` (Domain & Capability Guards)**: Enforces `ProblemSpec.validate_cole_hopf_lmdp` (rejecting finite `u_max` or anisotropic `r_diag`), rejects cross-room goal unions and portal-straddling goals with explicit `ValueError`, short-circuits `start_in_goal`, and supports `start_on_portal` readout.
   - **`EC-03` (Directed Reachability & Floor-Free Policy Evaluators)**: Verifies directed target reachability (`check_directed_goal_reachability`) and policy properness; unreachable goals return `certified=False, status="unreachable", +inf` in both `M2.2` and `M2.3`, and scale-invariant row-max-normalized evaluators satisfy Bellman consistency to `2.66e-15` without `1e-300` row-sum distortion.
   - **`EC-04` (Runtime Howard & Unclipped Lyapunov Verification)**: `solve_and_verify_portal_howard_bounds` iterates up to `30` steps and explicitly verifies post-fixed-point $W_{\text{lo}} \ge L\underline{v}$, pre-fixed-point $W_{\text{hi}} \le L\overline{v}$, unclipped Lyapunov defect $s_0 = (I - K) w_{\text{lyap}} > 0$ (recording $\beta = \min_i s_{0,i}/w_{\text{lyap},i}$), and roundoff perturbation `max_k_neg_roundoff` prior to issuing any certificate.
   - **`EC-05` (Reference Solver Verification)**: `solve_exact_reference_value` enforces `info == 0`, strict positivity, and normalized residual $\le 10^{-9}$ (`raises RuntimeError` under injected `info=80`); all `M2.3.1` cohorts verify against **independent full-grid `SingleLU_GoalCapacitance`**.
   - **`EC-06` & `7.3` (Trajectory Chain Identity, Executable Policy Handle, & Strictly Nested Dyadic Portals)**: `RecedingHorizonCertificateChain` requires contiguous step-indexed certificates (`step_index = 0..m-1`), rejecting repeated unindexed roots `(c, c, c, c)`; `LazyRoomPortalPolicy` (constructed and primed at the start room inside `query_ms`) binds `(operator_epoch, goal_signature)` and rejects stale epochs; `build_portal_level_blocks` uses recursive dyadic splitting (`L0=1 -> L1=4 -> L2=16 -> L3=64` with `0` cross-parent blocks on `11x11` portals).

---

## 2. Milestone `M2.1` — Global-Grid DWR Economic `STOP` ([m21_ablation_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_ablation_results.json), [m21_economic_gate_verdict.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_economic_gate_verdict.json), [m21_post_audit_closure.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_post_audit_closure.json))

- Evaluates `2,400` unique test tasks across `6` arms (`14,400` method-task evaluations, `0` bound violations); `WP0` closes dynamic row-extension indexing and action-specific root $Q$-intervals (`m21_post_audit_closure.json`).
- All `8 / 8` streams trigger the pre-declared economic `STOP` gate (`F11` `+59.3%..+221.5%` slower than `ExactRing` / `StructMem`) due to `5.0 / 5.0` monolithic global `splu(A_t)` factorizations and $O(N|\mathcal{R}|)$ full-grid witness matmuls.

---

## 3. Milestone `M2.2a/b` — 2D Multi-Room Portal Quotients ([m22_portal_quotient_pilot.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m22_portal_quotient_pilot.py), [m22_pilot_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m22_pilot_results.json))

- **Part A (`4 / 4` Controlled Graph Families Passed)**: Equivalent lanes stay compressed (`4.0x`, `0` regret); entry-dependent room barrier splits aliased doorways (`regret 0.5134 -> 2.05e-5`); `tiny-Z` aliasing fails closed; cyclic 3-room drift loop confirms `0.0` (`1.22e-15`) multi-exit Cole–Hopf interface loss vs. `+1.0148` single-option Jensen loss.
- **Part B (`2D` Soft-Wall 16-Room Streaming `K = 50` Goals)**: Across `Dev 49^2`, `Confirm 49^2`, `Confirm 65^2`, and `1-Worker Rotated 65^2` (`8,000` method-task evaluations across cohorts/methods, `0` violations), uncompressed `LocalSchur` beats `FullGrid_Exact_Direct` by **`2.29x–2.40x` (`p <= 6.42e-4`)**, while iterative 2D portal splitting (`n_gamma = 381` 1D cuts) only crosses below `FullGrid` on single-worker `65^2` (`1.20x`, `p = 0.0350`) and remains slower than uncompressed `LocalSchur` in 2D.

---

## 4. Milestones `M2.3 / M2.4` (Frozen `ec75871`) & `M2.3.1` Same-Quality 3D Attribution Closure

### 4.1 Scope & Accounting Notes on Frozen `ec75871` Artifact ([m23_m24_3d_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m23_m24_3d_results.json))
To preserve strict auditability without overwriting `ec75871` data, `m23_m24_3d_results.json` is retained untouched with the following exact accounting scope:
- **Verification Denominators**: Of `1,008` total tasks (`576` in `M2.3` + `432` in `M2.4`), all `1,008` checked value-interval containment against the portal reference, whereas **`360` tasks** (`288` on `35^3`, `36` on `47^3`, `36` on `59^3`, `0` on `M2.4`) evaluated exact deployed discrete KL-LMDP policies.
- **Extrapolation & Matched-Seed Denominators**: On `Confirm 47^3`, `FullGrid_SPLU` projected `K=24` from `2` measured solves/map (`12` solves); on `Confirm 59^3`, `FullGrid_SPLU` (`2` solves on seeds `62000..62001`) and `LocalSchur_3D` (`8` solves on seeds `62000..62001`) were projected (`matched 2-map projected ratios vs M2.3 are 18.55x and 2.72x`, rather than dividing 2-map projections by the 6-map candidate mean `20.13x / 2.95x`). Actual `ProcessPoolExecutor` workers were `3` (`35^3, 47^3, M2.4`) and `2` (`59^3`), with single-threaded BLAS/OpenMP (`1`) inside each worker.
- **Unscaled `Warm-ILU` Diagnosis**: `Warm-ILU` (`rtol=1e-11`) exceeded `0.25` value error on `0/6` `Dev 35^3`, `1/6` `Confirm 35^3` (`max err 0.308` at $z^*(s_0) \approx 2.75\times 10^{-14}$), `0/6` `Confirm 47^3`, and `4/6` `Confirm 59^3` maps—not because $10^{-14}..10^{-18}$ underflows IEEE float64 (`min normal 2.2e-308`), but because global Euclidean linear residuals fail to bound relative error on small $z$, amplified by $-\lambda \log z$.
- **Coarse vs. Full-Interface Work & Discovery/Update Scope**: In `ec75871` (non-nested `1->4->16->36` quantile bins), full-interface Krylov defect closure ran on `22.2%` (`Confirm 35^3`), `51.4%` (`Confirm 47^3`), and `72.9%` (`Confirm 59^3`) of queries; `94.7` retained `M2.4` cache items denote `(portal_id, level)` entries across `51` physical doorways; bottleneck discovery operates on known 3D occupancy grids under axis-aligned planar walls; and `M2.4` evaluates known-support synthetic operator updates rather than online GP refitting.

### 4.2 Authoritative `M2.3.1` Same-Quality 6-Arm Attribution & Cache Causal Study ([m231_fair_ablation.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m231_fair_ablation.py), [m231_fair_ablation_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m231_fair_ablation_results.json), [m231_fair_ablation_summary.png](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m231_fair_ablation_summary.png))

Evaluates **brand-new untouched confirmation seeds `63000..63005`** across computational scale family `35^3 -> 47^3 -> 59^3` (`K = 24` unseen single-room goals/map, Latin-square balanced execution order, **`100%` measured with zero extrapolation**, `LazyRoomPortalPolicy` / `FullGridGuidePolicy` primed inside `query_ms`, shared `gp_fit_ms` + `operator_assembly_ms` explicitly billed, verified against independent `SingleLU_GoalCapacitance`):
- **Four Separate Verification Counters on `M231_Portal_CacheOn`**: `certificate_conditions_verified_count = 792 / 792`, `optimal_value_reference_checked_count = 792 / 792` (`0` violations vs `SingleLU`), `deployed_policy_evaluated_count = 396` (`144` `Dev 35^3` + `144` `Fresh 35^3` + `72` `Fresh 47^3` + `36` `Fresh 59^3`, **`0` violations, max deployed regret `<= 0.0402`**), and `continuous_or_real_world_evaluated_count = 0`.

| Cohort (`K = 24`, Balanced Order, `100%` Measured) | Free DOFs / `|\Gamma|` -> Coarse DOFs (Full-Interface Closure Rate) | `Verified_Global_WarmILU` (ms; `Unverified` ms) | `SingleLU_GoalCapacitance` (ms; LU MB) | `MatrixFree_ExactSchur_Krylov` (ms) | `M231_Portal_StructureOnly` / `CacheOff_Cold` (ms) | `M231_Portal_CacheOn` (`Lazy` \| `Eager` ms; `First6 -> Last6` ms/g) | `M231` Speedup vs `MatFree` / `SingleLU` / `VerWarmILU` ($p_{2s}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Dev 6-Map` `35^3`** (`61000..61005`) | `38,218` / `2,499` -> `254.1` (**`6.2%`**) | `8,511.3` (`3,944.4`) | `4,667.8` (`194 MB`) | `2,886.9` | `7,827.6` / `7,818.3` | **`2,910.5`** \| `3,111.9` (`140.0 -> 87.2`) | `0.99x` (`p=0.834`) / **`1.60x`** (`2.7e-4`) / **`2.92x`** (`2.1e-6`) |
| **`Fresh 6-Map` `35^3`** (`63000..63005`) | `38,240` / `2,499` -> `259.4` (**`9.0%`**) | `9,034.2` (`4,021.4`) | `5,049.6` (`200 MB`) | **`2,873.5`** | `8,412.2` / `8,435.1` | `3,222.7` \| `3,431.2` (`125.9 -> 102.5`) | `0.89x` (`p=0.0338`) / **`1.57x`** (`3.1e-4`) / **`2.80x`** (`5.4e-6`) |
| **`Fresh 6-Map` `47^3`** (`63000..63005`) | `94,817` / `4,131` -> `333.4` (**`20.8%`**) | `35,256.5` (`14,546.2`) | `20,669.7` (`752 MB`) | `11,241.4` | `29,393.5` / `29,224.7` | **`9,016.9`** \| `9,733.2` (`381.6 -> 255.1`) | **`1.25x`** (`0.00121`) / **`2.29x`** (`5.9e-6`) / **`3.91x`** (`4.3e-7`) |
| **`Fresh 6-Map` `59^3`** (`63000..63005`) | `190,603` / `6,171` -> `403.1` (**`42.4%`**) | `110,770.3` (`40,133.0`) | `71,187.5` (`2,135 MB`) | `36,063.7` | — | **`29,730.3`** \| `31,812.1` (`1,237.0 -> 897.6`) | **`1.21x`** (`0.00229`) / **`2.39x`** (`8.1e-5`) / **`3.73x`** (`1.2e-6`) |

- **Key Mechanistic & Causal Findings**:
  1. **Strictly Nested Dyadic Portals Cut Full-Interface Fallback Dramatically**: Upgrading `build_portal_level_blocks` to recursive dyadic splitting reduces full-interface defect closure to **`6.2%–9.0%` (`35^3`), `20.8%` (`47^3`), and `42.4%` (`59^3`)** (`57.6%–93.8%` certified purely on the coarse quotient!). End-of-stream memory on `59^3` is `885.3 MB` local room LUs + `181.9 MB` `K` cache + `408.5 MB` `Y` cache (`1,475.7 MB` total vs. `2,135.2 MB` for a single global `59^3` `splu`).
  2. **Within-3D Interface Crossover vs. `MatrixFree_ExactSchur_Krylov`**: On small `35^3` doorways (`7x7 = 49` nodes, `K = 24`), `MatrixFree_ExactSchur_Krylov` (sharing our room LUs and L0 Lyapunov gauge) matches or slightly beats `M231_Portal_CacheOn` (`0.99x` Dev, `0.89x` Fresh) while `CacheOn` populates `L1..L3` bases; on larger `47^3` (`9x9 = 81` nodes) and `59^3` (`11x11 = 121` nodes) doorways, `M231_Portal_CacheOn` crosses below `MatrixFree` at **`k = 3` (`47^3`) and `k = 1` (`59^3`)**, achieving **`1.25x` (`p = 0.00121`) and `1.21x` (`p = 0.00229`)** net speedups (`1.24x` and `1.21x` end-to-end incl. GP + assembly).
  3. **Dominance Over Both Verified and Unverified Global Baselines**: Global additive residual bounds `(lam/q_min)||r||_inf` self-certify `full_policy_enclosure` (`z_sub > 0` globally) on only `1 / 576` tasks because antipodal-room $z^* \sim 10^{-16} \ll (\lambda/q_{\min})\|r\|_\infty$; even against **unverified** `Warm-ILU` (`rtol=1e-11`, which suffers `1` non-positive `inf` readout on `Fresh 59^3`), `M231_Portal_CacheOn` wins across all cohorts (**`1.25x–1.61x`, `p <= 0.0373`**).
  4. **Causal Cache Proof & Reversed-Order Control**: `CacheOn` beats `StructureOnly` and `CacheOff_Cold` by **`2.61x–3.26x` (`p <= 2.12e-5`)**, and reversing the task sequence (`tasks[::-1]`) preserves early-to-late query acceleration (`Fresh 47^3`: `420.8 -> 226.0 ms/g`).
  5. **Continual `known_support_synthetic_local_operator_updates` (`Fresh 47^3`, `1` Init + `5` Updates $\times$ `6` Tasks, `operator_rebuild_ms = 105.3 ms` Charged)**: Post-init marginal cost of `M231_Portal_CacheOn` (**`11,099.8 ms`**, retaining `81.3` `(portal_id, level)` entries/epoch, `0` violations) beats **`MatrixFree_ExactSchur_Krylov` (`13,309.2 ms`, `1.20x`, `p = 3.98e-4`)**, **`SingleLU_GoalCapacitance` (`52,627.7 ms`, `4.74x`, `p = 1.63e-5`)**, and **`Verified_Global_WarmILU` (`77,733.8 ms`, `7.00x`, `p = 4.63e-7`)**.

---

## 5. Reproducible Execution

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/usr/bin/python3 -W error quotient_phase2/m231_audit_closure.py
/usr/bin/python3 -u quotient_phase2/m231_fair_ablation.py --self-test
/usr/bin/python3 -u quotient_phase2/m231_fair_ablation.py
```
