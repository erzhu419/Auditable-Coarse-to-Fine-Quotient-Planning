"""Experiment 1 (Main Contribution, green_kriging_v3):
1A. Equal-Quality Coarse-to-Fine FD Pareto Sweep vs Strictly Positive Schur-Port Green
    across ALL queries in the stream (Smooth vs Narrow-Barrier 2D Maps, plus 3D 25^3 Maps).
1B. Multi-Waypoint Combinatorial Tour Planning with Decision-Driven Adaptive Port Refinement
    (Fixed Same-GP Fine Controller across all tour planners to isolate quotient/ordering error!).
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core_v3 import (
    GoalBall,
    GroundTruthWorld,
    HazardFeature,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    eval_goal_union,
    generate_benchmark_map,
    reflect_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
)
from schur_port_2d3d import ClassicalFDSolver, SchurPortGreenPlanner


def paired_student_ci95(diffs: Sequence[float]) -> Tuple[float, float]:
    from scipy.stats import t as student_t
    arr = np.asarray(diffs, dtype=float)
    m = float(np.mean(arr))
    if len(arr) <= 1:
        return m, 0.0
    se = float(np.std(arr, ddof=1) / np.sqrt(len(arr)))
    t_crit = float(student_t.ppf(0.975, df=len(arr) - 1))
    return m, t_crit * se


def build_catalog_and_stream(map_seed: int, dim: int, n_queries: int = 24) -> Tuple[List[GoalBall], List[HazardFeature], List[QueryTask]]:
    """Generates strictly non-overlapping catalog waypoints (`dist >= 2.25 * r_goal`) and stream queries."""
    rng = np.random.default_rng(map_seed + 4000)
    r_goal = 0.22 if dim == 2 else 0.28
    waypoints: List[GoalBall] = []
    for _ in range(12):
        for _att in range(80):
            pt = rng.uniform(-1.12, 1.12, size=dim)
            if dim == 3:
                pt[2] *= 0.65
            if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.25 * r_goal for w in waypoints):
                waypoints.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_goal))
                break

    patch_zones: List[HazardFeature] = []
    for _ in range(5):
        pc = rng.uniform(-0.65, 0.65, size=dim)
        if dim == 3:
            pc[2] *= 0.5
        w = 0.19 if dim == 2 else 0.26
        patch_zones.append(HazardFeature(tuple(pc.tolist()), amplitude=15.0, widths=tuple([w] * dim)))

    queries: List[QueryTask] = []
    for k in range(n_queries):
        if k % 3 == 0:
            gi = int(rng.integers(0, len(waypoints)))
            w0 = waypoints[gi]
            goals = (GoalBall(w0.center, 0.0, w0.radius),)
        else:
            pair = rng.choice(len(waypoints), size=2, replace=False)
            phi2 = float(rng.choice([0.0, 0.20, 0.45]))
            goals = (
                GoalBall(waypoints[pair[0]].center, 0.0, r_goal),
                GoalBall(waypoints[pair[1]].center, phi2, r_goal),
            )
        used_c = [np.asarray(g.center) for g in goals]
        cand_s = [w for w in waypoints if all(np.linalg.norm(np.asarray(w.center) - u) >= 2.3 * r_goal for u in used_c)]
        s_pick = cand_s[int(rng.integers(0, len(cand_s)))] if cand_s else GoalBall(tuple((-used_c[0]).tolist()), 0.0, r_goal)
        starts = (s_pick.center,)

        loc_h = ()
        if k % 4 == 3:
            valid_hz = [hz for hz in patch_zones if all(np.linalg.norm(np.asarray(hz.center) - u) >= 1.6 * r_goal for u in used_c)]
            if valid_hz:
                loc_h = (valid_hz[int(rng.integers(0, len(valid_hz)))],)

        queries.append(QueryTask(f"M{map_seed}_Q{k+1}", goals=goals, start_points=starts, local_hazards=loc_h))
    return waypoints, patch_zones, queries


def run_pareto_stream(dim: int, regime: str, fd_grids: Sequence[int], fine_n: int, n_maps: int, n_probes: int, n_queries: int = 24) -> dict:
    """Evaluates ALL `n_queries` per map for BOTH cumulative planning time AND closed-loop CRN cost!"""
    port_configs = [("SchurPort-r1", 1), ("SchurPort-Multi", 4 if dim == 2 else 6)]
    all_methods = ["GroundTruth-FineFD"] + [f"SameGP-FD-{gn}" for gn in fd_grids] + [p[0] for p in port_configs]

    map_costs: Dict[str, List[float]] = {m: [] for m in all_methods}
    map_reach: Dict[str, List[float]] = {m: [] for m in all_methods}
    map_plan_ms: Dict[str, List[float]] = {m: [] for m in all_methods if m != "GroundTruth-FineFD"}
    map_roll_ms: Dict[str, List[float]] = {m: [] for m in all_methods if m != "GroundTruth-FineFD"}
    total_neg_violations = 0
    min_raw_z_seen = np.inf

    base_seed = 100 if (dim == 2 and regime == "smooth") else (200 if dim == 2 else 300)

    for m_i in range(n_maps):
        map_seed = base_seed + m_i
        world = generate_benchmark_map(map_seed, dim=dim, regime=regime, with_drift=True)
        waypoints, patch_zones, queries = build_catalog_and_stream(map_seed, dim=dim, n_queries=n_queries)

        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=map_seed + 11, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        q_fn = km.predict_q
        b_fn = km.predict_b

        # GroundTruth Fine FD reference across ALL queries
        gt_fd = ClassicalFDSolver(world.spec, fine_n, world.q_hidden, world.drift)
        gt_c, gt_r = [], []
        for qi, q in enumerate(queries):
            sol = gt_fd.solve_direct(q)
            sim = simulate_closed_loop_crn(world, sol["policy"], q, n_per_start=16, seed=5000 + 100 * m_i + qi)
            gt_c.append(sim["mean_cost"]); gt_r.append(sim["reach_rate"])
        map_costs["GroundTruth-FineFD"].append(float(np.mean(gt_c)))
        map_reach["GroundTruth-FineFD"].append(float(np.mean(gt_r)))

        # Multi-resolution Same-GP FD Pareto sweep
        for gn in fd_grids:
            m_name = f"SameGP-FD-{gn}"
            fd_s = ClassicalFDSolver(world.spec, gn, q_fn, b_fn)
            p_tot = fd_s.op_build_ms
            cs, rs, rls = [], [], []
            for qi, q in enumerate(queries):
                sol = fd_s.solve_direct(q)
                p_tot += sol["solve_ms"]
                sim = simulate_closed_loop_crn(world, sol["policy"], q, n_per_start=16, seed=5000 + 100 * m_i + qi)
                cs.append(sim["mean_cost"]); rs.append(sim["reach_rate"]); rls.append(sim["rollout_ms"])
            map_costs[m_name].append(float(np.mean(cs)))
            map_reach[m_name].append(float(np.mean(rs)))
            map_plan_ms[m_name].append(p_tot)
            map_roll_ms[m_name].append(float(np.sum(rls)))

        # Strictly Positive Schur-Port Planners on `fine_n`
        for p_name, n_sec in port_configs:
            sp_pl = SchurPortGreenPlanner(world.spec, fine_n, q_fn, b_fn, waypoints, patch_zones, initial_sectors_per_wp=n_sec)
            p_tot = sp_pl.op_build_ms
            cs, rs, rls = [], [], []
            for qi, q in enumerate(queries):
                sol = sp_pl.solve_query(q)
                p_tot += sol["solve_ms"]
                total_neg_violations += sol["negative_node_count"]
                min_raw_z_seen = min(min_raw_z_seen, sol["raw_min_Z"])
                sim = simulate_closed_loop_crn(world, sol["policy"], q, n_per_start=16, seed=5000 + 100 * m_i + qi)
                cs.append(sim["mean_cost"]); rs.append(sim["reach_rate"]); rls.append(sim["rollout_ms"])
            map_costs[p_name].append(float(np.mean(cs)))
            map_reach[p_name].append(float(np.mean(rs)))
            map_plan_ms[p_name].append(p_tot)
            map_roll_ms[p_name].append(float(np.sum(rls)))

        print(
            f"  [{dim}D {regime} map {m_i+1}/{n_maps}] FD-{fine_n}={map_costs[f'SameGP-FD-{fine_n}'][-1]:.3f} ({map_plan_ms[f'SameGP-FD-{fine_n}'][-1]:.0f}ms) | "
            f"FD-{fd_grids[1]}={map_costs[f'SameGP-FD-{fd_grids[1]}'][-1]:.3f} ({map_plan_ms[f'SameGP-FD-{fd_grids[1]}'][-1]:.0f}ms) | "
            f"SchurPort={map_costs['SchurPort-Multi'][-1]:.3f} ({map_plan_ms['SchurPort-Multi'][-1]:.0f}ms)",
            flush=True,
        )

    fine_fd_arr = np.array(map_costs[f"SameGP-FD-{fine_n}"])
    out = {
        "dim": dim,
        "regime": regime,
        "n_maps": n_maps,
        "n_queries_all_evaluated": n_queries,
        "total_pre_floor_negative_violations": total_neg_violations,
        "worst_raw_min_Z": min_raw_z_seen,
        "methods": {},
    }
    for m in all_methods:
        arr = np.array(map_costs[m])
        entry = {"mean_cost": float(np.mean(arr)), "reach_rate": float(np.mean(map_reach[m])), "per_map_costs": map_costs[m]}
        if m != "GroundTruth-FineFD":
            dm, ci = paired_student_ci95(arr - fine_fd_arr)
            entry.update({
                "paired_diff_vs_fine_fd": {"mean": dm, "student_t_ci95": ci},
                "rel_excess_vs_fine_fd_pct": 100.0 * dm / float(np.mean(fine_fd_arr)),
                "total_stream_plan_ms": float(np.mean(map_plan_ms[m])),
                "total_stream_rollout_ms": float(np.mean(map_roll_ms[m])),
            })
        out["methods"][m] = entry
    return out


def run_adaptive_port_tour_experiment(n_maps: int = 12, tours_per_map: int = 8, grid_n: int = 85) -> dict:
    """Evaluates 4 tour-ordering planners on 12 Narrow-Barrier + Vortex Maps x 8 Tour Tasks per map
    drawn from a 12-waypoint facility catalog (`r_wp = 0.27`).
    CRITICAL FAIRNESS: All 4 orderings execute with the EXACT SAME `Same-GP Fine FD (85^2)` leg controller
    so 100% of any performance difference comes strictly from ordering / port-quotient fidelity!
    """
    planners = ["Euclidean-Order", "Fixed-1Port-Order", "Adaptive-SchurPort-Order", "Full-8Port-Order"]
    map_tour_costs = {p: [] for p in planners}
    map_tour_complete = {p: [] for p in planners}
    map_cum_plan_ms = {p: [] for p in planners}
    map_total_backsolves = {p: [] for p in planners}
    adaptive_backsolves_by_task = np.zeros(tours_per_map, dtype=float)

    for m_i in range(n_maps):
        map_seed = 800 + m_i
        world = generate_benchmark_map(map_seed, dim=2, regime="narrow_barrier", with_drift=True)
        rng = np.random.default_rng(map_seed + 77)
        r_wp = 0.27
        catalog_wps: List[GoalBall] = []
        for _ in range(12):
            for _att in range(180):
                pt = rng.uniform(-1.20, 1.20, size=2)
                if all(np.linalg.norm(pt - np.asarray(w.center)) >= 2.06 * r_wp for w in catalog_wps):
                    catalog_wps.append(GoalBall(tuple(pt.tolist()), phi=0.0, radius=r_wp))
                    break

        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=90, seed=map_seed + 5, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)

        exec_fd = ClassicalFDSolver(world.spec, grid_n, km.predict_q, km.predict_b)
        leg_pol_cache = {}
        for j, w in enumerate(catalog_wps):
            qj = QueryTask(f"leg_{j}", (w,), ((0.0, 0.0),))
            leg_pol_cache[j] = exec_fd.solve_direct(qj)["policy"]

        pl_1port = SchurPortGreenPlanner(world.spec, grid_n, km.predict_q, km.predict_b, catalog_wps, initial_sectors_per_wp=1)
        pl_adapt = SchurPortGreenPlanner(world.spec, grid_n, km.predict_q, km.predict_b, catalog_wps, initial_sectors_per_wp=1)
        pl_full8 = SchurPortGreenPlanner(world.spec, grid_n, km.predict_q, km.predict_b, catalog_wps, initial_sectors_per_wp=8)

        cum_ms = {
            "Euclidean-Order": 0.0,
            "Fixed-1Port-Order": pl_1port.op_build_ms,
            "Adaptive-SchurPort-Order": pl_adapt.op_build_ms,
            "Full-8Port-Order": pl_full8.op_build_ms,
        }
        c_tasks = {p: [] for p in planners}
        comp_tasks = {p: [] for p in planners}

        def _eval_tour_order_crn(start_xy: np.ndarray, order: Tuple[int, ...], seed_t: int) -> Tuple[float, float]:
            n_tr = 24
            ss = np.random.SeedSequence([seed_t, 333])
            trngs = [np.random.default_rng(c) for c in ss.spawn(n_tr)]
            tot_c = np.zeros(n_tr, dtype=float)
            all_done = np.ones(n_tr, dtype=bool)
            cur_x = np.repeat(start_xy[None, :], n_tr, axis=0)
            dt = world.spec.dt_sim; sq = np.sqrt(dt)

            for wp_j in order:
                pol = leg_pol_cache[wp_j]
                g_ball = catalog_wps[wp_j]
                alive = all_done.copy()
                for _st in range(650):
                    idx = np.flatnonzero(alive)
                    if len(idx) == 0:
                        break
                    xa = cur_x[idx]
                    u = pol(xa)
                    un = np.linalg.norm(u, axis=1, keepdims=True)
                    u = np.where(un > 25.0, u * (25.0 / np.maximum(un, 1e-12)), u)
                    qt = world.q_total(xa)
                    tot_c[idx] += (qt + 0.5 * np.sum(u ** 2, axis=1)) * dt
                    nz = np.vstack([trngs[ii].normal(0.0, sq, size=2) for ii in idx])
                    xn = reflect_into_box(xa + (world.drift(xa) + u) * dt + world.spec.sigma * nz, world.spec.half_width)
                    cur_x[idx] = xn
                    hit, _ = eval_goal_union(xn, (g_ball,))
                    if np.any(hit):
                        alive[idx[hit]] = False
                failed = alive & all_done
                if np.any(failed):
                    tot_c[failed] += 8.0
                    all_done[failed] = False
            return float(np.mean(tot_c)), float(np.mean(all_done))

        prev_solves = pl_adapt.total_lu_backsolves
        for t_i in range(tours_per_map):
            sub_ids = tuple(rng.choice(len(catalog_wps), size=5, replace=False).tolist())
            start_xy = rng.uniform(-1.15, 1.15, size=2)
            t_seed = 9500 + 20 * m_i + t_i

            t0 = time.perf_counter()
            euc_ord = min(
                itertools.permutations(sub_ids),
                key=lambda perm: float(np.linalg.norm(start_xy - np.asarray(catalog_wps[perm[0]].center))) +
                sum(float(np.linalg.norm(np.asarray(catalog_wps[a].center) - np.asarray(catalog_wps[b].center))) for a, b in zip(perm[:-1], perm[1:])),
            )
            cum_ms["Euclidean-Order"] += 1000.0 * (time.perf_counter() - t0)

            r1 = pl_1port.plan_adaptive_waypoint_tour(start_xy, sub_ids, max_refine_rounds=0)
            cum_ms["Fixed-1Port-Order"] += r1["plan_ms"]

            ra = pl_adapt.plan_adaptive_waypoint_tour(start_xy, sub_ids, margin_tol=0.28, max_refine_rounds=3)
            cum_ms["Adaptive-SchurPort-Order"] += ra["plan_ms"]
            adaptive_backsolves_by_task[t_i] += (pl_adapt.total_lu_backsolves - prev_solves) / n_maps
            prev_solves = pl_adapt.total_lu_backsolves

            rf = pl_full8.plan_adaptive_waypoint_tour(start_xy, sub_ids, max_refine_rounds=0)
            cum_ms["Full-8Port-Order"] += rf["plan_ms"]

            order_eval_cache = {}
            for name, ord_pick in [
                ("Euclidean-Order", euc_ord),
                ("Fixed-1Port-Order", r1["best_order"]),
                ("Adaptive-SchurPort-Order", ra["best_order"]),
                ("Full-8Port-Order", rf["best_order"]),
            ]:
                if ord_pick not in order_eval_cache:
                    order_eval_cache[ord_pick] = _eval_tour_order_crn(start_xy, ord_pick, t_seed)
                c_val, comp_val = order_eval_cache[ord_pick]
                c_tasks[name].append(c_val)
                comp_tasks[name].append(comp_val)

        map_total_backsolves["Euclidean-Order"].append(0)
        map_total_backsolves["Fixed-1Port-Order"].append(pl_1port.total_lu_backsolves)
        map_total_backsolves["Adaptive-SchurPort-Order"].append(pl_adapt.total_lu_backsolves)
        map_total_backsolves["Full-8Port-Order"].append(pl_full8.total_lu_backsolves)

        for p in planners:
            map_tour_costs[p].append(float(np.mean(c_tasks[p])))
            map_tour_complete[p].append(float(np.mean(comp_tasks[p])))
            map_cum_plan_ms[p].append(cum_ms[p])

    adapt_arr = np.array(map_tour_costs["Adaptive-SchurPort-Order"])
    return {
        "n_maps": n_maps,
        "tours_per_map": tours_per_map,
        "catalog_size": len(catalog_wps),
        "initial_catalog_backsolves": len(catalog_wps),
        "mean_new_lu_backsolves_per_tour_step": adaptive_backsolves_by_task.tolist(),
        "methods": {
            p: {
                "mean_tour_cost": float(np.mean(map_tour_costs[p])),
                "full_tour_completion_rate": float(np.mean(map_tour_complete[p])),
                "cumulative_plan_ms": float(np.mean(map_cum_plan_ms[p])),
                "mean_total_lu_backsolves": float(np.mean(map_total_backsolves[p])),
                "adapt_minus_method_cost": dict(zip(["mean", "student_t_ci95"], paired_student_ci95(adapt_arr - np.array(map_tour_costs[p])))),
                "per_map_costs": map_tour_costs[p],
            }
            for p in planners
        },
    }


def plot_exp1(p_smooth: dict, p_narrow: dict, p_3d: dict, tour: dict, out_png: Path):
    fig, axes = plt.subplots(1, 4, figsize=(19.5, 4.6))

    for ax, data, title in [
        (axes[0], p_smooth, "2D Smooth Maps (8×24 Queries)\nQuality–Time Pareto"),
        (axes[1], p_narrow, "2D Narrow-Barrier Maps (8×24 Queries)\nQuality–Time Pareto"),
        (axes[2], p_3d, "3D Grid Stream (6×20 Queries)\nQuality–Time Pareto"),
    ]:
        fd_keys = [k for k in data["methods"] if k.startswith("SameGP-FD-")]
        fd_t = [data["methods"][k]["total_stream_plan_ms"] for k in fd_keys]
        fd_c = [data["methods"][k]["mean_cost"] for k in fd_keys]
        ax.plot(fd_t, fd_c, "o-", color="#d62728", lw=2.1, label="Same-GP Coarse→Fine FD Curve")
        for k, t_v, c_v in zip(fd_keys, fd_t, fd_c):
            gn = k.split("-")[-1]
            ax.annotate(f"{gn}^d", (t_v, c_v), textcoords="offset points", xytext=(4, 4), fontsize=7.8, color="#a50f15")

        for pk, col, mk, lbl in [
            ("SchurPort-r1", "#2ca02c", "^", "Schur-Port (r=1, Strict Z>0)"),
            ("SchurPort-Multi", "#1f77b4", "s", "Schur-Port (Multi-Sector, Z>0)"),
        ]:
            pt = data["methods"][pk]["total_stream_plan_ms"]
            pc = data["methods"][pk]["mean_cost"]
            ax.scatter([pt], [pc], s=110, color=col, marker=mk, zorder=5, label=lbl)

        ax.axhline(data["methods"]["GroundTruth-FineFD"]["mean_cost"], color="#555555", ls=":", lw=1.3, label="GroundTruth Fine FD")
        ax.set_xscale("log")
        ax.set_xlabel("Total Stream Planning Time (ms, log)")
        ax.set_ylabel("Closed-Loop Cost (All Queries)")
        ax.set_title(title, fontsize=9.5)
        ax.grid(True, alpha=0.3, which="both")
        ax.legend(fontsize=7.2)

    # Panel 4: Adaptive Schur-Port Tour Planning (Same-GP Fine Controller!)
    p_names = ["Euclidean-Order", "Fixed-1Port-Order", "Adaptive-SchurPort-Order", "Full-8Port-Order"]
    lbls = ["Euclidean\nOrder", "Fixed 1-Port\nOrder", "Adaptive\nSchur-Port", "Full 8-Port\nReference"]
    cs = [tour["methods"][p]["mean_tour_cost"] for p in p_names]
    ms = [tour["methods"][p]["cumulative_plan_ms"] for p in p_names]
    bars = axes[3].bar(np.arange(4), cs, width=0.54, color=["#7f7f7f", "#ff7f0e", "#1f77b4", "#2ca02c"])
    axes[3].set_xticks(np.arange(4))
    axes[3].set_xticklabels(lbls, fontsize=8.3)
    axes[3].set_ylabel("5-Waypoint Tour Cost (Same-GP Controller)")
    n_tot_tours = tour.get("n_maps", 10) * tour.get("tours_per_map", 6)
    axes[3].set_title(f"Adaptive Port Refinement on {n_tot_tours} Tours\n(Isolating Quotient Ordering Error)", fontsize=9.5)
    axes[3].grid(True, axis="y", alpha=0.3)
    ymin = min(cs) * 0.88
    ymax = max(cs) * 1.09
    axes[3].set_ylim(ymin, ymax)
    for b, c_v, m_v in zip(bars, cs, ms):
        axes[3].text(b.get_x() + b.get_width() / 2, c_v + 0.01 * (ymax - ymin), f"{c_v:.2f}\n({m_v:.0f}ms)", ha="center", va="bottom", fontsize=8.0)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Exp 1A-1: 2D Smooth Regime Pareto Sweep (8 maps x 24 queries, all evaluated) ===", flush=True)
    p_smooth = run_pareto_stream(dim=2, regime="smooth", fd_grids=[21, 31, 41, 61, 81], fine_n=81, n_maps=8, n_probes=40, n_queries=24)

    print("\n=== Exp 1A-2: 2D Narrow-Barrier Regime Pareto Sweep (8 maps x 24 queries, all evaluated) ===", flush=True)
    p_narrow = run_pareto_stream(dim=2, regime="narrow_barrier", fd_grids=[21, 31, 41, 61, 81], fine_n=81, n_maps=8, n_probes=95, n_queries=24)

    print("\n=== Exp 1A-3: 3D Grid Pareto Sweep (6 maps x 20 queries, all evaluated) ===", flush=True)
    p_3d = run_pareto_stream(dim=3, regime="narrow_barrier", fd_grids=[13, 17, 21, 25], fine_n=25, n_maps=6, n_probes=110, n_queries=20)

    print("\n=== Exp 1B: Adaptive Decision-Driven Port Refinement on 5-Waypoint Tours (12 maps x 8 tours) ===", flush=True)
    tour = run_adaptive_port_tour_experiment(n_maps=12, tours_per_map=8, grid_n=85)
    for k, v in tour["methods"].items():
        print(f"  Tour {k:26s} | Cost={v['mean_tour_cost']:.3f} | Complete={v['full_tour_completion_rate']*100:.1f}% | 8-Tour Plan={v['cumulative_plan_ms']:.1f}ms | Backsolves={v['mean_total_lu_backsolves']:.1f} | Diff={v['adapt_minus_method_cost']['mean']:+.3f}±{v['adapt_minus_method_cost']['student_t_ci95']:.3f}", flush=True)
    print("  Mean new LU back-solves across tour sequence 1->8:", [round(x, 2) for x in tour["mean_new_lu_backsolves_per_tour_step"]], flush=True)

    out_dir = Path(__file__).resolve().parent
    res = {"pareto_2d_smooth": p_smooth, "pareto_2d_narrow_barrier": p_narrow, "pareto_3d": p_3d, "adaptive_tour_2d": tour}
    (out_dir / "exp1_pareto_and_tour_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_exp1(p_smooth, p_narrow, p_3d, tour, out_dir / "exp1_pareto_and_adaptive_tour.png")
    print("Saved exp1_pareto_and_tour_results.json and exp1_pareto_and_adaptive_tour.png", flush=True)


if __name__ == "__main__":
    main()
