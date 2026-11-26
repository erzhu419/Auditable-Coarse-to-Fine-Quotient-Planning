"""Canonical Modular Package for Auditable Coarse-to-Fine Green Response Planning (`green_response`).

Consolidates all verified components into one authoritative library (superseding historical
`green_kriging_mvp..v4` snapshots, which remain frozen for reproducibility):
  - `core`: Problem specifications, capability guards, reflection mechanics, Same-GP Kriging,
    closed-loop CRN simulator (with exact `t=0` absorption), and scale-equivariant paired statistics.
  - `port_solvers`: 2D/3D Schur-Port response planner with unified nested `L1 -> L4 -> L8 -> EXACT`
    partition trees, corrected single-query value-bound log shifts, zero silent interval clamping,
    reuse-aware classical/ring baselines, exact anisotropic KKT policy readout, and exact continuous-disk
    robust HJB.
  - `macro_planning`: Exact ball-stopping multi-waypoint tour envelopes, cross-round interval
    branch-and-bound pruning (`m = 5..8`), and genuine `O(m^2 2^m)` subset-state adaptive macro-Bellman
    planning (`m = 5..10`).
  - `highd_solvers`: `C^2` even-collar Helmholtz/Bessel physics-mean GP distillation (with scalar `R = r I`
    support and explicit domain guards), Eikonal/geometric mean-prior controls, and scoped 4D kinetic
    telescoping extensions with independent path-vs-endpoint jump verification.
"""

from .core import (
    GoalBall,
    GroundTruthWorld,
    HazardFeature,
    IntervalCertificate,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    collect_runtime_metadata,
    compute_source_manifest,
    enforce_single_thread_env,
    eval_goal_union,
    eval_hazard_features,
    generate_benchmark_map,
    holm_bonferroni_adjust,
    observe_world_at_points,
    paired_relative_noninferiority,
    paired_stats,
    reflect_into_box,
    reflect_kinetic_into_box,
    run_map_parallel,
    sample_noisy_probes,
    simulate_closed_loop_crn,
)
from .highd_solvers import (
    BoxNeumannBesselBaseGuide,
    EikonalConeMeanGuide,
    MirrorNeumannMatern52GP,
    build_kinetic_lqr_base_guide,
    fit_gp_value_with_prior,
    make_antithetic_centered_pimc_policy,
    solve_highd_fk_distillation,
    solve_kinetic_underactuated_greenres,
)
from .macro_planning import (
    MacroTourPlanner,
    independent_exact_ball_operators,
    independent_exact_ball_tour_scores,
    independent_exact_macro_bellman_reference,
)
from .port_solvers import (
    ClassicalFDSolver,
    SchurPortPlanner,
    build_grid_points,
    build_upwind_mmatrix_desirability_operator,
    compute_discrete_fixed_policy_residual_2d,
    compute_monotone_anisotropic_bellman_residual,
    make_consistent_value_and_policy_2d3d,
    solve_anisotropic_constrained_kkt_action,
    solve_exact_continuous_ball_robust_hjb_2d,
    solve_monotone_anisotropic_constrained_hjb_2d,
)

__all__ = [
    "BoxNeumannBesselBaseGuide",
    "ClassicalFDSolver",
    "EikonalConeMeanGuide",
    "GoalBall",
    "GroundTruthWorld",
    "HazardFeature",
    "IntervalCertificate",
    "KrigingWorldModel",
    "MacroTourPlanner",
    "MirrorNeumannMatern52GP",
    "ProblemSpec",
    "QueryTask",
    "SchurPortPlanner",
    "build_grid_points",
    "build_kinetic_lqr_base_guide",
    "build_upwind_mmatrix_desirability_operator",
    "collect_runtime_metadata",
    "compute_discrete_fixed_policy_residual_2d",
    "compute_monotone_anisotropic_bellman_residual",
    "enforce_single_thread_env",
    "eval_goal_union",
    "eval_hazard_features",
    "fit_gp_value_with_prior",
    "generate_benchmark_map",
    "independent_exact_ball_operators",
    "independent_exact_ball_tour_scores",
    "independent_exact_macro_bellman_reference",
    "make_antithetic_centered_pimc_policy",
    "make_consistent_value_and_policy_2d3d",
    "paired_relative_noninferiority",
    "paired_stats",
    "reflect_into_box",
    "reflect_kinetic_into_box",
    "sample_noisy_probes",
    "simulate_closed_loop_crn",
    "solve_anisotropic_constrained_kkt_action",
    "solve_exact_continuous_ball_robust_hjb_2d",
    "solve_highd_fk_distillation",
    "solve_kinetic_underactuated_greenres",
    "solve_monotone_anisotropic_constrained_hjb_2d",
]
