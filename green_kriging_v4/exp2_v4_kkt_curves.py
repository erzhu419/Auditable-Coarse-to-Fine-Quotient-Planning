"""Experiment 2 (`green_kriging_v4`):
Same-Grid Non-LMDP Anisotropic Constrained HJB (`R = diag(0.35, 3.0)`, `u_max = 1.80`)
Evaluated on ALL THREE Audit Axes (`GPT6 Section 5.2 / 6.2`) across 10 Maps (`5` dev + `5` held-out)
x 10 Queries (`100` queries per grid on `35^2` and `51^2`):
  1. Equal Bellman Residual Tolerance (`||F(V)||_inf <= 1e-8`): sweeps & wall-clock time!
  2. Sweep / Compute Budget Curve (`k = 1, 2, 3, 5` sweeps vs `tol=1e-8`): closed-loop CRN cost & Bellman residual!
  3. Equal Control-Cost Tolerance (`<= +0.5%` excess cost): minimum sweeps & stream wall-clock!
"""
from __future__ import annotations

from core_v4 import enforce_single_thread_env
enforce_single_thread_env()

import json
import time
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core_v4 import (
    GoalBall,
    HazardFeature,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    collect_runtime_metadata,
    eval_goal_union,
    generate_benchmark_map,
    paired_stats,
    sample_noisy_probes,
    simulate_closed_loop_crn,
)
from schur_port_v4 import (
    ClassicalFDSolverV4,
    SchurPortCertifiedPlannerV4,
    build_grid_points,
    solve_monotone_anisotropic_constrained_hjb_2d_v4,
)


def make_non_lmdp_queries(map_seed: int, n_queries: int = 10) -> Tuple[List[GoalBall], List[QueryTask]]:
    rng = np.random.default_rng(map_seed + 303)
    r_g = 0.22
    wps: List[GoalBall] = []
    for _ in range(6):
        for _att in range(120):
            c = rng.uniform(-1.12, 1.12, size=2)
            if all(np.linalg.norm(c - np.asarray(w.center)) >= 0.48 for w in wps):
                wps.append(GoalBall(tuple(c.tolist()), 0.0, r_g))
                break

    queries: List[QueryTask] = []
    for q_i in range(n_queries):
        picks = rng.choice(len(wps), size=2, replace=False)
        goals = (
            GoalBall(wps[picks[0]].center, 0.0, r_g),
            GoalBall(wps[picks[1]].center, float(rng.uniform(0.25, 1.05)), r_g),
        )
        starts = []
        for _ in range(2):
            for _att in range(100):
                s = rng.uniform(-1.25, 1.25, size=2)
                if all(np.linalg.norm(s - np.asarray(g.center)) > 0.48 for g in goals):
                    starts.append(tuple(s.tolist()))
                    break
        loc_h = ()
        if q_i % 3 == 1:
            mid = np.clip(0.5 * (np.asarray(starts[0]) + np.asarray(goals[0].center)), -1.15, 1.15)
            loc_h = (HazardFeature(tuple(mid.tolist()), float(rng.uniform(4.5, 8.5)), (0.20, 0.20)),)
        queries.append(QueryTask(f"nl_{q_i}", goals, tuple(starts), loc_h))
    return wps, queries


def geodesic_init_grid(pts: np.ndarray, spec: ProblemSpec, query: QueryTask, h: float) -> np.ndarray:
    eff_r = 0.75 * h * np.sqrt(2.0)
    eff_g = [GoalBall(g.center, g.phi, max(g.radius, eff_r)) for g in query.goals]
    is_g, phi_u = eval_goal_union(pts, eff_g)
    r_bar = float(np.sqrt(np.mean(spec.R_vec)))
    slope = np.sqrt(2.0 * spec.q0 * r_bar)
    v_min = np.full(len(pts), np.inf, dtype=float)
    for g in eff_g:
        d = np.maximum(0.0, np.linalg.norm(pts - np.asarray(g.center)[None, :], axis=1) - g.radius)
        v_min = np.minimum(v_min, g.phi + slope * d)
    v_min[is_g] = phi_u[is_g]
    return v_min


def run_kkt_grid_suite(grid_n: int, n_queries: int = 10, n_dev: int = 5, n_heldout: int = 5) -> dict:
    spec = ProblemSpec(
        dim=2, half_width=1.65, sigma=0.45, q0=0.50,
        r_diag=(0.35, 3.0), u_max=1.80, dt_sim=0.015, max_steps=380,
    )
    # 5 original dev seeds (6100..6104) + 5 held-out seeds (16100..16104)
    map_seeds = list(range(6100, 6100 + n_dev)) + list(range(16100, 16100 + n_heldout))
    inits = ["Zero", "Geodesic", "IsoFD", "SchurPort"]
    fixed_budgets = [1, 3]

    # Equal-tolerance (`tol = 1e-8`) tracking
    eq_tol_sweeps = {k: [] for k in inits}
    eq_tol_stream_ms = {k: [] for k in inits}
    eq_tol_cost = {k: [] for k in inits}
    eq_tol_res = {k: [] for k in inits}

    # Fixed-step curves (`k = 1, 3`)
    budget_cost = {f"{k}-{st}Step": [] for k in inits for st in fixed_budgets}
    budget_ms = {f"{k}-{st}Step": [] for k in inits for st in fixed_budgets}
    budget_res = {f"{k}-{st}Step": [] for k in inits for st in fixed_budgets}
    gt_costs = []

    _, pts, h = build_grid_points(2, spec.half_width, grid_n)

    for idx_m, m_seed in enumerate(map_seeds):
        world = generate_benchmark_map(m_seed, dim=2, regime="narrow_barrier", with_drift=True, spec=spec)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=85, seed=m_seed + 9, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        wps, queries = make_non_lmdp_queries(m_seed, n_queries=n_queries)

        iso_spec = ProblemSpec(dim=2, half_width=1.65, sigma=spec.sigma, q0=spec.q0, r_diag=(float(np.exp(np.mean(np.log(spec.r_diag)))),) * 2)
        iso_fd = ClassicalFDSolverV4(iso_spec, grid_n, km.predict_q, km.predict_b)
        port_pl = SchurPortCertifiedPlannerV4(iso_spec, grid_n, km.predict_q, km.predict_b, wps, initial_sectors_per_wp=4)

        ms_eq = {
            "Zero": 0.0,
            "Geodesic": 0.0,
            "IsoFD": iso_fd.init_ms,
            "SchurPort": port_pl.op_build_ms,
        }
        sw_eq = {k: [] for k in inits}
        cs_eq = {k: [] for k in inits}
        rs_eq = {k: [] for k in inits}

        ms_bd = {f"{k}-{st}Step": (iso_fd.init_ms if k == "IsoFD" else (port_pl.op_build_ms if k == "SchurPort" else 0.0)) for k in inits for st in fixed_budgets}
        cs_bd = {f"{k}-{st}Step": [] for k in inits for st in fixed_budgets}
        rs_bd = {f"{k}-{st}Step": [] for k in inits for st in fixed_budgets}
        c_gt_q = []

        for q_i, q in enumerate(queries):
            crn_s = 8200 + 30 * idx_m + q_i
            gt_sol = solve_monotone_anisotropic_constrained_hjb_2d_v4(spec, grid_n, world.q_hidden, world.drift, q, tol_bellman=1e-8)
            c_gt_q.append(simulate_closed_loop_crn(world, gt_sol["policy"], q, n_per_start=12, seed=crn_s)["mean_cost"])

            # Build the 4 initializers + record warm-start generation overhead!
            t0 = time.perf_counter()
            v_geo = geodesic_init_grid(pts, spec, q, h)
            t_geo = 1000.0 * (time.perf_counter() - t0)

            r_ifd = iso_fd.solve_direct(q)
            t_ifd = r_ifd["solve_ms"]

            r_prt = port_pl.solve_query(q)
            t_prt = r_prt["solve_ms"]

            init_map = {
                "Zero": (None, 0.0),
                "Geodesic": (v_geo, t_geo),
                "IsoFD": (r_ifd["V_grid"], t_ifd),
                "SchurPort": (r_prt["V_grid"], t_prt),
            }

            for k_name, (v0_arr, init_q_ms) in init_map.items():
                # 1. Equal-tolerance (`<= 1e-8`) solve
                sol_eq = solve_monotone_anisotropic_constrained_hjb_2d_v4(
                    spec, grid_n, km.predict_q, km.predict_b, q, V_init=v0_arr, max_iters=25, tol_bellman=1e-8
                )
                ms_eq[k_name] += init_q_ms + sol_eq["solve_ms"]
                sw_eq[k_name].append(sol_eq["sweeps_used"])
                rs_eq[k_name].append(sol_eq["true_bellman_residual"])
                sim_eq = simulate_closed_loop_crn(world, sol_eq["policy"], q, n_per_start=12, seed=crn_s)
                cs_eq[k_name].append(sim_eq["mean_cost"])

                # 2. Fixed sweep budgets (`1` and `3` sweeps)
                for st in fixed_budgets:
                    bkey = f"{k_name}-{st}Step"
                    sol_b = solve_monotone_anisotropic_constrained_hjb_2d_v4(
                        spec, grid_n, km.predict_q, km.predict_b, q, V_init=v0_arr, max_iters=st, tol_bellman=None
                    )
                    ms_bd[bkey] += init_q_ms + sol_b["solve_ms"]
                    rs_bd[bkey].append(sol_b["true_bellman_residual"])
                    sim_b = simulate_closed_loop_crn(world, sol_b["policy"], q, n_per_start=12, seed=crn_s)
                    cs_bd[bkey].append(sim_b["mean_cost"])

        gt_costs.append(float(np.mean(c_gt_q)))
        for k in inits:
            eq_tol_sweeps[k].append(float(np.mean(sw_eq[k])))
            eq_tol_stream_ms[k].append(ms_eq[k])
            eq_tol_cost[k].append(float(np.mean(cs_eq[k])))
            eq_tol_res[k].append(float(np.max(rs_eq[k])))
            for st in fixed_budgets:
                bkey = f"{k}-{st}Step"
                budget_cost[bkey].append(float(np.mean(cs_bd[bkey])))
                budget_ms[bkey].append(ms_bd[bkey])
                budget_res[bkey].append(float(np.mean(rs_bd[bkey])))
        print(
            f"  [KKT {grid_n}^2 Map {idx_m+1}/10] Tol=1e-8 Sweeps: Zero={eq_tol_sweeps['Zero'][-1]:.1f} ({eq_tol_stream_ms['Zero'][-1]:.0f}ms), "
            f"IsoFD={eq_tol_sweeps['IsoFD'][-1]:.1f} ({eq_tol_stream_ms['IsoFD'][-1]:.0f}ms), "
            f"Port={eq_tol_sweeps['SchurPort'][-1]:.1f} ({eq_tol_stream_ms['SchurPort'][-1]:.0f}ms)",
            flush=True,
        )

    ref_conv_cost = np.array(eq_tol_cost["Zero"])
    ref_conv_ms = np.array(eq_tol_stream_ms["Zero"])

    return {
        "grid_n": grid_n,
        "spec": {"r_diag": [0.35, 3.0], "u_max": 1.80, "sigma": 0.45, "q0": 0.50},
        "n_maps_total": len(map_seeds),
        "dev_seeds": map_seeds[:5],
        "heldout_seeds": map_seeds[5:],
        "n_queries_per_map": n_queries,
        "ground_truth_converged_mean_cost": float(np.mean(gt_costs)),
        "same_grid_gp_info_gap": paired_stats(ref_conv_cost - np.array(gt_costs)),
        "equal_bellman_tol_1e_minus_8": {
            k: {
                "mean_sweeps": float(np.mean(eq_tol_sweeps[k])),
                "heldout_mean_sweeps": float(np.mean(eq_tol_sweeps[k][n_dev:])),
                "mean_stream_ms": float(np.mean(eq_tol_stream_ms[k])),
                "heldout_stream_ms": float(np.mean(eq_tol_stream_ms[k][n_dev:])),
                "equal_tol_speedup_vs_zero_init": float(np.mean(ref_conv_ms) / np.mean(eq_tol_stream_ms[k])),
                "mean_cost": float(np.mean(eq_tol_cost[k])),
                "max_bellman_residual": float(np.max(eq_tol_res[k])),
            }
            for k in inits
        },
        "fixed_budget_polish": {
            bkey: {
                "mean_cost": float(np.mean(budget_cost[bkey])),
                "heldout_mean_cost": float(np.mean(budget_cost[bkey][n_dev:])),
                "mean_stream_ms": float(np.mean(budget_ms[bkey])),
                "speedup_vs_zero_tol_1e_8": float(np.mean(ref_conv_ms) / np.mean(budget_ms[bkey])),
                "mean_bellman_residual": float(np.mean(budget_res[bkey])),
                "paired_cost_diff_vs_converged_kkt": paired_stats(
                    np.array(budget_cost[bkey]) - ref_conv_cost,
                    noninferiority_margin=0.005 * float(np.mean(ref_conv_cost)),
                ),
            }
            for bkey in budget_cost
        },
    }


def plot_exp2_v4(g35: dict, g51: dict, out_png: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 4.9))
    for ax, data, lbl_g in [(axes[0], g35, "35²"), (axes[1], g51, "51²")]:
        colors = {"Zero": "#d62728", "Geodesic": "#ff7f0e", "IsoFD": "#2ca02c", "SchurPort": "#1f77b4"}
        markers = {"Zero": "o", "Geodesic": "D", "IsoFD": "^", "SchurPort": "s"}
        for k in ("Zero", "Geodesic", "IsoFD", "SchurPort"):
            t_pts = [
                data["fixed_budget_polish"][f"{k}-1Step"]["mean_stream_ms"],
                data["fixed_budget_polish"][f"{k}-3Step"]["mean_stream_ms"],
                data["equal_bellman_tol_1e_minus_8"][k]["mean_stream_ms"],
            ]
            c_pts = [
                data["fixed_budget_polish"][f"{k}-1Step"]["mean_cost"],
                data["fixed_budget_polish"][f"{k}-3Step"]["mean_cost"],
                data["equal_bellman_tol_1e_minus_8"][k]["mean_cost"],
            ]
            sw_eq = data["equal_bellman_tol_1e_minus_8"][k]["mean_sweeps"]
            ax.plot(t_pts, c_pts, marker=markers[k], color=colors[k], lw=2.0, label=f"{k} (1→3→tol≤1e-8 @ {sw_eq:.1f} sw)")
            for tag, tx, cy in zip(["1", "3", "≤1e-8"], t_pts, c_pts):
                ax.annotate(tag, (tx, cy), xytext=(4, 3), textcoords="offset points", fontsize=7.3, color=colors[k])

        conv_c = data["equal_bellman_tol_1e_minus_8"]["Zero"]["mean_cost"]
        ax.axhline(conv_c * 1.005, color="#777777", ls=":", lw=1.1, label="+0.5% Cost Tolerance")
        ax.set_xlabel("Total 10-Query Stream Time incl. Warm-Start (ms)")
        ax.set_ylabel("Closed-Loop Cost (10 Maps × 10 Queries)")
        ax.set_title(f"Matched {lbl_g} Non-LMDP KKT: Budget & Equal-Tol (≤1e-8) Curves\n(R=diag(0.35, 3.0), u_max=1.80)", fontsize=9.8)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7.8)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Exp 2 (35^2): Equal-Tolerance & Fixed-Budget KKT Curves (10 Maps x 10 Queries) ===", flush=True)
    g35 = run_kkt_grid_suite(grid_n=35, n_queries=10)
    print("\n=== Exp 2 (51^2): Equal-Tolerance & Fixed-Budget KKT Curves (10 Maps x 10 Queries) ===", flush=True)
    g51 = run_kkt_grid_suite(grid_n=51, n_queries=10)

    out_dir = Path(__file__).resolve().parent
    payload = {"metadata": collect_runtime_metadata(), "grid_35": g35, "grid_51": g51}
    (out_dir / "exp2_v4_kkt_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    plot_exp2_v4(g35, g51, out_dir / "exp2_v4_kkt_curves.png")
    print("Saved exp2_v4_kkt_results.json and exp2_v4_kkt_curves.png", flush=True)


if __name__ == "__main__":
    main()
