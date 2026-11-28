# Phase II · Adaptive sub-portal planning in 3D discrete LMDPs

The Phase-II manuscript studies repeated queries in axis-aligned multi-room grids. The method reuses room factorizations, refines individual doorway blocks and shares a Lyapunov witness across nested cuts. Both the candidate and its closest comparator, matrix-free exact Schur Krylov, prime a deployable policy and use the same room factorizations and target capacitance. [Manuscript](MANUSCRIPT_CORE_DRAFT.md) · [Claim–evidence map](PAPER_CLAIM_EVIDENCE_BLUEPRINT.md)

## Static and continual benchmarks

All primary timings below come from the single-worker campaign with planner references released after every arm. Each static map received 24 queries. The paired observation is a map. Savings use the ratio of mean times. The last column tests the predeclared 20% engineering threshold with a one-sided paired t-test. [Clean campaign records](m233_clean_isolation_replication.json) · [Figure 2](m233_clean_isolation_summary.png)

| Block | Maps faster | PoU / matrix-free mean (s) | Planner saving | Two-sided paired t / exact sign-flip p | 20% threshold p |
| --- | ---: | ---: | ---: | ---: | ---: |
| Confirmation 47³ | 11/12 | 7.316 / 10.275 | **28.80%** | 0.0000424 / 0.000977 | **0.0292** |
| Replay 35³ | 5/6 | 2.771 / 3.123 | 11.28% | 0.0459 / 0.0625 | 0.936 |
| Replay 47³ | 6/6 | 8.478 / 11.381 | 25.51% | 0.00152 / 0.03125 | 0.145 |
| Replay 59³ | 6/6 | 25.645 / 33.915 | 24.38% | 0.000351 / 0.03125 | 0.128 |
| Continual 47³, post-initialization including updates | 4/6 | 10.706 / 11.815 | 9.39% | 0.157 / 0.15625 | 0.943 |
| Continual 47³, full lifecycle | 5/6 | 13.433 / 14.826 | 9.39% | 0.0649 / 0.09375 | 0.980 |

Hyperparameters were locked on development seeds 61000–61005. Replay uses 63000–63005. The clean campaign re-evaluates confirmation seeds 64000–64011 from the initial locked run. Including the shared GP fit and operator assembly, the confirmation saving is 28.03% (20% threshold p = 0.0366). [Primary records](m233_clean_isolation_replication.json)

The three-arm 47³ cache ablation gives 34.15% less planner time and 57.34% fewer operational room-LU right-hand sides with persistent responses than with only L0 retained. Each static block has one timed global SingleLU reference in the clean run. §5.4 gives those four matched observations. Process RSS and the selected factor/cache array bytes have separate scopes. [Manuscript](MANUSCRIPT_CORE_DRAFT.md)

The verification ledger covers 2,304 method-tagged events, 900 distinct geometric tasks and 792 scheduled deployed-policy evaluations. All saved reference-value and policy inequalities hold at zero comparison slack. The runtime checks operate on the declared float64 discrete model. [Verification records](m233_clean_isolation_replication.json)

## Reproduce or audit

Run these commands from the repository root with Python, NumPy, SciPy and Matplotlib installed. The `check` command verifies the published clean archive digest, both source manifests, the independent event roster and the shared cache/pair task identities. It also prints the matched SingleLU timings. The contracts command executes the PoU and planner-lifetime probes.

```bash
python3 -B quotient_phase2/reproduce/run.py check
python3 -B -W error quotient_phase2/m233_sisc_subportal_quadtree.py --contracts-only
```

Each of the following commands requires a new destination directory. The wrapper copies the frozen drivers and input records there. The full replication retimes the same maps and writes its own JSON and figure in the destination's `quotient_phase2/` directory. Timings depend on the machine. The M2.3.2 verification recomputes its numerical checks and report from the frozen M2.3.2 records.

```bash
python3 -B quotient_phase2/reproduce/run.py replicate .tmp/sisc-clean-replication
python3 -B quotient_phase2/reproduce/run.py verify-m232 .tmp/sisc-m232-verification
```

## Provenance

| Artifact | SHA-256 prefix | Role |
| --- | --- | --- |
| [Phase-I package](../green_response/) | `271ac8df` | Frozen Python source aggregate |
| [Phase-II source manifest](m233_clean_isolation_replication.json) | `e6ea565b` | Frozen top-level Python modules |
| [M2.3.2 archive](m232_targeted_replay_results.json) · [Release report](m232_release_verification_report.json) | `9979d61a` · `0786ce5e` | Uniform whole-portal baseline and verification |
| [Initial M2.3.3 archive](m233_sisc_unlock_results.json) | `339e723f` | Initial timings with cross-arm planner retention, historical record |
| [Clean M2.3.3 archive](m233_clean_isolation_replication.json) | `73101638` | Primary paired timings and method events |
| [Mechanism figure](m233_fig1_mechanism_and_counterexamples.png) · [Clean timing figure](m233_clean_isolation_summary.png) | | Figures 1 and 2 of the Phase-II manuscript |
