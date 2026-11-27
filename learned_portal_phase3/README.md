# Phase-III (`learned_portal_phase3`): PAC-Certified Spectral-Portal Quotient Learning (SPQL)

This isolated package implements the **NeurIPS / ICLR theoretical & algorithmic leap** beyond known-operator axis-aligned multiscale solvers: learning decision-sufficient bottleneck quotient Green operators **end-to-end from unknown-dynamics exploration trajectories** without spatial coordinates or occupancy-grid priors, backed by **non-asymptotic multi-goal PAC regret certificates**.

> **Strict Non-Destructive Isolation**: Both frozen Phase-I (`green_response/`, SHA-256 `271ac8df...`) and frozen Phase-II SISC (`quotient_phase2/`, SHA-256 `3dcf3834...`) remain **100% byte-for-byte untouched** (`verified automatically in Gate P3-C10`).

---

## Core Modules & Artifacts

| File | Description |
| :--- | :--- |
| `__init__.py` | SHA-256 byte-freeze guard (`verify_phase1_and_phase2_untouched`) and Phase-III package manifest generator. |
| `spql_core.py` | Dual Clopper–Pearson M-matrix confidence envelopes $(\underline{A}_n, \overline{A}_n)$, zero-prior spectral Fiedler separator discovery, nested binary Fiedler Partition-of-Unity (`50%` LU-conserving) portal trees, epistemic-aware stopping, and Martingale-unbiased portal-directed active exploration (`Algorithm 2`). |
| `baselines_and_contracts.py` | Competing multi-goal RL/representation baselines (`PlugIn_CE_FullGraph`, `LowRank_SR_LinearRL`, `Scalar_EigenOptions`, `Uncompressed_SpectralSchur_PAC`, `ModelFree_GoalSoftQ`) and the 10-gate deterministic mathematical & counterexample suite (`P3-C01..P3-C10`). |
| `continuous_manifold_spql.py` | Continuous-state $35^\circ$-rotated stochastic diffusion control (`dX_t = (b(X_t)+u_t)dt + \sigma dW_t`), online farthest-point Voronoi landmark quotienting, and HJB off-diagonal exit-direction continuous feedback synthesis. |
| `run_phase3_neurips_suite.py` | Single-threaded (`OMP/BLAS/MKL = 1`, `workers = 1`) end-to-end runner executing all 10 gates, Experiments 1–3 (`n = 8` seeds each), 300-DPI figures, and strict RFC-8259 JSON provenance. |
| `p3_neurips_benchmark_results.json` | Complete multi-seed empirical metrics, `95%` confidence intervals, paired Wilcoxon $p$-values, and SHA-256 provenance manifest. |
| `p3_fig1_architecture_and_counterexamples.png` | 4-panel figure: zero-prior $37^\circ$-rotated spectral portal discovery, monotone `L0 -> L4` Fiedler-tree tightening, structural counterexamples, and finite-sample optimism vs. PAC validity. |
| `p3_fig2_sample_complexity_3d_and_continuous.png` | 4-panel figure: $37^\circ$-rotated multi-goal sample complexity, PAC width contraction & epistemic stopping, $15{,}700$-state 3D curved caves, and continuous $35^\circ$-rotated SDE control. |
| `NEURIPS_MANUSCRIPT_DRAFT.md` | Full NeurIPS / ICLR paper draft including Propositions 1–3, Theorems 1–3, Algorithms 1–2, empirical tables, limitations, and complete mathematical proofs in Appendix A. |
| `REPORT_PHASE3_SPQL_NEURIPS_LEAP.md` | Comprehensive Chinese technical & empirical report summarizing the Phase-III NeurIPS/ICLR leap, 10-gate verification, and 3-domain benchmark results. |

---

## Reproducible Single-Threaded Execution Commands

1. **Fast 10-Gate Mathematical & Counterexample Audit (`~2.5s`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     /usr/bin/python3 -B -W error -c "import json; from learned_portal_phase3.baselines_and_contracts import run_phase3_10_contract_gates; print(json.dumps(run_phase3_10_contract_gates(), indent=2))"
   ```

2. **Full Multi-Seed NeurIPS Benchmark & Figure Generation (`workers = 1`, `~6.5 min`)**:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
     /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_neurips_suite
   ```

3. **Fast Figure Re-Render from Verified JSON (`~2s`)**:
   ```bash
   /usr/bin/python3 -B -W error -m learned_portal_phase3.run_phase3_neurips_suite --replot-from-json
   ```

---

## Headline Empirical Summary

- **10/10 Deterministic Contract Gates Passed (`P3-C01..P3-C10`)**: Exact `50.0%` binary PoU LU-backsolve conservation (`1.39e-17` max discrepancy), strictly positive hidden-wormhole PAC lower bound (`0.114 <= 2.983 <= 21.062 <= 39.637`), `0` cross-room leaks on $37^\circ$-rotated buildings (where axis-aligned slicing leaves `90.57%` unseparated), and verified Phase-I/II byte-freeze integrity.
- **Zero-Violation True-MDP Multi-Goal PAC Coverage**: **`1,472 / 1,472` (`100.0%`, `0` violations)** across unseen 2D and 3D goals, vs. **`94.5%` (2D)** and **`100.0%` (3D)** optimism violations for `PlugIn_CE_FullGraph`.
- **Unbiased Active Bottleneck Exploration (`Exp 1`)**: Statistically significant improvement over passive exploration on both closed-loop regret and PAC width across `70k–300k` steps (**paired Wilcoxon $p = 0.0078125$, `8/8` seeds improved**), while crushing `LowRank_SR` (`78.92`), `ModelFree_GoalSoftQ` (`60.31`), and `Scalar_EigenOptions` (`56.32`) down to **`6.23`** regret at `300k`.
- **3D Unstructured Curved Caves (`Exp 2`, `~15,700` states)**: Activates only **`9.96%`** of portal DOFs, reducing 3D room-LU backsolves by **`63.2%`** and resident memory by **`29.8%`** (`56.77 MB` vs. `80.87 MB`) relative to uncompressed PAC Schur complements.
- **Continuous $35^\circ$-Rotated SDE Control (`Exp 3`, `7,680` rollouts/method)**: Achieves **`100.0%` goal success** on all `8/8` seeds and lowest control cost (**`1.436`** vs. `2.157` Soft-Q, `4.706` Scalar Options, `9.170` RBF Linear-RL; **$p = 0.0078125$** against every baseline).
