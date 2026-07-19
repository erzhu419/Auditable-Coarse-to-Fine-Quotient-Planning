# Laplace Semi-MDP

This repository is an experimental artifact for a rate-distortion graph abstraction of finite semi-MDP planning. The core idea is not to discover options for their own sake: it is to compress noncritical state regions into first-boundary edges while keeping the MDP/SMDP planning distortion auditable.

## Main Claim

The current paper-facing path is:

1. **Reference objective:** exact first-hit Green kernels define the frozen RD insertion score. Exact and iterative search are teachers/oracles, not the intended runtime path.
2. **One-shot operator:** from mandatory boundary `B0`, build one truncated sparse Green response, apply the multichannel score once to every state, threshold/local-max once, and build final graph kernels once. There is no candidate insertion, beam search, or score recomputation.
3. **Audit and fallback:** the returned graph is evaluated under value and grouped topology/value/stochastic constraints. A failed audit may invoke certified adaptive/group-constrained refinement; that fallback is reported separately and is not charged to one-shot operator timing.
4. **Planner:** retained states become graph vertices, first-boundary options become graph-SMDP actions, and planning runs on the compressed graph.
5. **Certificates:** Green-tail bounds induce one-shot channel intervals; score margins certify stable threshold/local-max decisions. Bellman contraction and the four-term end-to-end theorem certify the returned graph, but do not claim that heuristic thresholding globally optimizes the RD set objective.

The most useful entry-point table is generated at:

```text
experiments/output/submission_main_table/summary.md
```

It aligns the large-scale certified adaptive result, compact baselines, exhaustive-oracle solver validity, and certificate appendices into one submission-facing report.

## Repository Map

- `experiments/`: executable benchmark and diagnostic scripts.
- `experiments/output/`: checked-in CSV/JSON/Markdown experiment artifacts.
- `experiments/finite_mdp_adapter.py`: generic finite known-model MDP interface for non-grid smoke tests.
- `proof/`: Lean 4 proof layer for the frozen RD operator, Green/Neumann certificates, Bellman contraction/value-gap statements, top-set fallback, and bits-curvature bounds.
- `paper/`: paper-facing claim, terminology, related-work, theorem, experiment, figure, and reviewer-risk planning docs.
- `scripts/check_paper_consistency.py`: citation, figure, cross-reference, title, and registered numeric-claim gate for the manuscript.
- `markdown/`: working research notes and GPT critique/advice logs.
- `reference/`: ignored local papers and cloned repositories.

## Quick Start

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

For exact artifact versions, use `requirements-lock.txt`; optional external
environment versions are pinned in `requirements-general-envs-lock.txt`.

Optional general-environment adapters for MiniGrid and Gymnasium-Robotics:

```bash
python3 -m pip install -r requirements-general-envs.txt
```

Run the proof layer:

```bash
bash scripts/reproduce_proofs.sh
```

Rebuild the certificate artifacts:

```bash
bash scripts/reproduce_certificates.sh
```

Rebuild the core paper-facing experiments:

```bash
bash scripts/reproduce_core.sh
```

Regenerate the final constrained tables, theorem bridge, evidence figures, and
LaTeX manuscript from tracked experiment artifacts:

```bash
bash scripts/reproduce_submission_artifact.sh
```

Run only the paper consistency gate, which verifies citation keys, figure
paths, LaTeX labels, the `CITATION.cff` title, and registered numeric claims:

```bash
python3 scripts/check_paper_consistency.py
```

Run the finite-MDP general-environment smoke benchmark:

```bash
python3 experiments/run_general_env_benchmark.py
```

Run the no-recompute operator benchmark. The first command evaluates the final
graph once; the second isolates operator extraction from final-kernel cost:

```bash
python3 experiments/run_one_shot_rd_operator.py \
  --map-specs corridor:32 open_room:10 four_rooms:11 maze:13 \
  --slips 0 0.05 0.1 --thresholds 0.15 \
  --baselines endpoints graph_rd_surrogate_joint graph_rd_joint

python3 experiments/run_one_shot_rd_operator.py \
  --map-specs corridor:256 open_room:32 four_rooms:31 maze:31 \
  --slips 0 0.05 0.1 --thresholds 0.15 --operator-only

# Test whether K can be predicted from one graph-level observation. The
# frontier certificate remains authoritative after the prediction.
python3 experiments/run_learned_green_horizon.py
```

This benchmark currently covers Gymnasium ToyText (`Taxi-v4`,
`FrozenLake8x8-v1`, `CliffWalking-v1`) plus a discretized sampled PointMaze,
and symbolic MiniGrid FourRooms, DoorKey, and MultiRoom tasks. It compares
primitive first-boundary options with boundary-targeted options over five seeds.
PointMaze rows are claims about the discretized empirical MDP, not exact
continuous-control theorems. Taxi is a structured negative case: the spatial
boundary graph compresses task variables that must remain explicit.

By default, experiment scripts cap BLAS/OpenMP to one CPU thread so local WSL
runs do not monopolize all cores. These experiments are NumPy/OpenBLAS linear
algebra jobs, not CUDA/GPU training. On CPU nodes, override the cap explicitly,
for example:

```bash
LAPLACE_NUM_THREADS=64 bash scripts/reproduce_core.sh
```

To choose a thread count on a CPU node, run:

```bash
python3 experiments/run_linear_solver_thread_scaling.py --threads 1 2 4 8 16 32 64
```

For large CPU-node paper runs, use the existing scheduler wrapper. First stage
the repo through the configured jump host to the shared scheduler workdir:

```bash
bash scripts/stage_laplace_scheduler.sh
```

Then submit scheduler tasks pinned to `node001`-`node006`; result directories
are synced back under `experiments/output/scheduler_large_runs/`:

```bash
python3 scripts/submit_laplace_scheduler.py --profile large --dispatch
```

The scheduler wrapper defaults to full-node BLAS/OpenMP threading
(`--threads 192`) while reserving a slightly lower scheduler CPU estimate
(`--cpu 128`) so transient load-average accounting does not keep otherwise
idle `node001`-`node006` jobs queued. The `--threads` value is exported as
`LAPLACE_NUM_THREADS`, `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS`. Large/xl amortized runs are split
into map/method shards by default (`--amortized-shards 32`) and use smaller
per-shard reservations (`--amortized-threads 16`, `--amortized-cpu 16`) because
that workload did not saturate a whole 192-core node. Each shard writes
application-level checkpoints (`progress.jsonl` plus an incrementally refreshed
CSV/summary) after every map/method job; `--scheduler-ckpt-dir` can also declare
those dirs to scheduler, but it is slower because submit scans remote paths.
The paper-grade suites can be submitted separately as scheduler shards:
`random_maze`, `large_scale`, `amortized`, `edge_reward`, and
`option_frontier`.  The XL profile defaults to multi-slip random/topology
stress tests, scaled compression maps, fixed-`B` edge reward relabeling, and a
matched option-baseline frontier.  To aggregate finished shard outputs:

```bash
python3 experiments/aggregate_scheduler_shards.py \
  --run-root experiments/output/scheduler_large_runs/<run_id> \
  --publish
```

For a cheap scheduler preflight:

```bash
python3 scripts/submit_laplace_scheduler.py --profile smoke --suites full --nodes node001 --dispatch
```

The underlying node runner is `scripts/run_node_large_paper.sh`; it runs
random-maze robustness, large-scale compression, multi-task amortization, thread
scaling, and a node summary under `experiments/output/scheduler_large_runs/`.

Reviewer-P0 audits use a separate wrapper so the main scheduler configuration
does not need to be edited. It submits strong full-state planners, direct state
abstraction/Schur baselines, complete-universe tiny oracles, multi-seed external
environments, the four-term value-gap decomposition, and failed-maze budget
recovery as fine-grained CPU shards:

```bash
python3 scripts/submit_p0_audits_scheduler.py \
  --run-id reviewer_p0_<date> --suites all --dispatch

python3 experiments/aggregate_p0_audit_shards.py \
  --run-root experiments/output/scheduler_p0_audits/reviewer_p0_<date>
```

The same wrapper exposes `one_shot_random` and `one_shot_xl` suites. Their
sharded CSVs are merged with `experiments/aggregate_one_shot_rd_operator.py`.

The P0 submitter creates one immutable, node-specific source snapshot before
dispatch. Each shard writes `_SUCCESS.json` only after a zero-exit run, and the
aggregator refuses incomplete or mixed-fingerprint runs. This prevents stale
launch-stage caches or nominal scheduler `done` states from entering paper tables.

## Current Artifact Status

- The explicit no-recompute backend is now implemented separately from search. On the 12-case classic table, threshold `0.15` uses two endpoint probes, zero candidate-insertion evaluations, and one final kernel build. Its median selection speedup is about `40.1x` versus iterative surrogate search and `157x` versus exact RD search; including the single final-kernel build, the paired median speedups are about `7.77x` and `22.9x`. On a paired 20-context held-out random-maze subset, boundary Jaccard is `0.920`, selection is `369.5x` faster, and the complete graph pipeline is `12.94x` faster than iterative surrogate search. The global classic maximum normalized value gap remains `0.00963`, although the one-shot graph is typically slightly denser.
- The one-shot path is not presented as a universal group-feasibility solver. The cheap one-shot transform fails all three hard group rows. A stricter frozen finite-difference order reaches feasibility only at `k=2` for open room and at tested prefixes `k=3..10` for four rooms, then loses it as the prefix grows; maze has no feasible prefix through `k=24`. This confirms that adaptive option-library drift cannot be certified by a frozen local transform alone, so group-constrained refinement remains an explicit fallback.
- A trainable-`K` pilot fits a graph-conditioned ridge proposal on 105 contexts, calibrates on 15, and tests on 60 larger/held-out contexts. It reaches a `93.3%` first-pass certificate rate and `100%` after fallback, with exact boundary agreement on this suite. It is nevertheless slower than both fixed-`K` (`0.906x`) and the current adaptive frontier stopping (`0.747x`) once graph-feature extraction and retries are charged. Thus learned `K` is retained as a batching/scheduling ablation, not claimed as the single-graph acceleration mechanism.
- A transition-graph GNN tests the stronger "look once and emit the boundary" idea on 360 corridor/open-room/four-room/DFS-maze/braided-maze reference contexts. Its boundary-only proposal passes the strict joint constraint on `68/90` scale holdouts. One predefined constraint-aware fixed-family follow-up raises raw proposal quality to `81/90`, against a candidate-family oracle of `85/90` and an adaptive RD reference proposal of `71/90`, at `656.0x` selection speed. These are different objectives: the paired outcomes are 64 both-pass, 17 reranker-only, 7 reference-only, and 2 both-fail (`p=0.0639`, exact McNemar), so the comparison is descriptive rather than a learned-superiority claim. Validation routing still misses `6/9` failures, and full audit reduces the reranker pipeline to `0.428x`; the learned branch is therefore a documented uncertified ablation and the constraint-aware topology extension was stopped under the predefined go/no-go protocol.
- Certified adaptive Green plus tie-aware epsilon/top-set certificates reaches final certified decisions on the current certification suite.
- Adaptive feasible top-k diagnostics now support using it as the main discovery backend: paired adaptive/fixed top-4 rows match feasibility on the current suite (`36/36`), certified feasible rate stays at `0.7222`, median selection time drops from about `47.18s` to `23.58s`, and the Lean proof layer states the feasible-envelope/work-bound guarantee plus the score-optimality caveat.
- The XL scheduler run `paper_xl_20260706_0659` has been published into the tracked paper-facing outputs: large-scale compression 135 rows, random maze 360 rows, option frontier 648 rows, amortized multitask 192 rows, and fixed-`B` edge reward 384 rows.
- The generic finite-MDP adapter now has 315 raw rows and 56 aggregate rows across seven external environments and five seeds. FrozenLake is a positive portability case; MiniGrid and PointMaze expose option-family bias; Taxi-v4 is a high-compression, high-gap, group-infeasible negative case.
- The matched strong-planner audit contains 405 paired timing rows. Sparse-vectorized VI is fastest in all 27 map/slip cases. The RD selector's median graph-planning speedup is about `29.6x`, but its median single-task total speedup is only `0.00116x`; the paper therefore claims planning/representation compression, not a single-task wall-time win.
- The compact benchmark compares full VI, exact RD graph variants, group-constrained RD, eigenoptions, betweenness bottlenecks, random landmarks, and coverage landmarks under the same map/slip suite.
- Solver-validity diagnostics compare operator-only and exact-refined beam search against small exhaustive oracles.
- The complete-universe oracle suite covers 315 contexts: exact-refine beam widths 4 and 8 match the exhaustive boundary and feasibility decision in every context; operator beam 8 matches feasibility in every context and the exact boundary in about `84.8%`.
- The larger group-constrained adaptive table evaluates `open_room_12`, `four_rooms_11`, and `maze_13` at slip `0` and `0.05`; group-constrained boundaries are feasible on the current suite, while endpoint-only boundaries are not.
- Discovery profiling is now separated from planning: `experiments/output/discovery_profile_cache/summary.md` decomposes probe construction, Green kernels, vectorized frozen scoring, full candidate recompute, and cache-hit reuse.
- Incremental Green diagnostics now check parent-to-child boundary insertion, and `group_constrained_incremental` wires the score-level update into beam selection as an ablation. The semantic diff identified the open-room issue as edge-uniform versus occupancy-weighted accounting; the insertion backend now honors and caches the production active-edge weights and is feasible on the larger group suite.
- Weighted spectral certificates are reported as sufficient appendix certificates; conditioned/rational audits expose the conditioning-vs-tightness tradeoff.
- Fixed-boundary multi-task relabeling is now separated from graph topology:
  `experiments/output/edge_reward_kernel_multitask/summary.md` compares full VI
  against exact edge discounted-occupancy reward kernels and query-time
  first-hit event kernels. Additive reward relabeling preserves compression;
  terminal-goal event kernels keep `B` fixed but expose the remaining
  option/boundary restriction gap. The goal-conditioned event-option extension
  keeps `B` fixed and reduces terminal-goal gaps using one shared policy and
  one batched event solve per queried goal, while reporting the extra
  goal-interface cost and break-even task count separately. The historical
  `108.4x` best amortized number uses the legacy dense NumPy VI denominator;
  normalized gaps and the denominator label are included so it is not confused
  with the matched sparse-VI audit.
- Paper-facing scaffolding now lives under `paper/`, including the main claim, method/results narrative scaffold, related-work matrix, theorem stack, experiment matrix, and figure plan.
- `experiments/run_random_maze_generalization.py`, `experiments/run_fair_budget_frontier.py`, `experiments/plot_graph_abstraction_figures.py`, and `experiments/run_theorem_experiment_bridge.py` add random-topology stress tests, shared budget-frontier aggregation, interpretability figures, and theorem/proof/experiment alignment.

Use `experiments/output/submission_main_table/summary.md` as the first reviewer-facing artifact rather than reading every historical output directory.
