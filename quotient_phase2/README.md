# `quotient_phase2`: Contract-Hardened Phase-II Certification, Dyadic Portal Quotient, & 3D Attribution Suite (`M2.0`–`M2.3.2` Frozen Release)

Isolated Phase-II research package importing the frozen Phase-I library (`../green_response/`, locked byte-for-byte at `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"`) strictly read-only.

## 0. Provenance & Non-Destructive Artifact Ledger (`B6-D01`)

All historical JSON artifacts from commits `89761ff`, `ec75871`, and `b6ff40d` are preserved **100% byte-untouched** (`verified at startup of m232_final_closure.py`). Final `M2.3.2` release patches (`B6-01..B6-05`) and single-worker balanced replay records write exclusively to `m232_*` standard RFC-8259 JSON artifacts (`allow_nan=False`):

| Artifact / Package | SHA-256 / Manifest Identifier | Provenance & Scope |
| :--- | :--- | :--- |
| `../green_response/*.py` (Frozen Phase-I) | `271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d` | Byte-frozen since `a26c116` (`verified_intact = true` at startup of every script) |
| `quotient_phase2/*.py` (**Final `M2.3.2` Release**) | `1901d24f34b003340701870eee6631a84829976188a164b6430281ee9a5ddb76` | Identical manifest embedded in `m232_contract_and_ring_closure.json` and `m232_targeted_replay_results.json` |
| `m21_ablation_results.json` (Frozen `89761ff`) | `634c15e52fb3a8181f738baef40b8d7c30e690a8600a7cf1e30b6ca17a3c4fc1` | Byte-untouched `89761ff` campaign (`8/8` global-grid DWR streams `STOP`) |
| `m20_contract_results.json` (Frozen `ec75871`) | `bdad834622c2ab0215be84c2e3cfb4473f5b242e053d9b7bef8e792081c67004` | Byte-untouched `ec75871` 15-gate verification (`generating_phase2_py_sha256 = c3f7a8a2...`) |
| `m22_pilot_results.json` (Frozen `ec75871`) | `55d7e1ea176d2ad53d173595339c21216fc6f210857b5d28e30b98c163a3d892` | Byte-untouched `ec75871` 2D portal pilot (`generating_phase2_py_sha256 = c3f7a8a2...`) |
| `m23_m24_3d_results.json` (Frozen `ec75871`) | `8fb6fb84749dfa640e5f5394c65db71426302a365e95a512c25dd896bce30f05` | Byte-untouched `ec75871` initial 3D campaign (`generating_phase2_py_sha256 = c3f7a8a2...`) |
| `m231_audit_closure.json` (Frozen `b6ff40d`) | `4a0e2514a351ab7102dc9e54c6fce38dc9b5b8325ec8c277aa96aaa09257c4a9` | Byte-untouched `b6ff40d` `EC-01..EC-06` + nested dyadic closure (`generating_phase2_py_sha256 = f530c1b8...`) |
| `m231_fair_ablation_results.json` (Frozen `b6ff40d`) | `f844a1028ec72ca7e0c26f77106b65d622412c8efb500fbe1e7f0869706cf003` | Byte-untouched `b6ff40d` 3-worker 6-arm campaign (`generating_phase2_py_sha256 = f530c1b8...`) |
| `m232_contract_and_ring_closure.json` (**New `M2.3.2` WP-1**) | `06b441563dd2f30bffc982cd437b7b5d4a497636451bc5cf69bf241339410dba` | Closes `B6-01..B6-05` + proves `792/792` official-task ring invariance (`0` warnings, strict RFC-8259 JSON) |
| `m232_targeted_replay_results.json` (**New `M2.3.2` WP-2/3**) | `9979d61a4de74d4e05fc8d1beff2103a4d292c693be4ebd1fc422004f91fc730` | `1`-worker exact-balance `47^3` 3-arm cache study + `47^3/59^3/Continual` `AB/BA` replay (`1,440` saved task events, `360` `4`-inequality policy checks, `0` violations) |

---

## 1. Mathematical Contracts & Public-API Hardening (`M2.0` + `M2.3.1` + `M2.3.2`)

1. **`M2.0` (`C01`–`C15`) & `M2.3.1` (`EC-01`–`EC-06`, `7.3`)**: Closed and re-verified (`0` warnings), covering four-object separation ($U, H, Z, P$), centered bilinear DWR, `tiny-Z` exit/cost adequacy, single-option vs. Cole–Hopf Jensen gap, cyclic SSP Lyapunov bounds, unit-terminal gauge shift invariance ($\phi_{\text{goal}} \in [-1000, 1000]$), `validate_cole_hopf_lmdp` & single-room guards, directed reachability + floor-free CSR-preserving policy evaluation, runtime 30-step Howard & unclipped Lyapunov verification ($s_0 = (I-K)w_{\text{lyap}} > 0$), reference non-convergence rejection, contiguous step-indexed `RecedingHorizonCertificateChain`, and strictly nested recursive dyadic portals (`1 -> 4 -> 16 -> 64`, `0` cross-parent blocks on `11x11` portals).
2. **`M2.3.2` Final Release Closure ([m232_final_closure.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m232_final_closure.py), [m232_contract_and_ring_closure.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m232_contract_and_ring_closure.json))**:
   - **`B6-01` (Complete Directed Goal-Ring Support)**: `extract_directed_goal_ring_in_room` extracts $R_G = \{ j \in G : \exists i \in \Omega \setminus G,\; A_{ij} < 0 \}$ by uniting room-interior and incident-portal incoming edges across `SeamFreePortal3DPlanner.solve_unseen_goal`, `solve_exact_reference_value`, and `MatrixFreeExactSchurKrylov3DPlanner.solve_unseen_goal`. Verified across `36 / 36` `17^3` asymmetric-drift cases (`interior_point`, `interior_3x3x3`, `portal_adjacent_slab_thickness{1,2,3}`, and `whole_goal_room` at $\varepsilon \in \{0.25, 0.01, 0.001\}$) with direct verification of $L \le V^* \le J^{\hat{\mu}} \le U$ (`thickness-3 eps=0.001` regret `2.29e-7`, internal reference error `4.44e-16`), and confirmed **`0 / 792` changed rings** across all official generated tasks.
   - **`B6-02` (Intra-Query vs. Cross-Query Cache Separation)**: All cache ablation modes preserve intra-query memoization (`0` repeated intra-query `L0` solves) while strictly separating cross-queryLU solve counts (`[93, 3] < [93, 93] < [93, 95]`).
   - **`B6-03` (Explicit Guarantee Tiers & Direct Perturbation Guard)**: Separates `float64_toleranced_model_enclosure` (`Portal / MatrixFree`, runtime-verified discrete KL-LMDP sub-/supersolutions within IEEE-754 float64 tolerances, not hardware interval arithmetic) from `high_accuracy_numerical_reference` (`SingleLU_GoalCapacitance`, `certified = False`, checking componentwise relative residual $\le 10^{-7}$ so `+1e-12` `PerturbedLU` fault injection is rejected with componentwise residual `1.03e8`).
   - **`B6-05` (Portal-Start Root Readiness & GC Cleanup)**: Priming `policy_handle.action_distribution(s_i)` inside `query_ms` yields `0` post-query room backsolves on both `interior_start` (`[0]` cached) and `portal_start` (`[0, 1]` cached), with verified weakref GC release between arms.

---

## 2. Summary of Prior Milestones (`M2.1`, `M2.2`, Frozen `ec75871` & `b6ff40d`)

- **`M2.1` ([m21_economic_gate_verdict.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m21_economic_gate_verdict.json))**: `14,400 / 14,400` certified (`0` violations), formal economic `STOP` across all `8 / 8` streams (`F11` `+59.3%..+221.5%`) due to monolithic global `splu(A_t)` refactorizations and full-grid witness matmuls.
- **`M2.2` ([m22_pilot_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m22_pilot_results.json))**: `4 / 4` graph families passed; in 2D soft-wall 16-room grids (`K = 50`), uncompressed `LocalSchur` beats `FullGrid` by `2.29x–2.40x` (`0 / 8,000` violations), whereas iterative 2D doorway splitting remains slower than `LocalSchur`.
- **Frozen `b6ff40d` 3-Worker Multi-Baseline Snapshot ([m231_fair_ablation_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m231_fair_ablation_results.json))**: Across `6` repeated-measure seeds `63000..63005` (`35^3 -> 47^3 -> 59^3`, `K = 24`, deterministic cyclic Latin shift, `workers = 3`, `792` aggregate `SingleLU` value checks + `396` $\varepsilon$-regret policy checks), `M231_Portal_CacheOn` beat `SingleLU_GoalCapacitance` by **`1.57x` (`35^3`), `2.29x` (`47^3`), `2.39x` (`59^3`), and `4.74x` (`Continual 47^3`)** (`resident factor+cache arrays on 59^3: 1,475.8 MB vs. 2,135.2 MB global LU`, not whole-process peak RSS) and beat `Verified_Global_WarmILU` (`uniform residual + SingleLU fallback; internal Krylov stage timing is a pipeline diagnostic, not an independent standalone raw baseline`) by `2.80x–3.91x`. Against closest neighbor `MatrixFree_ExactSchur_Krylov`, `3`-worker relative time savings (`1 - T_Portal / T_MF`) were **`-12.15%` (`35^3`, `0.89x`), `19.79%` (`47^3`, `1.25x`), `17.56%` (`59^3`, `1.21x`), and `16.60%` (`Continual 47^3` marginal, `1.20x`)**—establishing positive gains on larger portals while **NOT passing the pre-declared `20%` relative time-saving gate (`NOT_MET`)**. Queries certified without full-portal Krylov defect closure were `93.8%` (`Dev 35^3`), `91.0%` (`35^3`), `79.2%` (`47^3`), and `57.6%` (`59^3`) (still executing room-local LU solves, goal capacitance, and basis reads).

---

## 3. Authoritative `M2.3.2` Single-Worker Balanced Replay & Per-Task 4-Inequality Ledger ([m232_targeted_replay_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m232_targeted_replay_results.json), [m232_targeted_replay_summary.png](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m232_targeted_replay_summary.png))

Executed strictly single-process (`workers = 1`, zero cross-worker contention) on `Replay Cohort 63000..63005` (`6` independent map seeds reused for post-patch verification), saving **`1,440` per-task event records** (`lo, hi, reference_value, policy_value`) and reducing all denominators directly from events (**`1,440 / 1,440` value enclosures and `360 / 360` full four-inequality checks $L \le V^* \le J^{\hat{\mu}} \le U$ satisfied, `0` violations, max deployed regret `0.0478`**):

### 3.1 Corrected `47^3` Three-Arm Cache Causal Ablation (`workers = 1`, Exact `2x` `3x3` Latin Balance, Intra-Query Memoization `ON`)

| Cache Mode (`Replay 47^3`, `K = 24`, Rank Counts `[2,2,2]`) | Intra-Query Memoization | Query-Boundary Invalidation | Mean Total Planner Time (ms) | Mean Query Time (`First6 -> Last6` ms) | Mean Local LU Solves / Map | `CacheOn` Speedup / Net Time Saving ($p_{2s}$) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **`QueryCold`** | `ON` | Clear `L0..L3` per query | `15,275.2` | `599.2` (`528.5 -> 592.8`) | `21,456.8` | **`1.79x` / `43.98%`** (`p = 1.48e-6`) |
| **`CacheL0Only`** | `ON` | Keep `L0`, clear `L1..L3` | `12,181.7` | `470.6` (`414.0 -> 440.3`) | `19,008.8` | **`1.42x` / `29.75%`** (`p = 1.20e-4`) |
| **`CacheOn_Persistent`** | `ON` | Keep `L0..L3` across queries | **`8,557.5`** | **`319.1`** (`364.6 -> 241.6`) | **`9,322.2`** | Reference (`72/72` `L<=V*<=J<=U`) |

### 3.2 Exclusive Single-Worker `AB/BA` Closest-Neighbor Head-to-Head (`M231_Portal_CacheOn` vs. `MatrixFree_ExactSchur_Krylov`)

| Replay Block (`workers = 1`, Exact `3 AB / 3 BA` Balance) | `Portal_CacheOn` Mean (ms) | `MatrixFree_ExactSchur` Mean (ms) | Speedup $S$ | Net Time Saving $1 - 1/S$ | Equal-Time $p_{2s}$ (95% CI ms) | `20%` Saving Gate (`1`-Sided $p_{0.80}$) | Cohort-Mean / Per-Seed Crossing $k \le 24$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Replay 47^3`** (`K = 24`) | **`9,036.0`** | `10,652.0` | `1.18x` | **`15.17%`** | **`0.0174`** (`[-2805, -427]`) | **`NOT_MET`** (`p = 0.857`) | Mean `k = 6`; seeds `[18, 9, 1, 1, 7, None]` |
| **`Replay 59^3`** (`K = 24`) | **`28,319.4`** | `32,831.4` | `1.16x` | **`13.74%`** | **`0.00511`** (`[-6954, -2070]`) | **`NOT_MET`** (`p = 0.939`) | Mean `k = 13`; seeds `[18, 6, 12, 1, 17, 17]` |
| **`Continual 47^3` Marginal** (`5` local updates $\times$ `6` tasks, rebuild charged) | **`10,059.4`** | `11,174.0` | `1.11x` | **`9.98%`** | **`1.41e-4`** (`[-1390, -839]`) | **`NOT_MET`** (`p = 1.000`) | Retains `81.3` `(portal_id, lv)` entries |
| **`Continual 47^3` Lifecycle** (`Init + 5` updates, rebuild charged) | **`13,028.8`** | `14,052.8` | `1.08x` | **`7.29%`** | **`0.0130`** (`[-1721, -327]`) | **`NOT_MET`** (`p = 0.999`) | `36/36` continual `L<=V*<=J<=U` per arm |

---

## 4. Reproducible Execution

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
/usr/bin/python3 -W error -u quotient_phase2/m232_final_closure.py --contracts-only
/usr/bin/python3 -u quotient_phase2/m232_final_closure.py --self-test
/usr/bin/python3 -u quotient_phase2/m232_final_closure.py
```
