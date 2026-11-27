# `quotient_phase2`: Contract-Hardened Phase-II Certification, Adaptive Sub-Portal PoU-Quadtree Coarsening, & 3D SISC Suite (`M2.0`–`M2.3.3`)

Isolated Phase-II research package importing the frozen Phase-I library (`../green_response/`, locked byte-for-byte at `package_py_sha256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"`) strictly read-only.

## 0. Provenance & Non-Destructive Artifact Ledger

All 10 historical JSON artifacts from commits `89761ff`, `ec75871`, `b6ff40d`, and `ec3c58f` are preserved **100% byte-untouched** (`verified automatically at startup of both verify_m232_release.py and m233_sisc_subportal_quadtree.py`). Milestone `M2.3.3` adds the isolated SISC algorithmic unlock (`m233_sisc_subportal_quadtree.py`) and writes strictly to standard RFC-8259 JSON (`allow_nan=False`) and new figures:

| Artifact / Package | SHA-256 / Manifest Identifier | Provenance & Scope |
| :--- | :--- | :--- |
| `../green_response/*.py` (Frozen Phase-I) | `271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d` | Byte-frozen since `a26c116` (`verified_intact = true` at startup of every script) |
| `quotient_phase2/*.py` (**`M2.3.3` SISC Unlock**) | `3dcf3834cc70af209c83afd3c3a494fb7dc0d0cddd17b1e2d1250ff8d65dc23c` | Adds `m233_sisc_subportal_quadtree.py` (`ad09645a...`) & `generate_manuscript_mechanism_figure.py` (`b723215c...`); all `m20..m232` code & 10 JSONs untouched |
| `m20_contract_results.json` .. `m232_targeted_replay_results.json` (`10` Frozen JSONs) | `bdad8346...` .. `9979d61a...` | Byte-untouched archives across `89761ff`, `ec75871`, `b6ff40d`, and `ec3c58f` |
| `m232_release_verification_report.json` | `0786ce5eeb76f398dda737e18fd9eec0b22e76254a6bfb1228f8ed9c8b523c3d` | Read-only zero-slack audit of frozen `M2.3.2` (`1,440/1,440` events, `360/360` policy checks, `24` adversarial boundary checks) |
| `m233_sisc_unlock_results.json` (**`M2.3.3` SISC Campaign**) | `339e723ff8dca6b9f061c7589de40337e6e2c24e07bac00f6768aeea7ba4539b` | `1`-worker exact `AB/BA` across `35^3/47^3/59^3/Continual 47^3` (`63000..63005`) + **untouched $n=12$ `Confirm 64000..64011` (`47^3`)** (`2,304/2,304` events & `792/792` policy checks verified at **`0.0` slack**, `4/4` fault injections rejected) |
| `m233_fig1_mechanism_and_counterexamples.png` & `m233_sisc_unlock_summary.png` | `5800a4f5...` / `f49ef484...` | Publication-grade 4-panel mechanism/counterexample figure & 4-panel SISC benchmark figure |
| [MANUSCRIPT_CORE_DRAFT.md](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/MANUSCRIPT_CORE_DRAFT.md) | Upgraded SISC Manuscript Draft | Full exact-arithmetic proofs (Props 1–4, Lemma 1, Thms 1–2), complexity table, stage breakdown, `M2.3.2 -> M2.3.3` attribution, & 37 references |

---

## 1. Algorithmic Progression: `M2.3.2` (Uniform Whole-Portal `L0..L3`) $\to$ `M2.3.3` (Sub-Portal PoU-Quadtree `L0..L4`)

In `M2.3.2` ([m232_targeted_replay_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m232_targeted_replay_results.json)), promoting entire doorways uniformly up to `L3` (`64` blocks/portal, `m_cur < 480`) and re-solving three $O(m^3)$ Howard loops per round yielded statistically significant `1`-worker savings over `MatrixFree_ExactSchur_Krylov` (`15.17%` on `47^3`, `13.74%` on `59^3`, `9.98%` continual marginal) but fell short of the pre-declared `20%` engineering time-saving gate (`NOT_MET`) and lost `-12.15%` on `35^3`.

In `M2.3.3` ([m233_sisc_subportal_quadtree.py](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m233_sisc_subportal_quadtree.py), hyperparameters locked strictly on `Dev 61000..61005`), three mathematical & algorithmic advances eliminate those bottlenecks without altering model semantics or `float64_toleranced_model_enclosure` guarantees:
1. **Adaptive Sub-Portal Quadtree Cuts (`L0..L4` Singletons, `m_cap = 768`)**: Splits only high-adjoint-oscillation sub-blocks down to exact `L4` singletons, slashing full-interface Krylov fallback rates from `9.0% -> 0.7%` (`35^3`), `20.8% -> 4.5%–6.2%` (`47^3`), and `42.4% -> 13.9%` (`59^3`).
2. **Nested-Cut $L_0$-Lyapunov Invariance & Warm Howard**: Reuses the single `L0` witness $w_{\mathrm{lyap}} = L_0 v_{\mathrm{lyap}}^{(0)} > 0$ across nested quadtree cuts (refreshing only on `~0.1%` scale-mismatch events) with warm-started Howard iteration.
3. **Partition-of-Unity $(k - 1)$ Child Conservation**: Solves only $k - 1$ children per $k$-way split (`max |K_pou - K_direct| = 9.71e-17`), reducing `47^3` operational room-LU backsolves from `9,010.2` (`M2.3.2`) to **`5,950.3`** (`-34.0%`).

---

## 2. Authoritative `M2.3.3` Single-Worker (`workers = 1`, Exact `AB/BA`) SISC Results ([m233_sisc_unlock_results.json](file://wsl$/Ubuntu-22.04/home/erzhu419/mine_code/Auditable%20Coarse-to-Fine%20Quotient%20Planning/quotient_phase2/m233_sisc_unlock_results.json))

| Benchmark & Cohort (`workers = 1`, Exact `AB/BA`) | $n$ Maps | `PoU-QT` Mean (ms) | `MatrixFree` Mean (ms) | Speedup $S$ | Net Saving (End-to-End incl. GP+Asm) | Paired-$t$ $p_{2s}$ (Sign-Flip $p_{2s}$) | Faster Maps | `20%` Saving Gate ($p_{0.80}$) | Coarse Closure % (No Krylov) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Untouched Confirm 47^3`** (`64000..64011`, $K=24$) | **`12`** | **`7,098.9`** | `10,375.7` | **`1.46x`** | **`31.58%`** *(E2E: `30.74%`)* | **`1.46e-5`** (**`4.88e-4`**) | **`12 / 12`** | **`PASS`** (**`p = 0.00815`**) | **`95.49%`** (`275/288`) |
| **`Replay 59^3`** (`63000..63005`, $K=24$) | `6` | **`26,568.5`** | `37,299.9` | **`1.40x`** | **`28.77%`** *(E2E: `28.37%`)* | **`7.16e-4`** (`0.03125`) | **`6 / 6`** | **`PASS`** (**`p = 0.0374`**) | **`86.11%`** (`124/144`) |
| **`Replay 47^3`** (`63000..63005`, $K=24$) | `6` | **`8,063.9`** | `10,661.7` | **`1.32x`** | **`24.37%`** *(E2E: `23.73%`)* | **`1.22e-3`** (`0.03125`) | **`6 / 6`** | `NOT_MET` at $n=6$ (`p = 0.163`) | **`93.75%`** (`135/144`) |
| **`Replay 35^3`** (`63000..63005`, $K=24$) | `6` | **`2,583.6`** | `2,859.4` | **`1.11x`** | **`9.65%`** *(E2E: `9.10%`)* | `0.0924` (`0.15625`) | `5 / 6` | `NOT_MET` (`p = 0.950`) | **`99.31%`** (`143/144`) |
| **`Continual 47^3` Marginal** (`5` updates $\times 6$ tasks, rebuild charged) | `6` | **`11,152.1`** | `13,357.8` | **`1.20x`** | **`16.51%`** *(Lifecycle: `15.87%`, `6/6`, $p=0.0071$)* | **`0.0282`** (`0.0625`) | `5 / 6` | `NOT_MET` (`p = 0.728`) | **`92.13%`** (`retains 2,013.7 nodes`) |

- **Three-Arm `47^3` Cache Causal Ablation (`workers = 1`, `2x 3x3` Latin Square)**: `CacheOn_Persistent` (`7,944.1 ms`, `5,950.3` operational RHS/map) saves **`34.85%` (`1.54x`, $p = 3.10\times 10^{-4}$)** and **`57.34%` operational LU RHS** over `CacheL0Only` (`12,194.3 ms`, `13,949.3` RHS/map), and **`46.61%` (`1.87x`, $p = 2.37\times 10^{-5}$)** over `QueryCold` (`14,879.3 ms`, `16,295.3` RHS/map).
- **Vs. Global `SingleLU_GoalCapacitance` (`1`-worker exact timing)**: **`1.92x`** on `35^3` (`2.58s vs 4.97s`), **`2.72x`** on untouched `Confirm 47^3` (`7.10s vs 19.29s`, `543.7 MB vs 735.0 MB`), and **`2.71x`** on `59^3` (`26.57s vs 72.04s`, `1,539.2 MB vs 2,135.2 MB`).
- **Zero-Slack Verification**: **`2,304 / 2,304`** task events and **`792 / 792`** exact deployed-policy evaluations satisfy $L \le V^* \le J^{\hat{\mu}} \le U$ at **`0.0` slack** (`PoU-QT` max regret `0.02856` vs. $\varepsilon_{\mathrm{tol}} = 0.25$; `4/4` negative-control fault injections rejected).

---

## 3. Canonical Reproducible Entrypoints

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 1. Fast M2.3.3 Contract, PoU Conservation, & Zero-Slack Smoke Suite (~12s)
/usr/bin/python3 -B -W error -u quotient_phase2/m233_sisc_subportal_quadtree.py --self-test

# 2. Zero-Rerun Verification of All 10 Frozen M2.0..M2.3.2 Archives (~11s)
/usr/bin/python3 -B -W error -u quotient_phase2/verify_m232_release.py

# 3. Regenerate Figure 1 (Mechanism & Counterexamples)
/usr/bin/python3 -B -W error -u quotient_phase2/generate_manuscript_mechanism_figure.py

# 4. Full 1-Worker SISC Campaign (Replay 63k + Untouched n=12 Confirm 64k, ~30 min)
/usr/bin/python3 -B -u quotient_phase2/m233_sisc_subportal_quadtree.py
```
