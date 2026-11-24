"""
Kill-Test Runner for Direction 1A:
  Strictly Positive Semigroup Green's Operator + Kriging Residual + Elliptic Uncertainty Gating.
"""
from __future__ import annotations

import json
import os
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from env_and_oracle import build_default_benchmark, ExactFDPDEOracle, StochasticControlEnv, QuerySpec
from methods import (
    SemigroupGreenSolver,
    KrigingEnvironmentModel,
    GreenKriging1APlanner,
    fit_ordinary_kriging_V,
    fit_pinn_hjb,
)


def sample_observations(
    env: StochasticControlEnv,
    n_samples: int,
    seed: int,
    q_noise_std: float = 0.5,
    b_noise_std: float = 0.2,
    include_drift: bool = False,
):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1.05, 1.05, size=(n_samples, 2))
    q_obs = np.maximum(0.0, env.q_hidden(X) + rng.normal(0.0, q_noise_std, size=n_samples))
    b_obs = None
    if include_drift:
        b_obs = env.drift(X) + rng.normal(0.0, b_noise_std, size=(n_samples, 2))
    return X, q_obs, b_obs


def active_envelope_sensing(
    env: StochasticControlEnv,
    solver: SemigroupGreenSolver,
    queries: list[QuerySpec],
    n_init: int,
    n_total: int,
    seed: int,
    q_noise_std: float = 0.5,
    b_noise_std: float = 0.2,
    include_drift: bool = False,
):
    """
    Uncertainty-Gated Active Exploration ("切线隔离" + 主动补采):
    Starts with n_init random probes; adds remaining probes where the PDE value-envelope
    gap (V_upper - V_lower) x hazard posterior std is largest (re-optimizing GP kernels
    every 6 probes for speed).
    """
    rng = np.random.default_rng(seed)
    X_obs, q_obs, b_obs = sample_observations(env, n_init, seed, q_noise_std, b_noise_std, include_drift)

    gx = np.linspace(-1.0, 1.0, 21)
    XX, YY = np.meshgrid(gx, gx, indexing="ij")
    pool = np.stack([XX.ravel(), YY.ravel()], axis=1)

    fitted_kernels = None
    for step in range(n_total - n_init):
        reopt = (step % 6 == 0)
        km = KrigingEnvironmentModel(X_obs, q_obs, b_obs, fixed_kernels=None if reopt else fitted_kernels)
        if reopt:
            fitted_kernels = km.get_fitted_kernels()

        planner = GreenKriging1APlanner(solver, km, beta_ucb=1.65)
        gk = planner.solve(queries[0])  # mission-guided on training query Q1
        V_hi = gk["ucb"]["value_fn"](pool)
        V_lo = gk["lcb"]["value_fn"](pool)
        _, std_q = km.predict_q(pool)
        gap = np.maximum(0.0, V_hi - V_lo)
        min_d = np.min(np.linalg.norm(pool[:, None, :] - X_obs[None, :, :], axis=2), axis=1)
        score = gap * (0.2 + std_q) * (min_d > 0.14)
        best_idx = int(np.argmax(score))
        x_new = pool[best_idx : best_idx + 1]
        q_new = np.maximum(0.0, env.q_hidden(x_new) + rng.normal(0.0, q_noise_std, size=1))
        X_obs = np.vstack([X_obs, x_new])
        q_obs = np.concatenate([q_obs, q_new])
        if include_drift:
            b_new = env.drift(x_new) + rng.normal(0.0, b_noise_std, size=(1, 2))
            b_obs = np.vstack([b_obs, b_new])

    return X_obs, q_obs, b_obs


def eval_envelope_coverage(oracle_res: dict, gk_res: dict, query: QuerySpec, r_goal: float) -> dict:
    """Measure empirical soundness of V_lower(x) <= V_true*(x) <= V_upper(x) outside goal disks."""
    gx = np.linspace(-0.95, 0.95, 25)
    XX, YY = np.meshgrid(gx, gx, indexing="ij")
    pts = np.stack([XX.ravel(), YY.ravel()], axis=1)
    mask = np.ones(len(pts), dtype=bool)
    for gc, _ in query.goals:
        mask &= np.linalg.norm(pts - gc[None, :], axis=1) > (r_goal + 0.08)
    pts = pts[mask]

    v_true = oracle_res["value_fn"](pts)
    v_lo = gk_res["lcb"]["value_fn"](pts)
    v_hi = gk_res["ucb"]["value_fn"](pts)
    v_mean = gk_res["mean"]["value_fn"](pts)
    inside = (v_true >= v_lo - 0.08) & (v_true <= v_hi + 0.08)
    return {
        "coverage": float(np.mean(inside)),
        "mean_width": float(np.mean(np.maximum(0.0, v_hi - v_lo))),
        "mae_vs_oracle": float(np.mean(np.abs(v_mean - v_true))),
    }


def run_regime(regime_name: str, with_vortex: bool, sample_budgets=(15, 30, 60), seeds=(0, 1, 2)):
    print(f"\n{'='*84}\nREGIME: {regime_name} (with_vortex={with_vortex})\n{'='*84}")
    env, queries = build_default_benchmark(with_vortex=with_vortex)
    oracle = ExactFDPDEOracle(env, grid_n=101, half_width=2.0)
    green_solver = SemigroupGreenSolver(env, grid_n=25, half_width=1.65)

    oracle_solutions = {}
    oracle_metrics = {}
    exact_green_metrics = {}
    free_metrics = {}

    # Build exact-knowledge and free-space environment operators ONCE!
    drift_true = env.drift if with_vortex else None
    op_exact = green_solver.build_environment_operator(env.q_hidden, drift_fn=drift_true)
    op_free = green_solver.build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))), drift_fn=None)

    print(f"\n--- TEST 0: MATH SANITY (Exact-Knowledge Semigroup Green vs Exact FD PDE Oracle, M={green_solver.M}) ---")
    for q in queries:
        ores = oracle.solve(q)
        oracle_solutions[q.name] = ores
        om = env.simulate_rollouts(ores["policy"], q, n_per_start=50, seed=100)
        oracle_metrics[q.name] = om

        gres = green_solver.solve_query(op_exact, q)
        gm = env.simulate_rollouts(gres["policy"], q, n_per_start=50, seed=100)
        exact_green_metrics[q.name] = gm

        fres = green_solver.solve_query(op_free, q)
        fm = env.simulate_rollouts(fres["policy"], q, n_per_start=50, seed=100)
        free_metrics[q.name] = fm

        gap_pct = 100.0 * (gm["mean_cost"] - om["mean_cost"]) / max(om["mean_cost"], 1e-6)
        print(
            f"  {q.name:22s} | Oracle={om['mean_cost']:.3f} | Exact-Green-1A={gm['mean_cost']:.3f} "
            f"({gap_pct:+5.1f}%, {gres['solve_ms']:.2f}ms) | Pure-Free-Green={fm['mean_cost']:.3f} (haz={fm['mean_hazard']:.2f})"
        )

    results = {
        "regime": regime_name,
        "with_vortex": with_vortex,
        "oracle": oracle_metrics,
        "exact_green": exact_green_metrics,
        "pure_free_green": free_metrics,
        "by_budget": {},
    }

    for N in sample_budgets:
        print(f"\n--- BUDGET N={N} NOISY SAMPLES (averaged over {len(seeds)} seeds) ---")
        method_names = [
            "Ordinary-Kriging-V",
            "PINN-HJB (Q1-only)",
            "PINN-HJB (retrained/query)",
            "Green-Kriging-1A (Mean)",
            "Green-Kriging-1A (UCB-Safe)",
            "Green-Kriging-1A (Active-UCB)",
        ]
        agg = {
            m: {q.name: {"cost": [], "hazard": [], "reach": [], "ms": []} for q in queries}
            for m in method_names
        }
        cov_agg = {q.name: {"coverage": [], "width": [], "mae": []} for q in queries}

        for sd in seeds:
            X_obs, q_obs, b_obs = sample_observations(env, N, seed=1000 + 17 * sd + N, include_drift=with_vortex)
            krig_passive = KrigingEnvironmentModel(X_obs, q_obs, b_obs)
            planner_passive = GreenKriging1APlanner(green_solver, krig_passive, beta_ucb=1.65)

            n_init = max(6, N // 2)
            Xa, qa, ba = active_envelope_sensing(
                env, green_solver, queries, n_init=n_init, n_total=N,
                seed=1000 + 17 * sd + N, include_drift=with_vortex,
            )
            krig_active = KrigingEnvironmentModel(Xa, qa, ba)
            planner_active = GreenKriging1APlanner(green_solver, krig_active, beta_ucb=1.65)

            rng_v = np.random.default_rng(2000 + sd)
            V_q1_noisy = oracle_solutions[queries[0].name]["value_fn"](X_obs) + rng_v.normal(0.0, 0.10, size=N)
            ok_v = fit_ordinary_kriging_V(X_obs, V_q1_noisy)

            pinn_q1 = fit_pinn_hjb(env, krig_passive, queries[0], n_colloc=400, epochs=450, seed=sd)

            for qi, q in enumerate(queries):
                # 1. Ordinary-Kriging-V
                m_ok = env.simulate_rollouts(ok_v["policy"], q, n_per_start=40, seed=300 + sd)
                agg["Ordinary-Kriging-V"][q.name]["cost"].append(m_ok["mean_cost"])
                agg["Ordinary-Kriging-V"][q.name]["hazard"].append(m_ok["mean_hazard"])
                agg["Ordinary-Kriging-V"][q.name]["reach"].append(m_ok["reach_rate"])
                agg["Ordinary-Kriging-V"][q.name]["ms"].append(ok_v["solve_ms"] if qi == 0 else 0.0)

                # 2. PINN-HJB (Q1 only)
                m_p1 = env.simulate_rollouts(pinn_q1["policy"], q, n_per_start=40, seed=300 + sd)
                agg["PINN-HJB (Q1-only)"][q.name]["cost"].append(m_p1["mean_cost"])
                agg["PINN-HJB (Q1-only)"][q.name]["hazard"].append(m_p1["mean_hazard"])
                agg["PINN-HJB (Q1-only)"][q.name]["reach"].append(m_p1["reach_rate"])
                agg["PINN-HJB (Q1-only)"][q.name]["ms"].append(pinn_q1["solve_ms"] if qi == 0 else 0.0)

                # 3. PINN-HJB retrained per query (all queries at N=30, Q1 at all N)
                pinn_q = pinn_q1 if qi == 0 else (
                    fit_pinn_hjb(env, krig_passive, q, n_colloc=400, epochs=450, seed=sd + 10 * qi) if N == 30 else None
                )
                if pinn_q is not None:
                    m_pr = env.simulate_rollouts(pinn_q["policy"], q, n_per_start=40, seed=300 + sd)
                    agg["PINN-HJB (retrained/query)"][q.name]["cost"].append(m_pr["mean_cost"])
                    agg["PINN-HJB (retrained/query)"][q.name]["hazard"].append(m_pr["mean_hazard"])
                    agg["PINN-HJB (retrained/query)"][q.name]["reach"].append(m_pr["reach_rate"])
                    agg["PINN-HJB (retrained/query)"][q.name]["ms"].append(pinn_q["solve_ms"])

                # 4 & 5. Green-Kriging-1A (Passive: Mean & UCB-Safe)
                gk_p = planner_passive.solve(q)
                m_gm = env.simulate_rollouts(gk_p["mean"]["policy"], q, n_per_start=40, seed=300 + sd)
                agg["Green-Kriging-1A (Mean)"][q.name]["cost"].append(m_gm["mean_cost"])
                agg["Green-Kriging-1A (Mean)"][q.name]["hazard"].append(m_gm["mean_hazard"])
                agg["Green-Kriging-1A (Mean)"][q.name]["reach"].append(m_gm["reach_rate"])
                agg["Green-Kriging-1A (Mean)"][q.name]["ms"].append(gk_p["solve_ms"])

                m_gu = env.simulate_rollouts(gk_p["ucb"]["policy"], q, n_per_start=40, seed=300 + sd)
                agg["Green-Kriging-1A (UCB-Safe)"][q.name]["cost"].append(m_gu["mean_cost"])
                agg["Green-Kriging-1A (UCB-Safe)"][q.name]["hazard"].append(m_gu["mean_hazard"])
                agg["Green-Kriging-1A (UCB-Safe)"][q.name]["reach"].append(m_gu["reach_rate"])
                agg["Green-Kriging-1A (UCB-Safe)"][q.name]["ms"].append(gk_p["envelope_ms"])

                cov = eval_envelope_coverage(oracle_solutions[q.name], gk_p, q, env.r_goal)
                cov_agg[q.name]["coverage"].append(cov["coverage"])
                cov_agg[q.name]["width"].append(cov["mean_width"])
                cov_agg[q.name]["mae"].append(cov["mae_vs_oracle"])

                # 6. Green-Kriging-1A (Active Envelope-Gap Sensing + UCB)
                gk_a = planner_active.solve(q)
                m_ga = env.simulate_rollouts(gk_a["ucb"]["policy"], q, n_per_start=40, seed=300 + sd)
                agg["Green-Kriging-1A (Active-UCB)"][q.name]["cost"].append(m_ga["mean_cost"])
                agg["Green-Kriging-1A (Active-UCB)"][q.name]["hazard"].append(m_ga["mean_hazard"])
                agg["Green-Kriging-1A (Active-UCB)"][q.name]["reach"].append(m_ga["reach_rate"])
                agg["Green-Kriging-1A (Active-UCB)"][q.name]["ms"].append(gk_a["envelope_ms"])

        summary_N = {}
        header = f"  {'Method':30s} | " + " | ".join(f"{q.name[:12]:12s}" for q in queries) + " | AvgCost | Query(ms)"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for m_name in method_names:
            qdict = agg[m_name]
            costs_q, ms_q, cells = [], [], []
            summary_N[m_name] = {}
            for q in queries:
                arr = qdict[q.name]["cost"]
                if len(arr) == 0:
                    cells.append(f"{'n/a':>12s}")
                    continue
                mc = float(np.mean(arr))
                mr = float(np.mean(qdict[q.name]["reach"]))
                mh = float(np.mean(qdict[q.name]["hazard"]))
                mm = float(np.mean(qdict[q.name]["ms"]))
                costs_q.append(mc)
                ms_q.append(mm)
                cells.append(f"{mc:5.2f}({int(round(100*mr)):3d}%)")
                summary_N[m_name][q.name] = {"cost": mc, "hazard": mh, "reach": mr, "ms": mm}
            avg_c = float(np.mean(costs_q)) if costs_q else float("nan")
            avg_ms = float(np.mean(ms_q)) if ms_q else float("nan")
            print(f"  {m_name:30s} | " + " | ".join(cells) + f" | {avg_c:7.3f} | {avg_ms:8.2f}")

        print("  Elliptic Envelope Coverage (V_lo <= V* <= V_hi):")
        cov_summary = {}
        for q in queries:
            c_m = float(np.mean(cov_agg[q.name]["coverage"]))
            w_m = float(np.mean(cov_agg[q.name]["width"]))
            e_m = float(np.mean(cov_agg[q.name]["mae"]))
            cov_summary[q.name] = {"coverage": c_m, "mean_width": w_m, "mae": e_m}
            print(f"    {q.name:22s}: coverage={100*c_m:5.1f}%, mean_width={w_m:.3f}, MAE(V_mean,V*)={e_m:.3f}")
        results["by_budget"][str(N)] = {"methods": summary_N, "envelope": cov_summary}

    return results, env, queries, oracle_solutions, green_solver


def make_visual_plot(env, queries, oracle_solutions, solver: SemigroupGreenSolver, out_png: str):
    X_obs, q_obs, _ = sample_observations(env, 30, seed=1030, include_drift=False)
    km = KrigingEnvironmentModel(X_obs, q_obs, None)
    planner = GreenKriging1APlanner(solver, km, beta_ucb=1.65)
    op_free = solver.build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))), drift_fn=None)

    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.6), dpi=130)
    gx = np.linspace(-1.1, 1.1, 65)
    XX, YY = np.meshgrid(gx, gx, indexing="ij")
    grid_pts = np.stack([XX.ravel(), YY.ravel()], axis=1)

    for row, q in enumerate([queries[0], queries[2]]):
        gk = planner.solve(q)
        free_res = solver.solve_query(op_free, q)
        qh_grid = (env.q_hidden(grid_pts) + env.q_dynamic(grid_pts, q.extra_hazards)).reshape(XX.shape)
        V_or = oracle_solutions[q.name]["value_fn"](grid_pts).reshape(XX.shape)
        V_gk = gk["ucb"]["value_fn"](grid_pts).reshape(XX.shape)
        V_gap = np.maximum(0.0, gk["ucb"]["value_fn"](grid_pts) - gk["lcb"]["value_fn"](grid_pts)).reshape(XX.shape)

        ax = axes[row, 0]
        ax.contourf(XX, YY, qh_grid, levels=20, cmap="Reds", alpha=0.82)
        ax.scatter(X_obs[:, 0], X_obs[:, 1], c="black", s=18, marker="x", label="N=30 probes", zorder=5)
        for gc, _ in q.goals:
            circ = plt.Circle(gc, env.r_goal, color="lime", fill=False, lw=2.2, zorder=6)
            ax.add_patch(circ)
            ax.scatter([gc[0]], [gc[1]], c="green", s=70, marker="*", zorder=7)

        for st in q.start_points[:3]:
            for pol, col, ls_style, lbl in [
                (free_res["policy"], "dimgray", "--", "Pure-Free-Green"),
                (oracle_solutions[q.name]["policy"], "blue", "-", "Oracle-PDE"),
                (gk["ucb"]["policy"], "cyan", "-", "Green-Kriging-1A (UCB)"),
            ]:
                path = [st.copy()]
                x = st.copy()
                for _ in range(260):
                    if min(np.linalg.norm(x - gc) for gc, _ in q.goals) <= env.r_goal:
                        break
                    u = pol(x[None, :])[0]
                    un = np.linalg.norm(u)
                    if un > 6.0:
                        u = u * (6.0 / un)
                    x = np.clip(x + u * 0.015, -1.3, 1.3)
                    path.append(x.copy())
                P = np.array(path)
                ax.plot(P[:, 0], P[:, 1], color=col, linestyle=ls_style, lw=2.1, label=lbl if np.allclose(st, q.start_points[0]) else None)
        ax.set_title(f"{q.name}: Closed-Loop Mean Paths (N=30)")
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        if row == 0:
            ax.legend(loc="lower right", fontsize=7.5)

        ax2 = axes[row, 1]
        im2 = ax2.contourf(XX, YY, V_gk, levels=18, cmap="viridis")
        ax2.contour(XX, YY, V_or, levels=12, colors="white", linewidths=0.85, alpha=0.8)
        plt.colorbar(im2, ax=ax2, fraction=0.046)
        ax2.set_title(f"{q.name}: V_1A-UCB (fill) vs V_Oracle (white)")

        ax3 = axes[row, 2]
        im3 = ax3.contourf(XX, YY, V_gap, levels=18, cmap="magma")
        ax3.scatter(X_obs[:, 0], X_obs[:, 1], c="cyan", s=16, marker="x")
        plt.colorbar(im3, ax=ax3, fraction=0.046)
        ax3.set_title(f"{q.name}: Elliptic Envelope Gap (V_hi - V_lo)")

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close(fig)


if __name__ == "__main__":
    t_start = time.perf_counter()
    res1, env1, qs1, or1, gs1 = run_regime("Regime1_UnknownHazards", with_vortex=False, sample_budgets=(15, 30, 60), seeds=(0, 1, 2))
    res2, _, _, _, _ = run_regime("Regime2_UnknownHazards_Plus_VortexDrift", with_vortex=True, sample_budgets=(15, 30, 60), seeds=(0, 1, 2))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "kill_test_results.json"), "w", encoding="utf-8") as f:
        json.dump({"regime1": res1, "regime2": res2}, f, indent=2)

    png_path = os.path.join(out_dir, "kill_test_fields.png")
    make_visual_plot(env1, qs1, or1, gs1, png_path)
    print(f"\nAll tests completed in {time.perf_counter() - t_start:.1f}s. Saved results + plot to {out_dir}")
