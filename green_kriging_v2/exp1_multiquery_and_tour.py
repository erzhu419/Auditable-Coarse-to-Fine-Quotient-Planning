"""Battle 1 (v2): Same-GP Multi-Query Stream (2D 81x81 & 3D 25^3) and Combinatorial
Multi-Waypoint Tour Planning across 10 Independent Procedural Maps.

Directly tests whether Reusable Port/Capacitary Green Operators reduce cumulative multi-query
planning cost against `Same-GP + Direct FD` and `Same-GP + Warm-Start ILU-BiCGSTAB` at matched
closed-loop control quality, with map-clustered paired confidence intervals.
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core_spec_and_gp import (
    GoalBall,
    GroundTruthWorld,
    HazardBump,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    generate_random_map,
    reflect_into_box,
    sample_noisy_probes,
    simulate_closed_loop_crn,
)
from solvers_2d3d import ClassicalFDSolver, ReusableGreenOperator2D3D


def generate_stream_queries(map_seed: int, dim: int, n_queries: int = 60) -> List[QueryTask]:
    """Generates a realistic multi-query stream over 14 candidate waypoint ports and 6 local hazard zones
    (combining single-goal, multi-goal, and dynamic local blockage queries).
    """
    rng = np.random.default_rng(map_seed + 5000)
    r_goal = 0.22 if dim == 2 else 0.28
    waypoints = []
    for _ in range(14):
        for _att in range(40):
            pt = rng.uniform(-1.05, 1.05, size=dim)
            if dim == 3:
                pt[2] *= 0.65
            if all(np.linalg.norm(pt - w) > 1.8 * r_goal for w in waypoints):
                waypoints.append(pt)
                break

    patch_Pool = []
    for _ in range(6):
        pc = rng.uniform(-0.65, 0.65, size=dim)
        if dim == 3:
            pc[2] *= 0.5
        patch_Pool.append(HazardBump(tuple(pc.tolist()), amplitude=13.5, sigma_width=0.20 if dim == 2 else 0.28))

    queries = []
    for k in range(n_queries):
        if k % 3 == 0:
            gi = int(rng.integers(0, len(waypoints)))
            goals = (GoalBall(tuple(waypoints[gi].tolist()), phi=0.0, radius=r_goal),)
        else:
            g_pair = rng.choice(len(waypoints), size=2, replace=False)
            phi2 = float(rng.choice([0.0, 0.15, 0.30]))
            goals = (
                GoalBall(tuple(waypoints[g_pair[0]].tolist()), phi=0.0, radius=r_goal),
                GoalBall(tuple(waypoints[g_pair[1]].tolist()), phi=phi2, radius=r_goal),
            )

        # Pick 2 starts from remaining waypoints
        used = [ np.array(g.center) for g in goals ]
        cand_s = [w for w in waypoints if all(np.linalg.norm(w - u) > 2.4 * r_goal for u in used)]
        if len(cand_s) >= 2:
            s_idx = rng.choice(len(cand_s), size=2, replace=False)
            starts = (tuple(cand_s[s_idx[0]].tolist()), tuple(cand_s[s_idx[1]].tolist()))
        else:
            starts = (tuple((-np.array(goals[0].center)).tolist()),)

        loc_h = ()
        if k % 4 == 3:
            cand_h = [hb for hb in patch_Pool if all(np.linalg.norm(np.array(hb.center) - u) > 1.5 * r_goal for u in used)]
            if cand_h:
                loc_h = (cand_h[int(rng.integers(0, len(cand_h)))],)

        queries.append(QueryTask(f"S{map_seed}_Q{k+1}", goals=goals, start_points=starts, local_hazards=loc_h))
    return queries


def paired_ci95(diffs: Sequence[float]) -> Tuple[float, float]:
    arr = np.asarray(diffs, dtype=float)
    m = float(np.mean(arr))
    se = float(np.std(arr, ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0
    return m, 1.96 * se


def run_part1a_stream(dim: int, grid_n: int, n_maps: int, n_probes: int, n_queries: int = 60, eval_queries: int = 8) -> dict:
    """Evaluates planning time across all `n_queries` and closed-loop CRN rollout quality on `eval_queries` per map."""
    methods = ["Oracle-FD", "SameGP-Fresh-FD", "SameGP-ILU-Krylov", "SameGP-PortGreen-r1", "SameGP-PortGreen-Multipole", "SameGP-ExactCapGreen"]
    per_map_costs: Dict[str, List[float]] = {m: [] for m in methods}
    per_map_reach: Dict[str, List[float]] = {m: [] for m in methods}
    per_map_cum_ms: Dict[str, List[np.ndarray]] = {m: [] for m in methods if m != "Oracle-FD"}
    per_map_rollout_ms: Dict[str, List[float]] = {m: [] for m in methods if m != "Oracle-FD"}
    gp_fit_list = []

    for m_i in range(n_maps):
        map_seed = (100 if dim == 2 else 300) + m_i
        world, _ = generate_random_map(map_seed, dim=dim, with_drift=True, n_queries=2)
        queries = generate_stream_queries(map_seed, dim=dim, n_queries=n_queries)

        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=map_seed + 10, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        gp_fit_list.append(km.fit_ms)

        q_fn = lambda X, _km=km: _km.predict_q(X, return_std=False)[0]
        b_fn = lambda X, _km=km: _km.predict_b(X, return_std=False)

        # Ground-truth reference solver (evaluated on the first `eval_queries` queries)
        ref_fd = ClassicalFDSolver(world.spec, grid_n, world.q_hidden, world.drift)
        c_or, r_or = [], []
        for qi in range(eval_queries):
            sol = ref_fd.solve_direct(queries[qi])
            sim = simulate_closed_loop_crn(world, sol["policy"], queries[qi], n_per_start=25, seed=9000 + qi)
            c_or.append(sim["mean_cost"]); r_or.append(sim["reach_rate"])
        per_map_costs["Oracle-FD"].append(float(np.mean(c_or)))
        per_map_reach["Oracle-FD"].append(float(np.mean(r_or)))

        # Candidate Same-GP solvers across full 60-query stream!
        fd_solver = ClassicalFDSolver(world.spec, grid_n, q_fn, b_fn)
        kry_solver = ClassicalFDSolver(world.spec, grid_n, q_fn, b_fn)
        gr_r1 = ReusableGreenOperator2D3D(world.spec, grid_n, q_fn, b_fn)
        gr_mp = ReusableGreenOperator2D3D(world.spec, grid_n, q_fn, b_fn)
        gr_cap = ReusableGreenOperator2D3D(world.spec, grid_n, q_fn, b_fn)

        runners = [
            ("SameGP-Fresh-FD", fd_solver.op_build_ms, lambda q: fd_solver.solve_direct(q)),
            ("SameGP-ILU-Krylov", kry_solver.op_build_ms, lambda q: kry_solver.solve_warm_krylov(q)),
            ("SameGP-PortGreen-r1", gr_r1.op_build_ms, lambda q: gr_r1.solve_port_reduced(q, rich_modes=False)),
            ("SameGP-PortGreen-Multipole", gr_mp.op_build_ms, lambda q: gr_mp.solve_port_reduced(q, rich_modes=True)),
            ("SameGP-ExactCapGreen", gr_cap.op_build_ms, lambda q: gr_cap.solve_exact_capacitary(q)),
        ]

        for name, init_ms, fn in runners:
            solve_times = []
            c_list, r_list, roll_ms_list = [], [], []
            for qi, q in enumerate(queries):
                sol = fn(q)
                solve_times.append(sol["solve_ms"])
                if qi < eval_queries:
                    sim = simulate_closed_loop_crn(world, sol["policy"], q, n_per_start=25, seed=9000 + qi)
                    c_list.append(sim["mean_cost"])
                    r_list.append(sim["reach_rate"])
                    roll_ms_list.append(sim["rollout_ms"])
            cum_curve = init_ms + np.cumsum(solve_times)
            per_map_cum_ms[name].append(cum_curve)
            per_map_costs[name].append(float(np.mean(c_list)))
            per_map_reach[name].append(float(np.mean(r_list)))
            per_map_rollout_ms[name].append(float(np.mean(roll_ms_list)))

    summary = {
        "dim": dim,
        "grid_n": grid_n,
        "n_maps": n_maps,
        "n_probes": n_probes,
        "n_queries": n_queries,
        "mean_gp_fit_ms": float(np.mean(gp_fit_list)),
        "methods": {},
    }
    base_fd_costs = np.array(per_map_costs["SameGP-Fresh-FD"])
    checkpoints = [1, 5, 10, 20, 40, n_queries]

    for m in methods:
        mc = float(np.mean(per_map_costs[m]))
        mr = float(np.mean(per_map_reach[m]))
        entry = {"mean_cost": mc, "reach_rate": mr, "per_map_costs": per_map_costs[m]}
        if m != "Oracle-FD":
            diff_m, ci_m = paired_ci95(np.array(per_map_costs[m]) - base_fd_costs)
            cum_arr = np.mean(np.vstack(per_map_cum_ms[m]), axis=0)
            entry.update({
                "paired_diff_vs_fresh_fd": diff_m,
                "paired_ci95_vs_fresh_fd": ci_m,
                "mean_rollout_ms_per_query": float(np.mean(per_map_rollout_ms[m])),
                "cumulative_plan_ms": {str(k): float(cum_arr[k - 1]) for k in checkpoints},
                "full_cum_curve_ms": cum_arr.tolist(),
            })
        summary["methods"][m] = entry
    return summary


def run_part1b_waypoint_tour_2d(n_maps: int = 10, n_waypoints: int = 6, grid_n: int = 71) -> dict:
    """Asymmetric multi-waypoint tour planning in vortex wind + hidden hazards across 10 maps."""
    methods = ["Euclidean-TSP-Free", "SameGP-FreshFD-Tour", "SameGP-PortGreen-Tour"]
    map_costs = {m: [] for m in methods}
    map_plan_ms = {m: [] for m in methods}

    for m_i in range(n_maps):
        map_seed = 700 + m_i
        world, _ = generate_random_map(map_seed, dim=2, with_drift=True, n_queries=1)
        rng = np.random.default_rng(map_seed + 99)
        r_goal = 0.22
        pts_w = [np.array([-1.05, -1.05])]  # index 0 is start x0; 1..n_waypoints are targets
        while len(pts_w) < n_waypoints + 1:
            cand = rng.uniform(-1.05, 1.05, size=2)
            if all(np.linalg.norm(cand - p) > 2.3 * r_goal for p in pts_w):
                pts_w.append(cand)

        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=35, seed=map_seed + 3, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)
        q_fn = lambda X, _km=km: _km.predict_q(X, return_std=False)[0]
        b_fn = lambda X, _km=km: _km.predict_b(X, return_std=False)

        def _simulate_tour(order: Tuple[int, ...], leg_policies: Dict[int, callable]) -> float:
            # Simulate 30 CRN sequential tours visiting waypoints in `order`
            n_tr = 30
            ss = np.random.SeedSequence([map_seed, 888])
            trngs = [np.random.default_rng(c) for c in ss.spawn(n_tr)]
            total_c = np.zeros(n_tr, dtype=float)
            cur_x = np.repeat(pts_w[0][None, :], n_tr, axis=0)
            dt = world.spec.dt_sim
            sqrt_dt = np.sqrt(dt)
            for target_idx in order:
                pol = leg_policies[target_idx]
                gc = pts_w[target_idx]
                alive = np.ones(n_tr, dtype=bool)
                for _st in range(450):
                    idx = np.flatnonzero(alive)
                    if len(idx) == 0:
                        break
                    xa = cur_x[idx]
                    hit = np.linalg.norm(xa - gc[None, :], axis=1) <= r_goal
                    if np.any(hit):
                        alive[idx[hit]] = False
                        idx = np.flatnonzero(alive)
                        if len(idx) == 0:
                            break
                        xa = cur_x[idx]
                    u = pol(xa)
                    un = np.linalg.norm(u, axis=1, keepdims=True)
                    u = np.where(un > 25.0, u * (25.0 / np.maximum(un, 1e-12)), u)
                    qt = world.q_total(xa)
                    total_c[idx] += (qt + 0.5 * np.sum(u ** 2, axis=1)) * dt
                    noise = np.vstack([trngs[ii].normal(0.0, sqrt_dt, size=2) for ii in idx])
                    cur_x[idx] = reflect_into_box(xa + (world.drift(xa) + u) * dt + world.spec.sigma * noise, world.spec.half_width)
            return float(np.mean(total_c))

        # 1. Euclidean TSP + Free-space straight/FD controller
        t0 = time.perf_counter()
        free_fd = ReusableGreenOperator2D3D(world.spec, 51, lambda X: np.zeros(len(X)), None)
        free_pols = {}
        for j in range(1, n_waypoints + 1):
            qj = QueryTask(f"free_{j}", (GoalBall(tuple(pts_w[j].tolist()), 0.0, r_goal),), (tuple(pts_w[0].tolist()),))
            free_pols[j] = free_fd.solve_port_reduced(qj, rich_modes=False)["policy"]
        best_euc_order = min(
            itertools.permutations(range(1, n_waypoints + 1)),
            key=lambda perm: sum(float(np.linalg.norm(pts_w[a] - pts_w[b])) for a, b in zip((0,) + perm[:-1], perm)),
        )
        map_plan_ms["Euclidean-TSP-Free"].append(1000.0 * (time.perf_counter() - t0))
        map_costs["Euclidean-TSP-Free"].append(_simulate_tour(best_euc_order, free_pols))

        # 2. Same-GP + Fresh FD asymmetric stochastic tour
        t0 = time.perf_counter()
        fd_slv = ClassicalFDSolver(world.spec, grid_n, q_fn, b_fn)
        fd_pols = {}
        fd_val_mat = np.zeros((n_waypoints + 1, n_waypoints + 1))
        for j in range(1, n_waypoints + 1):
            qj = QueryTask(f"fd_{j}", (GoalBall(tuple(pts_w[j].tolist()), 0.0, r_goal),), (tuple(pts_w[0].tolist()),))
            sol = fd_slv.solve_direct(qj)
            fd_pols[j] = sol["policy"]
            all_src = np.vstack(pts_w)
            fd_val_mat[:, j] = sol["value_fn"](all_src)
        best_fd_order = min(
            itertools.permutations(range(1, n_waypoints + 1)),
            key=lambda perm: sum(float(fd_val_mat[a, b]) for a, b in zip((0,) + perm[:-1], perm)),
        )
        map_plan_ms["SameGP-FreshFD-Tour"].append(fd_slv.op_build_ms + 1000.0 * (time.perf_counter() - t0))
        map_costs["SameGP-FreshFD-Tour"].append(_simulate_tour(best_fd_order, fd_pols))

        # 3. Same-GP + Port-Green asymmetric stochastic tour
        t0 = time.perf_counter()
        gr_slv = ReusableGreenOperator2D3D(world.spec, grid_n, q_fn, b_fn)
        gr_pols = {}
        gr_val_mat = np.zeros((n_waypoints + 1, n_waypoints + 1))
        for j in range(1, n_waypoints + 1):
            qj = QueryTask(f"gr_{j}", (GoalBall(tuple(pts_w[j].tolist()), 0.0, r_goal),), (tuple(pts_w[0].tolist()),))
            sol = gr_slv.solve_port_reduced(qj, rich_modes=True)
            gr_pols[j] = sol["policy"]
            all_src = np.vstack(pts_w)
            gr_val_mat[:, j] = sol["value_fn"](all_src)
        best_gr_order = min(
            itertools.permutations(range(1, n_waypoints + 1)),
            key=lambda perm: sum(float(gr_val_mat[a, b]) for a, b in zip((0,) + perm[:-1], perm)),
        )
        map_plan_ms["SameGP-PortGreen-Tour"].append(1000.0 * (time.perf_counter() - t0))
        map_costs["SameGP-PortGreen-Tour"].append(_simulate_tour(best_gr_order, gr_pols))

    diff_vs_fd, ci_vs_fd = paired_ci95(np.array(map_costs["SameGP-PortGreen-Tour"]) - np.array(map_costs["SameGP-FreshFD-Tour"]))
    diff_vs_euc, ci_vs_euc = paired_ci95(np.array(map_costs["SameGP-PortGreen-Tour"]) - np.array(map_costs["Euclidean-TSP-Free"]))
    return {
        "n_maps": n_maps,
        "n_waypoints": n_waypoints,
        "methods": {
            m: {
                "mean_tour_cost": float(np.mean(map_costs[m])),
                "mean_plan_ms": float(np.mean(map_plan_ms[m])),
                "per_map_costs": map_costs[m],
            }
            for m in methods
        },
        "port_green_minus_fd_cost": {"mean": diff_vs_fd, "ci95": ci_vs_fd},
        "port_green_minus_euclidean_cost": {"mean": diff_vs_euc, "ci95": ci_vs_euc},
    }


def plot_battle1(s2d: dict, s3d: dict, tour: dict, out_png: Path):
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8))
    ks2 = np.arange(1, s2d["n_queries"] + 1)
    ks3 = np.arange(1, s3d["n_queries"] + 1)

    styles = [
        ("SameGP-Fresh-FD", "#d62728", "-", "Same-GP + Direct FD"),
        ("SameGP-ILU-Krylov", "#ff7f0e", "--", "Same-GP + Warm ILU-BiCGSTAB"),
        ("SameGP-ExactCapGreen", "#9467bd", "-.", "Same-GP + Exact Cap-Green"),
        ("SameGP-PortGreen-Multipole", "#1f77b4", "-", "Same-GP + Port-Green (Multipole)"),
        ("SameGP-PortGreen-r1", "#2ca02c", ":", "Same-GP + Port-Green (r=1)"),
    ]
    for m, col, ls, lbl in styles:
        axes[0].plot(ks2, s2d["methods"][m]["full_cum_curve_ms"], color=col, ls=ls, lw=2.1, label=lbl)
        axes[1].plot(ks3, s3d["methods"][m]["full_cum_curve_ms"], color=col, ls=ls, lw=2.1, label=lbl)

    axes[0].set_title("2D Fine Grid (81×81, 10 Maps): Cumulative Plan Time")
    axes[0].set_xlabel("Number of Queries K")
    axes[0].set_ylabel("Cumulative Operator + Solve Time (ms)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)

    axes[1].set_title("3D Grid (25³, 15,625 Nodes, 6 Maps): Cumulative Plan Time")
    axes[1].set_xlabel("Number of Queries K")
    axes[1].set_ylabel("Cumulative Operator + Solve Time (ms)")
    axes[1].set_yscale("log")
    axes[1].grid(True, alpha=0.3, which="both")

    m_names = ["Euclidean-TSP-Free", "SameGP-FreshFD-Tour", "SameGP-PortGreen-Tour"]
    x_pos = np.arange(len(m_names))
    costs = [tour["methods"][m]["mean_tour_cost"] for m in m_names]
    p_ms = [tour["methods"][m]["mean_plan_ms"] for m in m_names]
    bars = axes[2].bar(x_pos, costs, width=0.52, color=["#7f7f7f", "#d62728", "#1f77b4"])
    axes[2].set_xticks(x_pos)
    axes[2].set_xticklabels(["Euclidean TSP\n(Free Guide)", "Same-GP +\nDirect FD Tour", "Same-GP +\nPort-Green Tour"], fontsize=9)
    axes[2].set_ylabel("6-Waypoint Closed-Loop Tour Cost")
    axes[2].set_title("Asymmetric Vortex 6-Waypoint Tour (10 Maps)")
    axes[2].grid(True, axis="y", alpha=0.3)
    for bar, c, ms in zip(bars, costs, p_ms):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3, f"Cost={c:.2f}\n({ms:.0f} ms)", ha="center", va="bottom", fontsize=8.5)
    axes[2].set_ylim(0, max(costs) * 1.24)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Battle 1A (2D 81x81, 10 random maps x 60 queries) ===")
    s2d = run_part1a_stream(dim=2, grid_n=81, n_maps=10, n_probes=35, n_queries=60, eval_queries=8)
    for k, v in s2d["methods"].items():
        if "cumulative_plan_ms" in v:
            print(f"  2D {k:28s} | Cost={v['mean_cost']:.3f} (diff={v['paired_diff_vs_fresh_fd']:+.4f}±{v['paired_ci95_vs_fresh_fd']:.4f}) | K=1:{v['cumulative_plan_ms']['1']:.1f}ms -> K=60:{v['cumulative_plan_ms']['60']:.1f}ms | Rollout={v['mean_rollout_ms_per_query']:.1f}ms")
        else:
            print(f"  2D {k:28s} | Cost={v['mean_cost']:.3f} | Reach={v['reach_rate']*100:.1f}%")

    print("\n=== Battle 1A (3D 25^3 = 15,625 nodes, 6 random maps x 50 queries) ===")
    s3d = run_part1a_stream(dim=3, grid_n=25, n_maps=6, n_probes=60, n_queries=50, eval_queries=6)
    for k, v in s3d["methods"].items():
        if "cumulative_plan_ms" in v:
            print(f"  3D {k:28s} | Cost={v['mean_cost']:.3f} (diff={v['paired_diff_vs_fresh_fd']:+.4f}±{v['paired_ci95_vs_fresh_fd']:.4f}) | K=1:{v['cumulative_plan_ms']['1']:.1f}ms -> K=50:{v['cumulative_plan_ms']['50']:.1f}ms | Rollout={v['mean_rollout_ms_per_query']:.1f}ms")
        else:
            print(f"  3D {k:28s} | Cost={v['mean_cost']:.3f} | Reach={v['reach_rate']*100:.1f}%")

    print("\n=== Battle 1B (2D 6-Waypoint Asymmetric Vortex Tour, 10 random maps) ===")
    tour = run_part1b_waypoint_tour_2d(n_maps=10, n_waypoints=6, grid_n=71)
    for k, v in tour["methods"].items():
        print(f"  Tour {k:24s} | Cost={v['mean_tour_cost']:.3f} | Plan={v['mean_plan_ms']:.1f}ms")

    out_dir = Path(__file__).resolve().parent
    res = {"stream_2d": s2d, "stream_3d": s3d, "waypoint_tour_2d": tour}
    (out_dir / "battle1_multiquery_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_battle1(s2d, s3d, tour, out_dir / "battle1_multiquery_and_tour.png")
    print("Saved battle1_multiquery_results.json and battle1_multiquery_and_tour.png")


if __name__ == "__main__":
    main()
