# `quotient_phase2`: Contract-Hardened Phase-II Feasibility Suite (`M2.0` & `M2.1`)

Isolated Phase-II research package importing the frozen Phase-I library (`../green_response/`, locked byte-for-byte at `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"`) strictly read-only.

- `phase2_package_py_sha256`: `"cdd584d99b012aa3f6668680604bec7c2db12fa99da15db30f8fd348ce55e803"`
- `frozen_phase1_package_py_sha256`: `"271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"` (`verified_intact = true`)

---

## 1. Milestone `M2.0` — Mathematical Contracts & 10-Counterexample Gate (`m20_contracts.py`, `m20_contract_results.json`)

Closes all 10 small-matrix counterexamples (`P2A-01..05`, `P2B-01..04`, `P2C-01..02`) in `3.46 ms` (`ALL_10_COUNTEREXAMPLE_GATES_PASSED = true`):

1. **`C01` (`P2A-01`)**: Separates unbounded Green source response $U = A^{-1} E_\Gamma \ge 0$ (`max = 23.81 > 1` rejected as sub-Markov) from killed exterior hitting kernel $A_{II} H = -A_{I\Gamma}$ (`0 <= H`, `max row sum = 0.476 <= 1.0`).
2. **`C02` (`P2A-02`)**: Rejects interior-omitted collar concatenation (`[0.5, 0.25] != [2/3, 1/3]`) and verifies `0.0` error for both exact Schur back-substitution and zero-extended full-exterior remainder correction (`R_full = B - A_{II} H_lifted`).
3. **`C03` (`P2A-03`)**: On swapped stochastic rows ($H = \begin{pmatrix}0.9&0.1\\0.1&0.9\end{pmatrix}$ vs $\widetilde{H} = \begin{pmatrix}0.1&0.9\\0.9&0.1\end{pmatrix}$ where $(H-\widetilde{H})\mathbf{1} = 0$ yet $|(H-\widetilde{H})f| = 0.8$), verifies `bound_normalized_continuation_dwr` encloses both denominator $H\mathbf{1}$ and continuation numerator $H(f-\mu\mathbf{1})$.
4. **`C04` (`P2A-04`)**: `Phase2DecisionCertificate` fail-closed rejects a deployed policy with regret `100.0` despite root $Q^*$-gap `0.0` under `full_policy_enclosure`, while scaling `receding_horizon_root_action_enclosure` by $m \eta$ (`4 * 0.10 = 0.40`).
5. **`C05` (`P2A-05`)**: Rejects radial exponential $\psi = (1, e^{-1})^\top$ as an unverified super-adjoint on asymmetric $A = \begin{pmatrix}1&-0.9\\-0.1&1\end{pmatrix}$ (`min slack = -0.532`), while verifying that `prepare_bilinear_dwr_operator` still produces a sound interval by explicitly billing $\|e_p - A^\top \psi\|_1$.
6. **`C06` (`P2B-01`)**: Exposes `-1/6` negative entry in partition-of-unity Galerkin projection $W(W^\top W)^{-1}W^\top$ and verifies non-negativity + row-sum `<= 1` on row-stochastic $\overline{H} = R H L$.
7. **`C07` (`P2B-02`)**: Separates zero point-interval product width (`0.0`) from within-block exit dispersion (`delta_lump = 2.0`) and independent 2-step operator discrepancy (`||R P^2 L - (R P L)^2||_inf = 1.0`), recovering `0.0` defect upon splitting block `{0, 1} -> {0}, {1}`.
8. **`C08` (`P2B-03`)**: Verifies irreversible 3-cycle ratio `729.0` is invariant under diagonal Doob similarity.
9. **`C09` (`P2C-01`)**: Verifies compact-support prior $K_{LR} = 0$ induces nonlocal posterior $K_{LR \mid M} = -0.16$ (`-0.1905` mean shift).
10. **`C10` (`P2C-02`)**: Verifies single-block Schur perturbation shifts all `3 / 3` coupled global interface coordinates.

---

## 2. Milestone `M2.1` — Controlled $2 \times 2$ Ablation & 3D Scale Ladder (`m21_qgap_collar_ablation.py`, `m21_ablation_results.json`, `m21_ablation_summary.png`)

Evaluates **Killed-Domain Local Collar Remainder Lifting** $\times$ **Operator-Verified Bilinear Primal-Dual DWR (`Hf` & `H1`) + Same-State Dominated-Branch Pruning** under the strict **`full_policy_enclosure` ($\varepsilon_{\text{tol}} = 0.25$)** contract across **`14,400` test tasks (`14,400 / 14,400` certified, `0` bound violations)**, charging 100% of `ref_cache_build_ms + collar_lift_ms + dwr_witness_and_audit_ms + dp_ms + fallback_exact_ms`.

### 2.1 Part `M2.1-A`: Unseen-Target Source-Obstruction & Sub-Markov Positivity (`16` Maps)
- Fixed historical columns satisfy $(A V)|_{\Gamma_{\text{new}}} = 0 \implies \|E_{\Gamma_{\text{new}}} - A V c\|_\infty \ge 1.000$.
- Principal killed-collar lifts ($A_{CC} H_C = B_C$, `hops = 2, 3, 4` covering `1.6%–4.9%` of grid nodes in `3.5–4.0 ms` in 2D / `15.2–21.2 ms` in 3D across 6 unseen targets) achieve **`0` negative entries and `0` `Z > 1` rows (`100%` strict sub-Markov valid without clipping)** while driving `3D 21^3` rim row-sum residuals down (`2.32 -> 1.23 -> 0.68`).

### 2.2 Part `M2.1-B` & `M2.1-C`: Continual Full-Lifecycle Results & Stopping-Gate Verdict

| Cohort & Stream (`full_policy_enclosure`, `eps = 0.25`, `0` Viols) | Best Classical (Life / Marg ms) | `F00` Primal (Life / Marg ms) | `F10` +CollarLift (Life / Marg ms) | `F01` +BilinearDWR (Life / Marg ms) | `F11` Lift+DWR (Life / Marg / Refreshed Tasks / Test LUs) | Economic Gate Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Dev 12-Map`: `2D 51^2 GP` | **`269.1` / `226.1`** (`ExactRing`) | `329.0` / `274.5` | `356.2` / `301.7` | `831.6` / `742.5` | `865.1` / `779.7` (`262/360`, `5.0` LU) | **`STOP`** (`-221.5%` life) |
| `Dev 12-Map`: `2D 51^2 Param` | **`298.2` / `183.3`** (`ExactRing`) | `357.7` / `236.7` | `371.8` / `255.0` | `888.9` / `723.8` | `826.1` / `665.7` (`238/360`, `5.0` LU) | **`STOP`** (`-177.1%` life) |
| `Dev 12-Map`: `3D 21^3 GP` | **`6467.0` / `5156.4`** (`StructMem`) | `7558.3` / `6229.5` | `7112.0` / `5907.4` | `12953.5` / `8876.1` | `12480.0` / `8624.7` (`266/360`, `5.0` LU) | **`STOP`** (`-93.0%` life) |
| `Dev 12-Map`: `3D 21^3 Param` | **`8253.9` / `5068.3`** (`StructMem`) | `9056.7` / `5745.1` | `8861.9` / `5538.8` | `13918.6` / `7871.5` | `15602.7` / `8820.0` (`226/360`, `5.0` LU) | **`STOP`** (`-89.0%` life) |
| `Conf 8-Map`: `3D 21^3 GP` | **`9861.6` / `8181.5`** (`ExactRing`) | `17669.6` / `14548.1` | `16983.0` / `14147.0` | `15585.5` / `9261.0` | `15706.6` / `11141.3` (`161/240`, `5.0` LU) | **`STOP`** (`-58.0%` life) |
| `Conf 8-Map`: `3D 21^3 Param` | **`8721.6` / `5454.5`** (`StructMem`) | `10925.4` / `6618.5` | `9544.4` / `5976.4` | `14341.5` / `8007.6` | `15723.9` / `8490.2` (`140/240`, `5.0` LU) | **`STOP`** (`-64.4%` life) |
| `Conf 8-Map`: `3D 27^3 GP` | **`39125.6` / `32771.0`** (`ExactRing`) | `47313.4` / `37118.6` | `39998.9` / `32991.9` | `76226.8` / `48894.1` | `77663.4` / `50582.0` (`161/240`, `5.0` LU) | **`STOP`** (`-2.2%` `F10` / `-94.8%` `F01`) |
| `Conf 8-Map`: `3D 27^3 Param` | **`52219.4` / `32791.4`** (`ExactRing`) | `52624.1` / `32919.4` | `60095.1` / `38483.8` | `87780.2` / `47143.4` | `85134.5` / `43361.1` (`153/240`, `5.0` LU) | **`STOP`** (`-63.0%` `F11` life) |

- **3D Single-Worker `SuperLU` Scaling Ladder (`M2.1-C`)**: `21^3` (`9,261` DOF): `320.3 ms, 56.2 MiB` -> `25^3` (`15,625` DOF): `929.6 ms, 127.3 MiB` -> `27^3` (`19,683` DOF): `1,785.8 ms, 188.6 MiB` -> `31^3` (`29,791` DOF): `3,970.1 ms, 346.6 MiB`.
- **Root-Cause Attribution & Architectural Conclusion for `M2.2`**:
  1. *What worked mathematically*: `F11` certifies `87–100 / 240` tasks (`36%–42%`) with **zero new backsolves**, eliminates `99%+` of terminal DP fallbacks (`54/240 -> 2/240` on `27^3 Param`), and exhibits significant `Lift x DWR` synergy on `3D 27^3 Param` (`interaction = -9,346.7 ms, p = 4.74e-4`).
  2. *Why global-grid DWR hits the pre-declared `STOP` gate*: (a) **Monolithic epoch-LU cliff**—with `6` tasks per epoch spanning `~8–9` catalog targets, whenever **even 1 task** needs an exact waypoint refresh, `_ensure_current_lu()` pays the **entire global 3D `splu(A_t)`** (`5.0 / 5.0` test-epoch LUs, `fallback_exact_ms = 32.5 s` on `27^3`); and (b) **Full-grid $O(N |\mathcal{R}|)$ witness bank overhead** (`ref_cache_build_ms = 19.5 s` + `dwr_witness_and_audit_ms = 10.1 s` on `27^3`).
  3. *Direct consequence for `M2.2`*: Global $N$-node primal/dual witness banks paired with monolithic global `splu` fallbacks are **formally stopped**. In `M2.2`, both the transition brackets ($\overline{H} = R H L$) and any fallback solves must operate strictly on **decomposed local cells $\{\Omega_c\}$** (`11^3..15^3` per room, `< 15 ms` local `splu`), so a local refresh never triggers a global $N \times N$ factorization.

---

## 3. Reproducible Execution

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 quotient_phase2/m20_contracts.py

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  /usr/bin/python3 quotient_phase2/m21_qgap_collar_ablation.py
```
