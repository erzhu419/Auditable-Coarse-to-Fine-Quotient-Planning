# `quotient_phase2`: Contract-Hardened Phase-II Certification, Portal Quotient, & 3D Scale/Continual Suite (`M2.0`–`M2.4`)

Isolated Phase-II research package importing the frozen Phase-I library (`../green_response/`, locked byte-for-byte at `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"`) strictly read-only.

## 0. Provenance & Frozen Artifact Ledger (`v10 E07`)

| Artifact / Package | SHA-256 / Manifest Identifier | Provenance & Scope |
| :--- | :--- | :--- |
| `../green_response/*.py` (Frozen Phase-I) | `271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d` | Byte-frozen since `a26c116` (`verified_intact = true` at startup of every script) |
| `quotient_phase2/*.py` (Unified `M2.0–M2.4`) | `c3f7a8a23a724f38f702f8fefe55bdcd2d9a4f9d1b61667a85575c452d49c022` | Identical manifest embedded across `m20_contract_results.json`, `m21_post_audit_closure.json`, `m22_pilot_results.json`, and `m23_m24_3d_results.json` |
| `m21_ablation_results.json` (Frozen `89761ff`) | `634c15e52fb3a8181f738baef40b8d7c30e690a8600a7cf1e30b6ca17a3c4fc1` | Byte-untouched `89761ff` campaign (`generating_phase2_py_sha256 = cdd584d99b012aa3f6668680604bec7c2db12fa99da15db30f8fd348ce55e803`, `0` reruns; post-audit closure in `m21_post_audit_closure.json` & `m21_economic_gate_verdict.json`) |

---

## 1. Milestone `M2.0` + `WP0` — Mathematical Contracts & 15-Counterexample Gate ([m20_contracts.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m20_contracts.py), [m20_contract_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m20_contract_results.json))

Closes all 15 small-matrix & contract counterexamples (`C01..C10` from `v9` + `C11..C15` from `v10`) in `3.78 ms` (`ALL_15_COUNTEREXAMPLE_GATES_PASSED = true`):

1. **`C01` (`P2A-01`)**: Separates unbounded Green source response $U = A^{-1} E_\Gamma \ge 0$ (`max = 23.81 > 1` rejected as sub-Markov) from killed exterior hitting kernel $A_{II} H = -A_{I\Gamma}$ (`0 <= H`, `max row sum = 0.476 <= 1.0`).
2. **`C02` (`P2A-02`)**: Rejects interior-omitted collar concatenation (`[0.5, 0.25] != [2/3, 1/3]`) and verifies `0.0` error for both exact Schur back-substitution and zero-extended full-exterior remainder correction (`R_full = B - A_{II} H_lifted`).
3. **`C03` (`P2A-03`)**: On swapped stochastic rows ($H = \begin{pmatrix}0.9&0.1\\0.1&0.9\end{pmatrix}$ vs $\widetilde{H} = \begin{pmatrix}0.1&0.9\\0.9&0.1\end{pmatrix}$ where $(H-\widetilde{H})\mathbf{1} = 0$ yet $|(H-\widetilde{H})f| = 0.8$), verifies `bound_normalized_continuation_dwr` encloses both denominator $H\mathbf{1}$ and centered numerator $H(f-\mu\mathbf{1})$ (with optional `strict_fail_closed=True` disabling IEEE `1e-11` rounding slack).
4. **`C04` (`P2A-04` + `v10 C03`)**: `Phase2DecisionCertificate` rejects a deployed policy with regret `100.0` despite root $Q^*$-gap `0.0` under `full_policy_enclosure`; single-node `receding_horizon_root_action_enclosure` returns `guaranteed_full_horizon_regret_bound = None` (`v10 C03`), whereas `RecedingHorizonCertificateChain` returns $\sum_{t=1}^m \eta_t = 0.40$ **only** when all $m = 4$ step certificates are verified.
5. **`C05` (`P2A-05`)**: Rejects radial exponential $\psi = (1, e^{-1})^\top$ as an unverified super-adjoint on asymmetric $A = \begin{pmatrix}1&-0.9\\-0.1&1\end{pmatrix}$ (`min slack = -0.532`), while `prepare_bilinear_dwr_operator` remains sound by billing $\|e_p - A^\top \psi\|_1$.
6. **`C06` (`P2B-01`)**: Exposes `-1/6` negative entry in partition-of-unity Galerkin $W(W^\top W)^{-1}W^\top$ vs non-negative sub-Markov $\overline{H} = R H L$.
7. **`C07` (`P2B-02`)**: Separates zero point-interval product width (`0.0`) from within-block exit dispersion (`delta_lump = 2.0`) and 2-step operator error (`||R P^2 L - (R P L)^2||_inf = 1.0`).
8. **`C08` (`P2B-03`)**: Verifies irreversible 3-cycle ratio `729.0` invariance under diagonal Doob similarity.
9. **`C09` (`P2C-01`)**: Verifies compact-support prior $K_{LR} = 0$ induces nonlocal posterior $K_{LR \mid M} = -0.16$ (`-0.1905` mean shift).
10. **`C10` (`P2C-02`)**: Verifies single-block Schur perturbation shifts all `3 / 3` coupled global interface coordinates.
11. **`C11` (`v10 C02`)**: Rejects `NaN`/`inf`/negative `epsilon_tol`, `horizon_steps < 1`, `NaN` competitor Q-bounds, and `NaN` entries in `build_row_stochastic_sandwich_kernel` (`8 / 8` invalid inputs rejected fail-closed).
12. **`C12` (`v10` `tiny-Z` Exit Aliasing)**: On $H = \operatorname{diag}(10^{-8}, 10^{-8})$ (`raw delta_H = 2e-8` yet `delta_P = 2.0`, continuation diff `1.0`), `audit_normalized_block_state_adequacy` sets `kernel_valid = true` and `state_adequacy_certified = false`.
13. **`C13` (`v10` `tiny-Z` Cost Aliasing)**: On $H = \begin{pmatrix}10^{-8}&0\\2\times 10^{-8}&0\end{pmatrix}$ (`delta_P = 0` yet `delta_c0 = log(2) = 0.6931`), `audit_normalized_block_state_adequacy` rejects adequacy (`state_adequacy_certified = false`).
14. **`C14` (`v10` Option Expressiveness)**: Quantifies the single-option Jensen loss (`T_fixed = 2.0527` vs multi-exit Cole–Hopf `T_CH = 0.3991`, `gap = +1.6536`).
15. **`C15` (`v10` Cyclic SSP Resolvent Amplification)**: On $P_{\text{ret}} = 0.99$ (`bellman_residual = 0.01`, `true_value_error = 1.0`, `||(I - P)^{-1}||_inf = 100.0`), `certify_cyclic_ssp_policy_via_lyapunov_witness` encloses `V_true = 100.0` via Lyapunov witness $w = 100$.

---

## 2. Milestone `M2.1` + Post-Audit Closure `WP0` ([m21_qgap_collar_ablation.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_qgap_collar_ablation.py), [m21_ablation_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_ablation_results.json), [m21_economic_gate_verdict.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_economic_gate_verdict.json), [m21_post_audit_closure.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_post_audit_closure.json))

- **Evaluation Counting & Online Cache Scope (`v10 E03`, `C01`, `C04`)**:
  - `m21_ablation_results.json` evaluates **`2,400` unique physical test tasks** across **`6` arms = `14,400` method-task evaluations** (`14,400 / 14,400` certified, `0` bound violations) under pre-announced `begin_test_epoch(..., epoch_tasks)` batches, plus a standalone single-worker 3D `splu` scaling ladder (`21^3 -> 25^3 -> 27^3 -> 31^3`, `9,261 -> 29,791` DOF, `v10 E01`).
  - Post-`89761ff` bug closure (`WP0`) repairs atomic cache row extension (`ep_eval_nodes_tuple`) in `KilledCollarDWRPlanner._upgrade_waypoint_to_current_exact` / `_slice_task_dwr_op` (`C01`) and populates real per-action `root_action_q_bounds` (`C04`), verified in `m21_post_audit_closure.json`.
  - All `8 / 8` streams hit the pre-declared economic `STOP` gate (`F11` `+59.27%..+221.46%`, best candidate `+0.78%..+58.04%` slower than `ExactRing` / `StructMem`) due to `5.0 / 5.0` global epoch `splu` factorizations and $O(N|\mathcal{R}|)$ witness matmuls (`STOP_GLOBAL_GRID_WITNESS_AND_MONOLITHIC_LU`).

---

## 3. Milestone `M2.2a/b` — 2D Multi-Room State-Adequate Portal Quotients & Conductance Discovery ([m22_portal_quotient_pilot.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m22_portal_quotient_pilot.py), [m22_pilot_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m22_pilot_results.json), [m22_pilot_summary.png](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m22_pilot_summary.png))

- **Part A (`M2.2a` Multi-Room Graph Falsification Gate — `4 / 4` Passed)**: Equivalent lanes stay compressed (`4.0x`, `0` splits, `0` regret); entry-dependent room barrier splits aliased doorways (`regret 0.5134 -> 2.05e-5`); `tiny-Z` exit/cost aliasing fails closed (`delta_H = 2.82e-5`, `delta_P = 1.999`); cyclic 3-room drift loop (`||(I - P_SMDP)^{-1}||_inf = 45.19`) proves `0.0` (`1.22e-15`) multi-exit Cole–Hopf interface loss vs `+1.0148` fixed single-option Jensen loss.
- **Part B (`2D` 16-Room Streaming `K = 50` Unseen Goals — `8,000 / 8,000` Certified, `0` Bound Violations)**:

| Cohort (`K = 50` Unseen Goals, All Offline + Discovery Charged) | `FullGrid_Exact_Direct` (ms) | `LocalSchur_Uncompressed` (ms / Speedup vs `FullGrid`) | `Portal_Coarse_NoSplit` (ms / Mean Regret / Cert%) | `UniformGrid_AdaptiveQuot` (ms / DOFs) | `M22a_KnownWall_AdaptiveQuot` (ms / DOFs / Max Regret) | `M22b_Conductance_AdaptiveQuot` (`0` Wall Hints, ms / DOFs / Speedup vs `FullGrid`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Dev 12-Map` (`2D 49^2`) | `254.5` | **`111.2 ms`** (**`2.29x`**, `p = 2.75e-10`) | `100.1 ms` (`12.60` reg, `0%`) | `258.7 ms` (`278.3`) | `286.7 ms` (`265.4`, `0.028`) | `275.4 ms` (`267.8`, `0.92x`) |
| `Confirm 8-Map` (`2D 49^2`) | `288.2` | **`123.0 ms`** (**`2.34x`**, `p = 5.89e-8`) | `128.0 ms` (`16.05` reg, `0%`) | `270.7 ms` (`278.8`) | `329.6 ms` (`266.6`, `0.026`) | `314.5 ms` (`266.4`, `0.92x`) |
| `Confirm 8-Map` (`2D 65^2`) | `516.6` | **`219.3 ms`** (**`2.36x`**, `p = 1.30e-8`) | `186.5 ms` (`21.50` reg, `0%`) | `424.0 ms` (`376.2`) | `486.4 ms` (`366.6`, `0.023`) | `531.7 ms` (`364.9`, `0.97x`, `p = 0.586`) |
| `1-Worker Rotated` (`4-Map 65^2`) | `469.0` | **`195.3 ms`** (**`2.40x`**, `p = 6.42e-4`) | `142.6 ms` (`17.66` reg, `0%`) | `369.9 ms` (`377.8`) | `380.9 ms` (`369.6`, `0.023`) | **`391.0 ms`** (`369.3`, **`1.20x`**, `p = 0.0350`) |

---

## 4. Milestones `M2.3 & M2.4` — Large-Scale 3D Planar Portals (`35^3 -> 47^3 -> 59^3`), Seam-Free Integral Compression, & Continual World Updates ([m23_m24_3d_portal_scale.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m23_m24_3d_portal_scale.py), [m23_m24_3d_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m23_m24_3d_results.json), [m23_m24_3d_summary.png](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m23_m24_3d_summary.png))

Conquers the 3D planar-portal seam singularity ($O(1/h^2)$ jump of $A_{\Gamma\Gamma} L$) and multi-room $\exp(-V/\lambda)$ underflow across `27`-room baffled 3D buildings (`51` active planar doorways, `3` closed doorways, `6` internal 3D room baffles, 3D GP world fields):
- **Seam-Free Integral Portal Equation & Global M-Matrix Subsolution**: Pre-multiplying $S_{\Gamma\Gamma} z^*_\Gamma = (A_{\Gamma\Gamma} + M) z^*_\Gamma = r_\Gamma$ by the block-diagonal doorway inverse $A_{\Gamma\Gamma}^{-1} \ge 0$ yields $(I_\Gamma - K_{\Gamma\Gamma}) z^*_\Gamma = \hat{r}_\Gamma$ ($K_{\Gamma\Gamma} = A_{\Gamma\Gamma}^{-1}(-M) \ge 0$). The 1-step smooth Row-Coupled Howard field $W_{\text{lo}} = K_{\Gamma\Gamma} L \underline{v}^* + \hat{r}_\Gamma$ satisfies $S_{\Gamma\Gamma} W_{\text{lo}} = r_\Gamma - (-M)(W_{\text{lo}} - L \underline{v}^*) \le r_\Gamma$ and $A z_{\text{sub}} \le 0$ (`max residual <= 9.95e-14`) globally across up to `190,645` 3D DOFs, paired with Doob/Lyapunov sub-stochastic defect closure $(I - \widetilde{P})\hat{u} = \hat{r}_\Gamma / w_{\text{lyap}}$.
- **Zero-Hint 3D Bottleneck Discovery**: `discover_3d_bottleneck_planes_zero_hint` recovers **`100%` (`24 / 24` maps)** of jittered 3D wall planes from occupancy conductance alone (`22–99 ms`, `100%` charged to `M2.3`).

### 4.1 Part A (`M2.3`: 3D Progressive Scale & Streaming Self-Amortization, `K = 24` Unseen 3D Goals/Map — `0 / 576` Bound Violations)

| 3D Cohort (`K = 24` Unseen Goals, `eps = 0.25`) | Free DOFs / `|\Gamma|` -> Active DOFs (Compression) | `FullGrid_SPLU` (ms, Mode) | `LocalSchur_3D` (ms) | `Warm-ILU-BiCGSTAB` (ms, Mean/Goal) | `M2.3_SeamFree_Portal` (ms; `First6 -> Last6` ms/g) | Speedup vs `SPLU` / `LocalSchur` / `Warm-ILU` (`Planner` \| `Incl-GP`, $p_{2s}$) | Quality (`M2.3` Max Regret vs `Coarse_L0` Mean/Max Regret) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Dev 6-Map` `35^3`** | `38,218` / `2,499` -> **`227.5`** (**`11.1x`** port, **`170x`** grid) | `28,582.5` (full `K=24`) | `7,230.4` | `4,328.7` (`166.0`) | **`2,341.5 ms`** (`117.8 -> 67.5`) | **`12.21x`** / **`3.09x`** / **`1.85x`** (`1.77x`, `p = 1.52e-4`) | `0.040` vs `0.294 / 0.808` (`0%` cert) |
| **`Confirm 6-Map` `35^3`** | `38,238` / `2,499` -> **`242.8`** (**`10.5x`** port, **`160x`** grid) | `32,128.7` (full `K=24`) | `7,312.5` | `4,947.1` (`193.0`) | **`2,758.1 ms`** (`142.3 -> 79.1`) | **`11.65x`** / **`2.65x`** / **`1.79x`** (`1.74x`, `p = 7.32e-5`) | `0.080` vs `0.330 / 1.033` (`0%` cert) |
| **`Confirm 6-Map` `47^3`** | `94,814` / `4,131` -> **`301.7`** (**`13.8x`** port, **`316x`** grid) | `189,823.0` (`2`-solve proj) | `27,701.7` | `17,270.3` (`669.0`) | **`10,380.6 ms`** (`525.5 -> 331.5`) | **`18.29x`** / **`2.67x`** / **`1.66x`** (`1.64x`, `p = 3.66e-4`) | `0.044` vs `0.478 / 1.179` (`0%` cert) |
| **`Confirm 6-Map` `59^3`** | `190,574` / `6,171` -> **`340.8`** (**`18.2x`** port, **`563x`** grid) | `609,076.7` (`25.4s`/solve proj) | `89,319.9` | `39,725.0` (`1,519.6`) | **`30,256.8 ms`** (`1,584.2 -> 846.5`) | **`20.13x`** / **`2.95x`** / **`1.31x`** (`1.31x`, `p = 0.00756`) | `0.021` vs `0.551 / 1.283` (`0%` cert) |

- **Critical Numerical Stability Finding on `59^3`**: Unscaled global `Warm-ILU-BiCGSTAB` (`rtol = 1e-11, atol = 1e-15`) suffers severe desirability underflow stagnation on `59^3` 6-room detours (`max value drift vs SPLU = 134.17`), whereas `M2.3`'s Doob/Lyapunov gauge-scaled portal operator maintains `0 / 576` bound violations and `max_deployed_regret <= 0.080` (`<= 0.021` on `59^3`).

### 4.2 Part B (`M2.4`: Continual 3D Evolving-World Lifecycle on `Confirm 47^3` [`94,814` DOFs], `1` Init + `5` Update Epochs $\times$ `6` Tasks — `0 / 432` Bound Violations)

| Continual 3D Stream (`6` Maps `62000..62005`, `36` Tasks/Map) | `LocalSchur_Continual` (Life / Post-Init Marg ms) | `Warm-ILU_Continual` (Life / Post-Init Marg ms) | `M2.4_Continual_Portal` (Life / Post-Init Marg ms) | Marginal Speedup vs `Warm-ILU` / `LocalSchur` ($p_{2s}$) | Retained Portal Cache Entries / Active DOFs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`local_room_sensor_updates`** (`2 / 27` rooms/epoch) | `44,676.7` / `34,208.3` | `33,709.4` / `28,538.3` | **`14,730.7` / `10,591.5`** | **`2.69x`** (`p = 3.25e-6`) / **`3.23x`** (`p = 4.63e-7`) | **`94.7` entries** / `289.5` DOFs (`0` viols) |
| **`global_smooth_field_updates`** (`27 / 27` rooms/epoch) | `62,989.2` / `52,289.8` | `35,582.5` / `29,614.6` | **`23,279.5` / `18,657.5`** | **`1.59x`** (`p = 2.23e-4`) / **`2.80x`** (`p = 3.30e-7`) | `0.0` (full refresh) / `286.2` DOFs (`0` viols) |

---

## 5. Reproducible Execution

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/usr/bin/python3 quotient_phase2/m20_contracts.py
/usr/bin/python3 quotient_phase2/m21_postprocess_closure.py
/usr/bin/python3 quotient_phase2/m22_portal_quotient_pilot.py
/usr/bin/python3 quotient_phase2/m23_m24_3d_portal_scale.py
```
