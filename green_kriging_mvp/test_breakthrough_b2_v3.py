"""
Breakthrough B2 (v3): Separating Uncertainty-Gated Corridor Exploration from Control!
Key discovery from B2-v2:
  Adding GP posterior std directly to running cost everywhere creates a "fake perimeter wall"
  (dark-room phobia) that pushes the agent INTO sampled hazards.
Clean principled fix:
  1. Use GP uncertainty STRICTLY along the planned nominal corridor to place targeted active
     probes (discovering blind traps on the mission corridor while ignoring irrelevant map regions!).
  2. For control execution, enforce hard-obstacle Dirichlet masking (Z=0 where mu_q >= q_lethal)
     + nominal Kriging hazard mu_q (ZERO fake perimeter wall in safe empty space!).
"""
from __future__ import annotations

import json
import os
import time
import numpy as np
from env_and_oracle import build_default_benchmark, HazardBlob
from methods import SemigroupGreenSolver, KrigingEnvironmentModel
from test_breakthrough_b_safety import LethalObstacleEnv, trace_nominal_corridor


def solve_with_hard_mask(solver: SemigroupGreenSolver, q_fn, query, lethal_q_thresh: float = 9.0):
    """Hard Dirichlet absorbing barrier (Z = 0) wherever estimated q >= lethal_q_thresh."""
    def q_hard(X):
        qv = np.maximum(0.0, np.asarray(q_fn(X), dtype=float))
        # Very high killing rate approximates Dirichlet Z = 0 inside predicted lethal core
        return np.where(qv >= lethal_q_thresh, qv + 60.0, qv)
    op = solver.build_environment_operator(q_hard)
    return solver.solve_query(op, query)


def run_b2_v3():
    print(f"\n{'='*86}\nBREAKTHROUGH B2 (v3) — CORRIDOR-GATED ACTIVE PROBING + HARD-MASK 1A (ZERO FAKE WALL)\n{'='*86}")
    lethal_centers = [
        np.array([0.0, 0.10]),
        np.array([0.22, -0.32]),
        np.array([-0.40, -0.18]),
        np.array([-0.25, 0.62]),
        np.array([0.52, -0.10]),
    ]
    hazards = [HazardBlob(center=c, amplitude=18.0, width=0.17) for c in lethal_centers]
    env = LethalObstacleEnv(
        lethal_centers=lethal_centers, lethal_radius=0.16,
        sigma=0.28, q0=0.60, r_goal=0.14, hazards=hazards,
    )
    _, queries = build_default_benchmark(with_vortex=False)
    solver = SemigroupGreenSolver(env, grid_n=25, half_width=1.65)

    # Reference with true hazard + hard mask
    cs_o, cr_o, sr_o = [], [], []
    for q in queries:
        res = solve_with_hard_mask(solver, env.q_hidden, q, lethal_q_thresh=9.0)
        m = env.simulate_safe_rollouts(res["policy"], q, n_per_start=50, seed=100)
        cs_o.append(m["mean_cost"]); cr_o.append(m["crash_rate"]); sr_o.append(m["safe_reach_rate"])
    print(f"  {'Exact-HardMask-1A (Oracle)':42s} | AvgCost={np.mean(cs_o):5.2f} | CrashRate={100*np.mean(cr_o):5.1f}% | SafeReach={100*np.mean(sr_o):5.1f}%")

    n_init = 16
    n_passive_big = 28
    seeds = (0, 1, 2, 3, 4)
    names = [
        f"Mean-1A (Passive N={n_init})",
        f"HardMask-1A (Passive N={n_init})",
        f"HardMask-1A (Passive N={n_passive_big})",
        f"Corridor-Gated Active + HardMask-1A",
    ]
    agg = {m: {"cost": [], "crash": [], "reach": [], "probes": []} for m in names}

    for sd in seeds:
        rng = np.random.default_rng(900 + 29 * sd)
        X16 = rng.uniform(-1.05, 1.05, size=(n_init, 2))
        q16 = np.maximum(0.0, env.q_hidden(X16) + rng.normal(0.0, 0.5, size=n_init))
        X28 = np.vstack([X16, rng.uniform(-1.05, 1.05, size=(n_passive_big - n_init, 2))])
        q28 = np.concatenate([q16, np.maximum(0.0, env.q_hidden(X28[n_init:]) + rng.normal(0.0, 0.5, size=n_passive_big - n_init))])

        km16 = KrigingEnvironmentModel(X16, q16)
        km28 = KrigingEnvironmentModel(X28, q28)
        op_m16 = solver.build_environment_operator(lambda X, _k=km16: np.maximum(0.0, _k.predict_q(X)[0]))

        Xg, qg = X16.copy(), q16.copy()
        km_g = KrigingEnvironmentModel(Xg, qg)
        fk = km_g.get_fitted_kernels()

        for q in queries:
            # 1. Soft Mean N=16
            m1 = env.simulate_safe_rollouts(solver.solve_query(op_m16, q)["policy"], q, n_per_start=45, seed=400 + sd)
            agg[names[0]]["cost"].append(m1["mean_cost"]); agg[names[0]]["crash"].append(m1["crash_rate"])
            agg[names[0]]["reach"].append(m1["safe_reach_rate"]); agg[names[0]]["probes"].append(n_init)

            # 2. HardMask N=16
            r2 = solve_with_hard_mask(solver, lambda X, _k=km16: _k.predict_q(X)[0], q)
            m2 = env.simulate_safe_rollouts(r2["policy"], q, n_per_start=45, seed=400 + sd)
            agg[names[1]]["cost"].append(m2["mean_cost"]); agg[names[1]]["crash"].append(m2["crash_rate"])
            agg[names[1]]["reach"].append(m2["safe_reach_rate"]); agg[names[1]]["probes"].append(n_init)

            # 3. HardMask N=28
            r3 = solve_with_hard_mask(solver, lambda X, _k=km28: _k.predict_q(X)[0], q)
            m3 = env.simulate_safe_rollouts(r3["policy"], q, n_per_start=45, seed=400 + sd)
            agg[names[2]]["cost"].append(m3["mean_cost"]); agg[names[2]]["crash"].append(m3["crash_rate"])
            agg[names[2]]["reach"].append(m3["safe_reach_rate"]); agg[names[2]]["probes"].append(n_passive_big)

            # 4. Corridor-Gated Active Probing (max 3 probes/query along planned corridor) + HardMask
            for _ in range(3):
                r_cur = solve_with_hard_mask(solver, lambda X, _k=km_g: _k.predict_q(X)[0], q)
                corr = trace_nominal_corridor(r_cur["policy"], q, env.r_goal)
                _, std_c = km_g.predict_q(corr)
                min_d = np.min(np.linalg.norm(corr[:, None, :] - Xg[None, :, :], axis=2), axis=1)
                gated = np.where(min_d > 0.14, std_c, 0.0)
                bi = int(np.argmax(gated))
                if gated[bi] <= 2.2:
                    break
                x_new = corr[bi : bi + 1]
                q_new = np.maximum(0.0, env.q_hidden(x_new) + rng.normal(0.0, 0.5, size=1))
                Xg = np.vstack([Xg, x_new]); qg = np.concatenate([qg, q_new])
                km_g = KrigingEnvironmentModel(Xg, qg, None, fixed_kernels=None if len(Xg) % 4 == 0 else fk)
                if len(Xg) % 4 == 0:
                    fk = km_g.get_fitted_kernels()

            r4 = solve_with_hard_mask(solver, lambda X, _k=km_g: _k.predict_q(X)[0], q)
            m4 = env.simulate_safe_rollouts(r4["policy"], q, n_per_start=45, seed=400 + sd)
            agg[names[3]]["cost"].append(m4["mean_cost"]); agg[names[3]]["crash"].append(m4["crash_rate"])
            agg[names[3]]["reach"].append(m4["safe_reach_rate"]); agg[names[3]]["probes"].append(len(Xg))

    out = {"oracle_hardmask": {"cost": float(np.mean(cs_o)), "crash": float(np.mean(cr_o)), "reach": float(np.mean(sr_o))}, "methods": {}}
    for lbl in names:
        mc, mcr, msr, mpr = float(np.mean(agg[lbl]["cost"])), float(np.mean(agg[lbl]["crash"])), float(np.mean(agg[lbl]["reach"])), float(np.mean(agg[lbl]["probes"]))
        out["methods"][lbl] = {"cost": mc, "crash": mcr, "reach": msr, "avg_probes": mpr}
        print(f"  {lbl:42s} | Probes={mpr:4.1f} | AvgCost={mc:5.2f} | CrashRate={100*mcr:5.1f}% | SafeReach={100*msr:5.1f}%")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "breakthrough_b2_v3_results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    t0 = time.perf_counter()
    run_b2_v3()
    print(f"Done in {time.perf_counter() - t0:.1f}s.")
