"""
Breakthrough B2 (v2): Fixing the Linear-UCB "Fake Perimeter Wall" Paradox!
Compares on a HARD blind-trap lethal benchmark (hidden narrow lethal mines that
initial passive probes miss!):
  1. Nominal Mean-1A (overconfident in blind spots -> crashes into hidden mines!)
  2. Naive Linear-UCB-1A (mu_q + 2.4*std_q -> creates fake walls in safe empty perimeter!)
  3. Exceedance-Risk-1A (mu_q + C_risk * P_GP(q > q_thresh) -> ZERO fake perimeter walls,
     sharp protective shield around suspected hazards!)
  4. Corridor-Gated Active + Exceedance-Risk-1A ("切线隔离"闭环: inspects ONLY the
     planned nominal corridor, places 2-3 targeted probes where corridor uncertainty
     threatens safety, then deploys Exceedance-Risk-1A!)
"""
from __future__ import annotations

import json
import os
import time
import numpy as np
from scipy.special import ndtr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from env_and_oracle import build_default_benchmark, HazardBlob, QuerySpec
from methods import SemigroupGreenSolver, KrigingEnvironmentModel
from test_breakthrough_b_safety import LethalObstacleEnv, trace_nominal_corridor


def exceedance_risk_q(km: KrigingEnvironmentModel, X: np.ndarray, q_thresh: float = 8.0, c_risk: float = 18.0) -> np.ndarray:
    """
    Exact Gaussian exceedance probability risk cost:
        q_eff(x) = max(0, mu_q(x)) + c_risk * P(q(x) > q_thresh)
    Unlike linear mu + beta*std, empty unexplored space (mu=0, std=2.5) has
    P(q > 8) = Phi(-3.2) = 0.0007 -> ZERO fake perimeter walls!
    """
    mu, std = km.predict_q(X)
    prob_danger = 1.0 - ndtr((q_thresh - mu) / np.maximum(std, 1e-6))
    return np.maximum(0.0, mu) + c_risk * prob_danger


def run_b2_v2():
    print(f"\n{'='*86}\nBREAKTHROUGH B2 (v2) — EXCEEDANCE-RISK & CORRIDOR-GATED ACTIVE SAFETY ON BLIND TRAPS\n{'='*86}")
    # Include a narrow sneaky lethal mine right on the natural detour corridor!
    lethal_centers = [
        np.array([0.0, 0.10]),
        np.array([0.22, -0.32]),
        np.array([-0.40, -0.18]),
        np.array([-0.25, 0.62]),  # sneaky mine on the upper detour!
        np.array([0.52, -0.10]),  # sneaky mine on the right detour!
    ]
    hazards = [HazardBlob(center=c, amplitude=18.0, width=0.17) for c in lethal_centers]
    env = LethalObstacleEnv(
        lethal_centers=lethal_centers,
        lethal_radius=0.16,
        sigma=0.28,
        q0=0.60,
        r_goal=0.14,
        hazards=hazards,
    )
    _, queries = build_default_benchmark(with_vortex=False)
    solver = SemigroupGreenSolver(env, grid_n=25, half_width=1.65)

    op_exact = solver.build_environment_operator(env.q_hidden)
    op_free = solver.build_environment_operator(lambda X: np.zeros(len(np.atleast_2d(X))))

    print("--- REFERENCE ---")
    ref = {}
    for lbl, op in [("Exact-Green-1A (Oracle)", op_exact), ("Pure-Free-Green", op_free)]:
        cs, crs, srs = [], [], []
        for q in queries:
            m = env.simulate_safe_rollouts(solver.solve_query(op, q)["policy"], q, n_per_start=50, seed=100)
            cs.append(m["mean_cost"]); crs.append(m["crash_rate"]); srs.append(m["safe_reach_rate"])
        ref[lbl] = {"cost": float(np.mean(cs)), "crash": float(np.mean(crs)), "reach": float(np.mean(srs))}
        print(f"  {lbl:38s} | AvgCost={np.mean(cs):5.2f} | CrashRate={100*np.mean(crs):5.1f}% | SafeReach={100*np.mean(srs):5.1f}%")

    # Very sparse initial exploration (N0=16 random probes -> misses several narrow mines!)
    n_init = 16
    n_passive_big = 28
    seeds = (0, 1, 2, 3, 4)

    names = [
        f"Mean-1A (Passive N={n_init})",
        f"Mean-1A (Passive N={n_passive_big})",
        f"Naive-Linear-UCB (Passive N={n_init})",
        f"Exceedance-Risk-1A (Passive N={n_init})",
        f"Corridor-Gated-1A (N0={n_init}+active)",
    ]
    agg = {m: {"cost": [], "crash": [], "reach": [], "probes": []} for m in names}
    vis = None

    for sd in seeds:
        rng = np.random.default_rng(900 + 29 * sd)
        X16 = rng.uniform(-1.05, 1.05, size=(n_init, 2))
        q16 = np.maximum(0.0, env.q_hidden(X16) + rng.normal(0.0, 0.5, size=n_init))
        X28 = np.vstack([X16, rng.uniform(-1.05, 1.05, size=(n_passive_big - n_init, 2))])
        q28 = np.concatenate([q16, np.maximum(0.0, env.q_hidden(X28[n_init:]) + rng.normal(0.0, 0.5, size=n_passive_big - n_init))])

        km16 = KrigingEnvironmentModel(X16, q16)
        km28 = KrigingEnvironmentModel(X28, q28)

        op_m16 = solver.build_environment_operator(lambda X, _k=km16: np.maximum(0.0, _k.predict_q(X)[0]))
        op_m28 = solver.build_environment_operator(lambda X, _k=km28: np.maximum(0.0, _k.predict_q(X)[0]))
        op_lu16 = solver.build_environment_operator(lambda X, _k=km16: np.maximum(0.0, _k.predict_q(X)[0] + 2.4 * _k.predict_q(X)[1]))
        op_er16 = solver.build_environment_operator(lambda X, _k=km16: exceedance_risk_q(_k, X))

        # Corridor-Gated Active + Exceedance Risk sequentially across Q1..Q4
        Xg, qg = X16.copy(), q16.copy()
        km_g = KrigingEnvironmentModel(Xg, qg)
        fk = km_g.get_fitted_kernels()

        for qi, q in enumerate(queries):
            for lbl, op, npr in [
                (f"Mean-1A (Passive N={n_init})", op_m16, n_init),
                (f"Mean-1A (Passive N={n_passive_big})", op_m28, n_passive_big),
                (f"Naive-Linear-UCB (Passive N={n_init})", op_lu16, n_init),
                (f"Exceedance-Risk-1A (Passive N={n_init})", op_er16, n_init),
            ]:
                res = solver.solve_query(op, q)
                m = env.simulate_safe_rollouts(res["policy"], q, n_per_start=45, seed=400 + sd)
                agg[lbl]["cost"].append(m["mean_cost"]); agg[lbl]["crash"].append(m["crash_rate"])
                agg[lbl]["reach"].append(m["safe_reach_rate"]); agg[lbl]["probes"].append(npr)

            # Corridor-gated active probing: inspect ONLY planned corridor, probe highest-std blind spot!
            for _ in range(3):
                op_cur = solver.build_environment_operator(lambda X, _k=km_g: exceedance_risk_q(_k, X))
                res_cur = solver.solve_query(op_cur, q)
                corr = trace_nominal_corridor(res_cur["policy"], q, env.r_goal)
                _, std_c = km_g.predict_q(corr)
                min_d = np.min(np.linalg.norm(corr[:, None, :] - Xg[None, :, :], axis=2), axis=1)
                gated = np.where(min_d > 0.14, std_c, 0.0)
                bi = int(np.argmax(gated))
                if gated[bi] <= 2.2:
                    break
                x_new = corr[bi : bi + 1]
                q_new = np.maximum(0.0, env.q_hidden(x_new) + rng.normal(0.0, 0.5, size=1))
                Xg = np.vstack([Xg, x_new])
                qg = np.concatenate([qg, q_new])
                km_g = KrigingEnvironmentModel(Xg, qg, None, fixed_kernels=None if len(Xg) % 4 == 0 else fk)
                if len(Xg) % 4 == 0:
                    fk = km_g.get_fitted_kernels()

            op_final = solver.build_environment_operator(lambda X, _k=km_g: exceedance_risk_q(_k, X))
            res_final = solver.solve_query(op_final, q)
            mg = env.simulate_safe_rollouts(res_final["policy"], q, n_per_start=45, seed=400 + sd)
            lbl_g = f"Corridor-Gated-1A (N0={n_init}+active)"
            agg[lbl_g]["cost"].append(mg["mean_cost"]); agg[lbl_g]["crash"].append(mg["crash_rate"])
            agg[lbl_g]["reach"].append(mg["safe_reach_rate"]); agg[lbl_g]["probes"].append(len(Xg))

            if sd == 0 and qi == 0:
                vis = {
                    "env": env, "query": q, "X16": X16, "Xg": Xg.copy(),
                    "pol_mean": solver.solve_query(op_m16, q)["policy"],
                    "pol_lu": solver.solve_query(op_lu16, q)["policy"],
                    "pol_gate": res_final["policy"],
                    "pol_oracle": solver.solve_query(op_exact, q)["policy"],
                }

    out = {"reference": ref, "methods": {}}
    print(f"\n--- BLIND-TRAP LETHAL COMPARISON ACROSS Q1-Q4 ({len(seeds)} seeds) ---")
    for lbl in names:
        mc = float(np.mean(agg[lbl]["cost"]))
        mcr = float(np.mean(agg[lbl]["crash"]))
        msr = float(np.mean(agg[lbl]["reach"]))
        mpr = float(np.mean(agg[lbl]["probes"]))
        out["methods"][lbl] = {"cost": mc, "crash": mcr, "reach": msr, "avg_probes": mpr}
        print(f"  {lbl:38s} | Probes={mpr:4.1f} | AvgCost={mc:5.2f} | CrashRate={100*mcr:5.1f}% | SafeReach={100*msr:5.1f}%")

    if vis is not None:
        out_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breakthrough_b2_v2_safety.png")
        fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.9), dpi=130)
        gx = np.linspace(-1.1, 1.1, 70)
        XX, YY = np.meshgrid(gx, gx, indexing="ij")
        qh = env.q_hidden(np.stack([XX.ravel(), YY.ravel()], axis=1)).reshape(XX.shape)
        q0 = vis["query"]
        for ax, title, pol, show_active in [
            (axes[0], "Mean-1A (N=16): Hits Undiscovered Mines", vis["pol_mean"], False),
            (axes[1], "Naive Linear-UCB (N=16): Fake Perimeter Wall!", vis["pol_lu"], False),
            (axes[2], f"Corridor-Gated Exceedance-1A (N={len(vis['Xg'])})", vis["pol_gate"], True),
        ]:
            ax.contourf(XX, YY, qh, levels=18, cmap="Reds", alpha=0.65)
            for c in env.lethal_centers:
                ax.add_patch(plt.Circle(c, env.lethal_radius, facecolor="darkred", edgecolor="black", alpha=0.55, lw=1.6, zorder=4))
            for gc, _ in q0.goals:
                ax.add_patch(plt.Circle(gc, env.r_goal, facecolor="none", edgecolor="lime", lw=2.2, zorder=6))
                ax.scatter([gc[0]], [gc[1]], c="green", s=65, marker="*", zorder=7)
            ax.scatter(vis["X16"][:, 0], vis["X16"][:, 1], c="black", s=22, marker="x", label="Init N=16", zorder=6)
            if show_active and len(vis["Xg"]) > n_init:
                Xa = vis["Xg"][n_init:]
                ax.scatter(Xa[:, 0], Xa[:, 1], c="gold", edgecolor="black", s=65, marker="D", label=f"Active (+{len(Xa)})", zorder=8)
            for st in q0.start_points:
                for p_fn, col, ls_s in [(vis["pol_oracle"], "blue", "--"), (pol, "cyan", "-")]:
                    path = [st.copy()]
                    x = st.copy()
                    for _ in range(250):
                        if env.is_lethal(x[None, :])[0] or np.linalg.norm(x - q0.goals[0][0]) <= env.r_goal:
                            break
                        u = p_fn(x[None, :])[0]
                        un = np.linalg.norm(u)
                        if un > 6.0:
                            u = u * (6.0 / un)
                        x = np.clip(x + u * 0.015, -1.25, 1.25)
                        path.append(x.copy())
                    P = np.array(path)
                    ax.plot(P[:, 0], P[:, 1], color=col, linestyle=ls_s, lw=2.1, zorder=7)
            ax.set_xlim(-1.1, 1.1); ax.set_ylim(-1.1, 1.1)
            ax.set_title(title, fontsize=9.5)
            ax.legend(loc="lower right", fontsize=7.5)
        plt.tight_layout()
        plt.savefig(out_png)
        plt.close(fig)
        print(f"Saved B2-v2 plot to {out_png}")

    out_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breakthrough_b2_v2_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    t0 = time.perf_counter()
    run_b2_v2()
    print(f"\nBreakthrough B2 (v2) finished in {time.perf_counter() - t0:.1f}s.")
