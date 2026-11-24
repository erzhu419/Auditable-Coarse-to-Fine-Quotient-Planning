"""Battle 2 (v2): First-Principles Doob Adjoint Occupation Sensitivity Probing
(Point Queries & Reachable Exploration Trajectories) and Genuine Nonlinear Robust HJB Bounds
across 10 Independent Procedural Maps.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

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
from solvers_2d3d import (
    ClassicalFDSolver,
    ReusableGreenOperator2D3D,
    solve_nonlinear_robust_hjb_envelope_2d,
)


def paired_ci95(diffs: Sequence[float]) -> Tuple[float, float]:
    arr = np.asarray(diffs, dtype=float)
    m = float(np.mean(arr))
    se = float(np.std(arr, ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0
    return m, 1.96 * se


def build_challenging_localized_hazard_map(map_seed: int) -> Tuple[GroundTruthWorld, List[QueryTask]]:
    """Generates a random map with compact high-penalty hazard pockets + vortex wind,
    where blind or global-perimeter probing wastes budget outside the task-relevant flow corridors.
    """
    rng = np.random.default_rng(map_seed)
    spec = ProblemSpec(dim=2, half_width=1.65, sigma=0.42, q0=0.50)
    n_mines = int(rng.integers(5, 8))
    hazards = []
    for _ in range(n_mines):
        c = rng.uniform(-0.90, 0.90, size=2)
        amp = float(rng.uniform(14.0, 24.0))
        wid = float(rng.uniform(0.16, 0.24))
        hazards.append(HazardBump(tuple(c.tolist()), amp, wid))
    vc = rng.uniform(-0.35, 0.35, size=2)
    vstr = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.75, 1.15))
    world = GroundTruthWorld(spec, hazards, vortices=[(vc, vstr, 0.85, 0, 1)])

    # 3 task queries on this map
    queries = []
    pairs = [((-0.95, -0.85), (0.90, 0.85)), ((-0.90, 0.85), (0.88, -0.82)), ((0.0, -0.95), (0.05, 0.92))]
    for qi, (st, gl) in enumerate(pairs):
        st_j = np.clip(np.array(st) + rng.normal(0.0, 0.08, size=2), -1.15, 1.15)
        gl_j = np.clip(np.array(gl) + rng.normal(0.0, 0.08, size=2), -1.15, 1.15)
        queries.append(QueryTask(f"M{map_seed}_T{qi+1}", (GoalBall(tuple(gl_j.tolist()), 0.0, 0.22),), (tuple(st_j.tolist()),)))
    return world, queries


def select_batch_with_repulsion(pts: np.ndarray, scores: np.ndarray, existing_X: np.ndarray, k_select: int, min_dist: float = 0.22) -> np.ndarray:
    chosen = []
    cur_X = existing_X.copy()
    order = np.argsort(-scores)
    for idx in order:
        cand = pts[idx]
        if np.all(np.linalg.norm(cur_X - cand[None, :], axis=1) >= min_dist):
            chosen.append(cand)
            cur_X = np.vstack([cur_X, cand[None, :]])
            if len(chosen) == k_select:
                break
    if len(chosen) < k_select:
        for idx in order:
            if len(chosen) == k_select:
                break
            chosen.append(pts[idx])
    return np.array(chosen)


def run_part2a_point_probing(n_maps: int = 10, grid_n: int = 61) -> dict:
    """Sequential active probing: N0=8 -> 2 rounds of +8 probes -> N_total=24 across 10 independent maps."""
    strategies = ["Random", "Global-MaxVar", "Corridor-Heuristic", "Doob-Adjoint-Sensitivity"]
    map_costs = {s: [] for s in ["Oracle-FD"] + strategies}
    map_haz_costs = {s: [] for s in ["Oracle-FD"] + strategies}
    acq_ms = {s: [] for s in strategies}

    for m_i in range(n_maps):
        map_seed = 1200 + m_i
        world, queries = build_challenging_localized_hazard_map(map_seed)
        X0, q0_obs, b0_obs = sample_noisy_probes(world, n_probes=8, seed=map_seed + 1, probe_box=1.35, include_drift=True)

        # Ground-truth reference
        ref_fd = ClassicalFDSolver(world.spec, grid_n, world.q_hidden, world.drift)
        or_c, or_h = [], []
        for qi, q in enumerate(queries):
            sol = ref_fd.solve_direct(q)
            sim = simulate_closed_loop_crn(world, sol["policy"], q, n_per_start=35, seed=4000 + qi)
            or_c.append(sim["mean_cost"]); or_h.append(sim["mean_hazard_cost"])
        map_costs["Oracle-FD"].append(float(np.mean(or_c)))
        map_haz_costs["Oracle-FD"].append(float(np.mean(or_h)))

        for strat in strategies:
            rng = np.random.default_rng(map_seed + 50)
            X_cur = X0.copy()
            q_cur = q0_obs.copy()
            b_cur = b0_obs.copy()
            t_acq_total = 0.0

            for _round in range(2):  # 2 rounds x 8 = +16 probes => N=24 total
                km_tmp = KrigingWorldModel(X_cur, q_cur, b_cur)
                t0 = time.perf_counter()
                gr_tmp = ReusableGreenOperator2D3D(
                    world.spec, 51,
                    lambda X, _k=km_tmp: _k.predict_q(X, return_std=False)[0],
                    lambda X, _k=km_tmp: _k.predict_b(X, return_std=False),
                )
                pts_cand = gr_tmp.pts
                # Restrict candidate sensor domain to [-1.35, 1.35]^2
                in_box = np.all(np.abs(pts_cand) <= 1.35, axis=1)
                pts_in = pts_cand[in_box]
                _, std_q = km_tmp.predict_q(pts_in, return_std=True)

                if strat == "Random":
                    X_new = rng.uniform(-1.35, 1.35, size=(8, 2))
                elif strat == "Global-MaxVar":
                    X_new = select_batch_with_repulsion(pts_in, std_q, X_cur, 8, min_dist=0.25)
                elif strat == "Corridor-Heuristic":
                    # Distance to straight segments start -> goal across queries
                    cor_w = np.zeros(len(pts_in))
                    for q in queries:
                        a = np.array(q.start_points[0]); b = np.array(q.goals[0].center)
                        ab = b - a
                        t_proj = np.clip(((pts_in - a[None, :]) @ ab) / max(float(ab @ ab), 1e-9), 0.0, 1.0)
                        proj = a[None, :] + t_proj[:, None] * ab[None, :]
                        d_seg = np.linalg.norm(pts_in - proj, axis=1)
                        cor_w = np.maximum(cor_w, np.exp(-0.5 * (d_seg / 0.35) ** 2))
                    X_new = select_batch_with_repulsion(pts_in, cor_w * std_q, X_cur, 8, min_dist=0.22)
                elif strat == "Doob-Adjoint-Sensitivity":
                    # Exact first-principles occupation measure summed over task queries!
                    occ_full = np.zeros(len(pts_cand))
                    for q in queries:
                        occ_full += gr_tmp.compute_doob_sensitivity(q)
                    occ_in = occ_full[in_box]
                    X_new = select_batch_with_repulsion(pts_in, occ_in * std_q, X_cur, 8, min_dist=0.22)
                else:
                    raise ValueError(strat)

                t_acq_total += 1000.0 * (time.perf_counter() - t0)
                q_new = np.maximum(0.0, world.q_hidden(X_new) + rng.normal(0.0, 0.40, size=len(X_new)))
                b_new = world.drift(X_new) + rng.normal(0.0, 0.15, size=(len(X_new), 2))
                X_cur = np.vstack([X_cur, X_new])
                q_cur = np.concatenate([q_cur, q_new])
                b_cur = np.vstack([b_cur, b_new])

            acq_ms[strat].append(t_acq_total)
            km_fin = KrigingWorldModel(X_cur, q_cur, b_cur)
            fd_fin = ClassicalFDSolver(
                world.spec, grid_n,
                lambda X, _k=km_fin: _k.predict_q(X, return_std=False)[0],
                lambda X, _k=km_fin: _k.predict_b(X, return_std=False),
            )
            cs, hs = [], []
            for qi, q in enumerate(queries):
                sol = fd_fin.solve_direct(q)
                sim = simulate_closed_loop_crn(world, sol["policy"], q, n_per_start=35, seed=4000 + qi)
                cs.append(sim["mean_cost"]); hs.append(sim["mean_hazard_cost"])
            map_costs[strat].append(float(np.mean(cs)))
            map_haz_costs[strat].append(float(np.mean(hs)))

    doob_arr = np.array(map_costs["Doob-Adjoint-Sensitivity"])
    comparisons = {}
    for other in ["Random", "Global-MaxVar", "Corridor-Heuristic"]:
        dm, ci = paired_ci95(doob_arr - np.array(map_costs[other]))
        comparisons[f"Doob_minus_{other}"] = {"mean": dm, "ci95": ci}

    return {
        "n_maps": n_maps,
        "total_probes": 24,
        "methods": {
            m: {
                "mean_deploy_cost": float(np.mean(map_costs[m])),
                "mean_hazard_cost": float(np.mean(map_haz_costs[m])),
                "mean_acq_ms": float(np.mean(acq_ms[m])) if m in acq_ms else 0.0,
                "per_map_costs": map_costs[m],
            }
            for m in ["Oracle-FD"] + strategies
        },
        "paired_differences": comparisons,
    }


def run_part2b_reachable_trajectory_exploration(n_maps: int = 8, grid_n: int = 55) -> dict:
    """Reachable on-trajectory exploration (no teleporting probes!):
    Agent starts with 0 probes, executes 4 physical closed-loop exploration episodes,
    collecting subsampled noisy trajectory measurements while paying real exploration cost,
    then deploys on Q1-Q3.
    """
    modes = ["Greedy-Exploit-Traj", "GlobalVar-Detour-Traj", "Doob-Sensitivity-Detour-Traj"]
    deploy_costs = {m: [] for m in modes}
    explore_costs = {m: [] for m in modes}

    for m_i in range(n_maps):
        map_seed = 1500 + m_i
        world, queries = build_challenging_localized_hazard_map(map_seed)
        dt = world.spec.dt_sim
        sqrt_dt = np.sqrt(dt)

        for mode in modes:
            rng = np.random.default_rng(map_seed + 303)
            X_obs_list = []
            q_obs_list = []
            b_obs_list = []
            exp_c_total = 0.0

            for ep in range(4):
                q_ep = queries[ep % len(queries)]
                if len(X_obs_list) == 0:
                    gr = ReusableGreenOperator2D3D(world.spec, 45, lambda X: np.zeros(len(X)), None)
                    pol = gr.solve_port_reduced(q_ep)["policy"]
                else:
                    km = KrigingWorldModel(np.vstack(X_obs_list), np.concatenate(q_obs_list), np.vstack(b_obs_list))
                    gr = ReusableGreenOperator2D3D(
                        world.spec, 45,
                        lambda X, _k=km: _k.predict_q(X, return_std=False)[0],
                        lambda X, _k=km: _k.predict_b(X, return_std=False),
                    )
                    if mode == "Greedy-Exploit-Traj":
                        pol = gr.solve_port_reduced(q_ep)["policy"]
                    else:
                        pts_c = gr.pts
                        in_b = np.all(np.abs(pts_c) <= 1.25, axis=1)
                        _, std_q = km.predict_q(pts_c[in_b], return_std=True)
                        if mode == "GlobalVar-Detour-Traj":
                            wp = pts_c[in_b][int(np.argmax(std_q))]
                        else:
                            occ = gr.compute_doob_sensitivity(q_ep)[in_b]
                            wp = pts_c[in_b][int(np.argmax(occ * std_q))]
                        # Two-stage reachable policy: steer to waypoint `wp`, then to `q_ep.goals[0]`!
                        q_wp = QueryTask("wp", (GoalBall(tuple(wp.tolist()), 0.0, 0.22),), q_ep.start_points)
                        pol_wp = gr.solve_port_reduced(q_wp)["policy"]
                        pol_gl = gr.solve_port_reduced(q_ep)["policy"]
                        pol = (pol_wp, wp, pol_gl)

                # Roll out 1 physical episode, sampling observations every 12 steps (~0.14s)
                x = np.array(q_ep.start_points[0], dtype=float)
                hit_wp = not isinstance(pol, tuple)
                ep_pts, ep_q, ep_b = [], [], []
                for step in range(420):
                    if np.linalg.norm(x - np.array(q_ep.goals[0].center)) <= q_ep.goals[0].radius:
                        break
                    if not hit_wp and np.linalg.norm(x - pol[1]) <= 0.24:
                        hit_wp = True
                    act_fn = pol if not isinstance(pol, tuple) else (pol[2] if hit_wp else pol[0])
                    u = act_fn(x[None, :])[0]
                    un = float(np.linalg.norm(u))
                    if un > 12.0:
                        u = u * (12.0 / un)
                    qt = float(world.q_total(x[None, :])[0])
                    bv = world.drift(x[None, :])[0]
                    exp_c_total += (qt + 0.5 * float(np.dot(u, u))) * dt
                    if step % 14 == 0:
                        ep_pts.append(x.copy())
                        ep_q.append(max(0.0, qt - world.spec.q0 + float(rng.normal(0.0, 0.40))))
                        ep_b.append(bv + rng.normal(0.0, 0.15, size=2))
                    x = reflect_into_box(x + (bv + u) * dt + world.spec.sigma * rng.normal(0.0, sqrt_dt, size=2), world.spec.half_width)

                if ep_pts:
                    X_obs_list.append(np.array(ep_pts))
                    q_obs_list.append(np.array(ep_q))
                    b_obs_list.append(np.array(ep_b))

            explore_costs[mode].append(exp_c_total / 4.0)
            km_f = KrigingWorldModel(np.vstack(X_obs_list), np.concatenate(q_obs_list), np.vstack(b_obs_list))
            fd_f = ClassicalFDSolver(
                world.spec, grid_n,
                lambda X, _k=km_f: _k.predict_q(X, return_std=False)[0],
                lambda X, _k=km_f: _k.predict_b(X, return_std=False),
            )
            dc = [simulate_closed_loop_crn(world, fd_f.solve_direct(q)["policy"], q, n_per_start=30, seed=6000 + qi)["mean_cost"]
                  for qi, q in enumerate(queries)]
            deploy_costs[mode].append(float(np.mean(dc)))

    dm, ci = paired_ci95(np.array(deploy_costs["Doob-Sensitivity-Detour-Traj"]) - np.array(deploy_costs["Greedy-Exploit-Traj"]))
    dm_gv, ci_gv = paired_ci95(np.array(deploy_costs["Doob-Sensitivity-Detour-Traj"]) - np.array(deploy_costs["GlobalVar-Detour-Traj"]))
    return {
        "n_maps": n_maps,
        "episodes_per_map": 4,
        "methods": {
            m: {
                "mean_explore_episode_cost": float(np.mean(explore_costs[m])),
                "mean_post_explore_deploy_cost": float(np.mean(deploy_costs[m])),
            }
            for m in modes
        },
        "doob_minus_greedy_deploy": {"mean": dm, "ci95": ci},
        "doob_minus_globalvar_deploy": {"mean": dm_gv, "ci95": ci_gv},
    }


def run_part2c_robust_hjb_bounds(n_maps: int = 8, grid_n: int = 51) -> dict:
    """Compares genuine nonlinear robust HJB bounds (`b_hat.grad V ± rho ||grad V||`)
    across N = 15, 30, 60 observations against high-res ground-truth V*(x).
    Reports BOTH pointwise empirical inclusion rate and simultaneous all-test-point inclusion rate.
    """
    budgets = [15, 30, 60]
    out = {}
    for n_p in budgets:
        pt_covs, sim_covs, widths, bellman_diffs = [], [], [], []
        for m_i in range(n_maps):
            map_seed = 1800 + m_i
            world, queries = generate_random_map(map_seed, dim=2, with_drift=True, n_queries=2)
            q = queries[0]
            ref = ClassicalFDSolver(world.spec, 81, world.q_hidden, world.drift).solve_direct(q)

            X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_p, seed=map_seed + n_p, include_drift=True)
            km = KrigingWorldModel(X_obs, q_obs, b_obs)

            rob = solve_nonlinear_robust_hjb_envelope_2d(
                world.spec,
                grid_n,
                q_mu_fn=lambda X, _k=km: _k.predict_q(X, return_std=True),
                b_mu_std_fn=lambda X, _k=km: _k.predict_b(X, return_std=True),
                query=q,
                beta_conf=2.5,
                n_iters=10,
            )
            # Evaluate on 64 interior test points outside goal
            rng = np.random.default_rng(map_seed + 9)
            X_eval = rng.uniform(-1.15, 1.15, size=(80, 2))
            X_eval = X_eval[np.linalg.norm(X_eval - np.array(q.goals[0].center)[None, :], axis=1) > q.goals[0].radius + 0.08][:64]
            v_true = ref["value_fn"](X_eval)
            v_lo = rob["val_lo_fn"](X_eval)
            v_hi = rob["val_hi_fn"](X_eval)
            inside = (v_true >= v_lo - 1e-6) & (v_true <= v_hi + 1e-6)
            pt_covs.append(float(np.mean(inside)))
            sim_covs.append(float(np.all(inside)))
            widths.append(float(np.mean(v_hi - v_lo)))
            bellman_diffs.append(rob["max_iter_diff"])

        out[f"N={n_p}"] = {
            "pointwise_empirical_coverage": float(np.mean(pt_covs)),
            "simultaneous_64pt_map_fraction": float(np.mean(sim_covs)),
            "mean_interval_width": float(np.mean(widths)),
            "max_robust_hjb_iter_diff": float(np.max(bellman_diffs)),
        }
    return out


def plot_battle2(p2a: dict, p2b: dict, p2c: dict, out_png: Path):
    fig, axes = plt.subplots(1, 3, figsize=(16.2, 4.7))

    # Panel 1: Point active probing across 10 maps
    names_a = ["Random", "Global-MaxVar", "Corridor-Heuristic", "Doob-Adjoint-Sensitivity", "Oracle-FD"]
    labels_a = ["Random\n(N=24)", "Global\nMax-Var", "Corridor\nHeuristic", "Doob Adjoint\n(Ours)", "GroundTruth\nReference"]
    vals_a = [p2a["methods"][m]["mean_deploy_cost"] for m in names_a]
    cols_a = ["#8c8c8c", "#ff7f0e", "#9467bd", "#1f77b4", "#2ca02c"]
    bars = axes[0].bar(np.arange(len(names_a)), vals_a, width=0.56, color=cols_a)
    axes[0].set_xticks(np.arange(len(names_a)))
    axes[0].set_xticklabels(labels_a, fontsize=8.5)
    axes[0].set_ylabel("Closed-Loop Deployment Cost (10 Maps)")
    axes[0].set_title("Active Point Probing (N0=8 → N=24, Same-GP FD)")
    axes[0].grid(True, axis="y", alpha=0.3)
    for b, v in zip(bars, vals_a):
        axes[0].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.08, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)
    axes[0].set_ylim(0, max(vals_a) * 1.2)

    # Panel 2: Reachable on-trajectory exploration (explore vs deploy cost)
    names_b = ["Greedy-Exploit-Traj", "GlobalVar-Detour-Traj", "Doob-Sensitivity-Detour-Traj"]
    labels_b = ["Greedy Exploit\n(4 Traj)", "Global-Var Detour\n(4 Traj)", "Doob Sensitivity\nDetour (4 Traj)"]
    x_b = np.arange(len(names_b))
    w = 0.34
    exp_v = [p2b["methods"][m]["mean_explore_episode_cost"] for m in names_b]
    dep_v = [p2b["methods"][m]["mean_post_explore_deploy_cost"] for m in names_b]
    axes[1].bar(x_b - w / 2, exp_v, width=w, color="#aec7e8", label="Exploration Episode Cost")
    b_dep = axes[1].bar(x_b + w / 2, dep_v, width=w, color="#1f77b4", label="Post-Explore Deploy Cost")
    for b, v in zip(b_dep, dep_v):
        axes[1].text(b.get_x() + b.get_width() / 2, b.get_height() + 0.08, f"{v:.2f}", ha="center", va="bottom", fontsize=8.5)
    axes[1].set_xticks(x_b)
    axes[1].set_xticklabels(labels_b, fontsize=8.5)
    axes[1].set_ylabel("Trajectory Cost (8 Maps)")
    axes[1].set_title("Reachable On-Trajectory Exploration (No Teleport)")
    axes[1].legend(fontsize=8.5)
    axes[1].grid(True, axis="y", alpha=0.3)

    # Panel 3: True Nonlinear Robust HJB Interval Width & Pointwise Coverage
    ns = [15, 30, 60]
    widths = [p2c[f"N={n}"]["mean_interval_width"] for n in ns]
    covs = [100.0 * p2c[f"N={n}"]["pointwise_empirical_coverage"] for n in ns]
    ax3 = axes[2]
    ax3.plot(ns, widths, "o-", color="#d62728", lw=2.2, label="Mean Robust HJB Width")
    ax3.set_xlabel("Observation Budget N")
    ax3.set_ylabel("Mean Interval Width [V_lo, V_hi]", color="#d62728")
    ax3.set_xticks(ns)
    ax3.grid(True, alpha=0.3)
    ax3_r = ax3.twinx()
    ax3_r.plot(ns, covs, "s--", color="#2ca02c", lw=2.0, label="Pointwise Coverage (%)")
    ax3_r.set_ylabel("Pointwise Empirical Inclusion (%)", color="#2ca02c")
    ax3_r.set_ylim(75, 103)
    ax3.set_title("Nonlinear Robust HJB Empirical Bounds (8 Maps)")

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Battle 2A: Sequential Point Active Probing (10 independent maps, N=8->24) ===")
    p2a = run_part2a_point_probing(n_maps=10, grid_n=61)
    for m, v in p2a["methods"].items():
        print(f"  {m:28s} | DeployCost={v['mean_deploy_cost']:.3f} | HazCost={v['mean_hazard_cost']:.3f} | Acq={v['mean_acq_ms']:.1f}ms")
    for k, v in p2a["paired_differences"].items():
        print(f"  Paired {k}: {v['mean']:+.3f} ± {v['ci95']:.3f}")

    print("\n=== Battle 2B: Reachable On-Trajectory Exploration (8 independent maps, 4 episodes) ===")
    p2b = run_part2b_reachable_trajectory_exploration(n_maps=8, grid_n=55)
    for m, v in p2b["methods"].items():
        print(f"  {m:30s} | ExploreEpCost={v['mean_explore_episode_cost']:.3f} | DeployCost={v['mean_post_explore_deploy_cost']:.3f}")
    print("  Doob minus Greedy deploy:", p2b["doob_minus_greedy_deploy"])
    print("  Doob minus GlobalVar deploy:", p2b["doob_minus_globalvar_deploy"])

    print("\n=== Battle 2C: Nonlinear Robust HJB Bounds (`b_hat.grad V ± rho ||grad V||`) ===")
    p2c = run_part2c_robust_hjb_bounds(n_maps=8, grid_n=51)
    for k, v in p2c.items():
        print(f"  {k}: PointCov={v['pointwise_empirical_coverage']*100:.1f}% | Sim64Cov={v['simultaneous_64pt_map_fraction']*100:.1f}% | Width={v['mean_interval_width']:.2f} | IterDiff={v['max_robust_hjb_iter_diff']:.2e}")

    out_dir = Path(__file__).resolve().parent
    res = {"point_probing": p2a, "reachable_trajectory_exploration": p2b, "nonlinear_robust_hjb_bounds": p2c}
    (out_dir / "battle2_active_and_robust_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_battle2(p2a, p2b, p2c, out_dir / "battle2_active_and_robust.png")
    print("Saved battle2_active_and_robust_results.json and battle2_active_and_robust.png")


if __name__ == "__main__":
    main()
