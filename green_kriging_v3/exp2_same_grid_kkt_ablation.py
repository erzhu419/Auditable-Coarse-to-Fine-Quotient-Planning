"""Experiment 2 (green_kriging_v3): Strictly Matched-Grid Non-LMDP KKT Warm-Start Ablation.

Addresses every attribution point from `green_kriging_v2_review` Section 7 / 11:
1. Evaluates ALL initializers on the EXACT SAME GRID (`35^2` AND `51^2` separately!).
2. Includes `Same-GP Isotropic FD Warm-Start` alongside `Zero`, `Geodesic`, and `Schur-Port`
   warm-starts so single-query initialization benefit vs multi-query reuse benefit are cleanly split!
3. Separates `K=1` cold total time (charging full `SchurPortGreenPlanner` build cost!) from
   `K=12` multi-query stream cumulative time.
4. Evaluates `GroundTruth` vs `Same-GP` on the EXACT SAME `51^2` grid to cleanly isolate GP
   observation error from spatial discretization error, and logs TRUE discrete Bellman residuals!
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

from core_v3 import (
    GoalBall,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    generate_benchmark_map,
    sample_noisy_probes,
    simulate_closed_loop_crn,
    solve_anisotropic_ball_qp,
)
from exp1_pareto_and_adaptive_tour import build_catalog_and_stream, paired_student_ci95
from schur_port_2d3d import (
    ClassicalFDSolver,
    SchurPortGreenPlanner,
    make_grid_axes,
    solve_monotone_anisotropic_constrained_hjb_2d,
)


def run_matched_grid_kkt_ablation(grid_n: int, n_maps: int = 8, n_queries: int = 12, n_probes: int = 45) -> dict:
    R_diag = (0.35, 3.0)
    u_max = 1.8
    spec_nl = ProblemSpec(dim=2, half_width=1.65, sigma=0.45, q0=0.50, r_diag=R_diag, u_max=u_max)
    spec_iso = ProblemSpec(dim=2, half_width=1.65, sigma=0.45, q0=0.50)

    methods = [
        "GroundTruth-FullKKT",
        "SameGP-FullKKT",
        "ZeroInit-3Step",
        "GeodesicInit-3Step",
        "IsoFDInit-3Step",
        "SchurPortInit-3Step",
    ]
    map_costs: Dict[str, List[float]] = {m: [] for m in methods}
    map_bellman_res: Dict[str, List[float]] = {m: [] for m in methods}
    map_k1_cold_ms: Dict[str, List[float]] = {m: [] for m in methods if m != "GroundTruth-FullKKT"}
    map_k_all_ms: Dict[str, List[float]] = {m: [] for m in methods if m != "GroundTruth-FullKKT"}

    _, _, pts = make_grid_axes(spec_nl.half_width, grid_n, 2)

    for m_i in range(n_maps):
        map_seed = 6100 + m_i
        world = generate_benchmark_map(map_seed, dim=2, regime="narrow_barrier", with_drift=True, spec=spec_nl)
        waypoints, patch_zones, queries = build_catalog_and_stream(map_seed, dim=2, n_queries=n_queries)
        X_obs, q_obs, b_obs = sample_noisy_probes(world, n_probes=n_probes, seed=map_seed + 9, include_drift=True)
        km = KrigingWorldModel(X_obs, q_obs, b_obs)

        # Build isotropic FD & SchurPort operators on the EXACT SAME `grid_n` (explicitly timed!)
        iso_fd = ClassicalFDSolver(spec_iso, grid_n, km.predict_q, km.predict_b)
        schur_pl = SchurPortGreenPlanner(spec_iso, grid_n, km.predict_q, km.predict_b, waypoints, patch_zones, initial_sectors_per_wp=4)

        c_q = {m: [] for m in methods}
        br_q = {m: [] for m in methods}
        ms_q = {m: [] for m in methods if m != "GroundTruth-FullKKT"}

        for qi, q in enumerate(queries):
            crn_s = 7500 + 50 * m_i + qi
            # 1. GroundTruth Full KKT on SAME `grid_n`
            gt = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, grid_n, world.q_hidden, world.drift, q, n_iters=22)
            c_q["GroundTruth-FullKKT"].append(simulate_closed_loop_crn(world, gt["policy"], q, n_per_start=18, seed=crn_s)["mean_cost"])
            br_q["GroundTruth-FullKKT"].append(gt["true_bellman_residual"])

            # 2. Same-GP Full KKT on SAME `grid_n`
            full_gp = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, grid_n, km.predict_q, km.predict_b, q, n_iters=22)
            c_q["SameGP-FullKKT"].append(simulate_closed_loop_crn(world, full_gp["policy"], q, n_per_start=18, seed=crn_s)["mean_cost"])
            br_q["SameGP-FullKKT"].append(full_gp["true_bellman_residual"])
            ms_q["SameGP-FullKKT"].append(full_gp["solve_ms"])

            # 3. Zero-Init 3-Step
            z3 = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, grid_n, km.predict_q, km.predict_b, q, n_iters=3)
            c_q["ZeroInit-3Step"].append(simulate_closed_loop_crn(world, z3["policy"], q, n_per_start=18, seed=crn_s)["mean_cost"])
            br_q["ZeroInit-3Step"].append(z3["true_bellman_residual"])
            ms_q["ZeroInit-3Step"].append(z3["solve_ms"])

            # 4. Geodesic-Init 3-Step (free-space analytical direction to nearest goal)
            t0 = time.perf_counter()
            g_c = np.array([g.center for g in q.goals])
            diffs = pts[:, None, :] - g_c[None, :, :]
            dn = np.linalg.norm(diffs, axis=2)
            best_g = np.argmin(dn, axis=1)
            dir_g = diffs[np.arange(len(pts)), best_g] / np.maximum(dn[np.arange(len(pts)), best_g][:, None], 1e-9)
            u_geo = solve_anisotropic_ball_qp(np.sqrt(2.0 * spec_nl.q0) * dir_g, np.array(R_diag), u_max)
            geo_prep = 1000.0 * (time.perf_counter() - t0)
            g3 = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, grid_n, km.predict_q, km.predict_b, q, n_iters=3, u_init_grid=u_geo)
            c_q["GeodesicInit-3Step"].append(simulate_closed_loop_crn(world, g3["policy"], q, n_per_start=18, seed=crn_s)["mean_cost"])
            br_q["GeodesicInit-3Step"].append(g3["true_bellman_residual"])
            ms_q["GeodesicInit-3Step"].append(geo_prep + g3["solve_ms"])

            # 5. Isotropic-FD-Init 3-Step (includes FD solve + KKT projection time!)
            t0 = time.perf_counter()
            sol_ifd = iso_fd.solve_direct(q)
            u_ifd = solve_anisotropic_ball_qp(-sol_ifd["policy"](pts), np.array(R_diag), u_max)
            ifd_prep = 1000.0 * (time.perf_counter() - t0)
            ifd3 = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, grid_n, km.predict_q, km.predict_b, q, n_iters=3, u_init_grid=u_ifd)
            c_q["IsoFDInit-3Step"].append(simulate_closed_loop_crn(world, ifd3["policy"], q, n_per_start=18, seed=crn_s)["mean_cost"])
            br_q["IsoFDInit-3Step"].append(ifd3["true_bellman_residual"])
            ms_q["IsoFDInit-3Step"].append(ifd_prep + ifd3["solve_ms"])

            # 6. SchurPort-Init 3-Step (includes port solve + KKT projection time!)
            t0 = time.perf_counter()
            sol_sp = schur_pl.solve_query(q)
            u_sp = solve_anisotropic_ball_qp(-sol_sp["policy"](pts), np.array(R_diag), u_max)
            sp_prep = 1000.0 * (time.perf_counter() - t0)
            sp3 = solve_monotone_anisotropic_constrained_hjb_2d(spec_nl, grid_n, km.predict_q, km.predict_b, q, n_iters=3, u_init_grid=u_sp)
            c_q["SchurPortInit-3Step"].append(simulate_closed_loop_crn(world, sp3["policy"], q, n_per_start=18, seed=crn_s)["mean_cost"])
            br_q["SchurPortInit-3Step"].append(sp3["true_bellman_residual"])
            ms_q["SchurPortInit-3Step"].append(sp_prep + sp3["solve_ms"])

        for m in methods:
            map_costs[m].append(float(np.mean(c_q[m])))
            map_bellman_res[m].append(float(np.mean(br_q[m])))

        # Explicit cold K=1 vs cumulative K=12 accounting (charging full operator build!)
        map_k1_cold_ms["SameGP-FullKKT"].append(ms_q["SameGP-FullKKT"][0])
        map_k_all_ms["SameGP-FullKKT"].append(float(np.sum(ms_q["SameGP-FullKKT"])))
        map_k1_cold_ms["ZeroInit-3Step"].append(ms_q["ZeroInit-3Step"][0])
        map_k_all_ms["ZeroInit-3Step"].append(float(np.sum(ms_q["ZeroInit-3Step"])))
        map_k1_cold_ms["GeodesicInit-3Step"].append(ms_q["GeodesicInit-3Step"][0])
        map_k_all_ms["GeodesicInit-3Step"].append(float(np.sum(ms_q["GeodesicInit-3Step"])))
        map_k1_cold_ms["IsoFDInit-3Step"].append(iso_fd.op_build_ms + ms_q["IsoFDInit-3Step"][0])
        map_k_all_ms["IsoFDInit-3Step"].append(iso_fd.op_build_ms + float(np.sum(ms_q["IsoFDInit-3Step"])))
        map_k1_cold_ms["SchurPortInit-3Step"].append(schur_pl.op_build_ms + ms_q["SchurPortInit-3Step"][0])
        map_k_all_ms["SchurPortInit-3Step"].append(schur_pl.op_build_ms + float(np.sum(ms_q["SchurPortInit-3Step"])))

        print(f"  [KKT {grid_n}^2 map {m_i+1}/{n_maps}] Full={map_costs['SameGP-FullKKT'][-1]:.3f} | Geo3={map_costs['GeodesicInit-3Step'][-1]:.3f} | IsoFD3={map_costs['IsoFDInit-3Step'][-1]:.3f} | Schur3={map_costs['SchurPortInit-3Step'][-1]:.3f}", flush=True)

    full_gp_arr = np.array(map_costs["SameGP-FullKKT"])
    gt_arr = np.array(map_costs["GroundTruth-FullKKT"])
    info_gap_m, info_gap_ci = paired_student_ci95(full_gp_arr - gt_arr)

    summary = {
        "grid_n": grid_n,
        "n_maps": n_maps,
        "n_queries": n_queries,
        "same_grid_gp_vs_gt_info_gap": {
            "mean": info_gap_m,
            "student_t_ci95": info_gap_ci,
            "rel_pct": 100.0 * info_gap_m / float(np.mean(gt_arr)),
        },
        "methods": {},
    }
    for m in methods:
        arr = np.array(map_costs[m])
        entry = {
            "mean_cost": float(np.mean(arr)),
            "mean_true_bellman_residual": float(np.mean(map_bellman_res[m])),
            "per_map_costs": map_costs[m],
        }
        if m != "GroundTruth-FullKKT":
            dm, ci = paired_student_ci95(arr - full_gp_arr)
            entry.update({
                "paired_diff_vs_same_grid_full_kkt": {"mean": dm, "student_t_ci95": ci},
                "rel_gap_vs_same_grid_full_kkt_pct": 100.0 * dm / float(np.mean(full_gp_arr)),
                "k1_cold_total_ms": float(np.mean(map_k1_cold_ms[m])),
                "k12_stream_total_ms": float(np.mean(map_k_all_ms[m])),
            })
        summary["methods"][m] = entry
    return summary


def plot_exp2(r35: dict, r51: dict, out_png: Path):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.7))
    cand = ["ZeroInit-3Step", "GeodesicInit-3Step", "IsoFDInit-3Step", "SchurPortInit-3Step", "SameGP-FullKKT"]
    cols = ["#d62728", "#ff7f0e", "#9467bd", "#1f77b4", "#2ca02c"]
    lbls = ["Zero Init (3-step)", "Geodesic Init (3-step)", "Iso-FD Init (3-step)", "Schur-Port Init (3-step)", "Full KKT-PI (22-step)"]

    for ax, data, g_lbl in [(axes[0], r35, "35×35 Same-Grid"), (axes[1], r51, "51×51 Same-Grid")]:
        for m, c, l in zip(cand, cols, lbls):
            t12 = data["methods"][m]["k12_stream_total_ms"]
            jc = data["methods"][m]["mean_cost"]
            ax.scatter([t12], [jc], s=115, color=c, label=f"{l}\n(Cost={jc:.3f}, 12Q={t12:.0f}ms)")
        ax.axhline(data["methods"]["GroundTruth-FullKKT"]["mean_cost"], color="#555555", ls=":", label="GroundTruth Full KKT (Same Grid)")
        ax.set_xscale("log")
        ax.set_xlabel("12-Query Stream Total Time Incl. Operator Build (ms, log)")
        ax.set_ylabel("Closed-Loop Cost (8 Narrow-Barrier Maps)")
        ax.set_title(f"{g_lbl} Non-LMDP Warm-Start Ablation")
        ax.grid(True, alpha=0.3, which="both")
        ax.legend(fontsize=7.6)

    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close(fig)


def main():
    print("=== Exp 2A: Matched 35x35 Grid Non-LMDP KKT Ablation (8 maps x 12 queries) ===", flush=True)
    r35 = run_matched_grid_kkt_ablation(grid_n=35, n_maps=8, n_queries=12, n_probes=75)
    print("\n=== Exp 2B: Matched 51x51 Grid Non-LMDP KKT Ablation (8 maps x 12 queries) ===", flush=True)
    r51 = run_matched_grid_kkt_ablation(grid_n=51, n_maps=8, n_queries=12, n_probes=75)

    out_dir = Path(__file__).resolve().parent
    res = {"grid_35": r35, "grid_51": r51}
    (out_dir / "exp2_kkt_ablation_results.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    plot_exp2(r35, r51, out_dir / "exp2_same_grid_kkt_ablation.png")
    print("Saved exp2_kkt_ablation_results.json and exp2_same_grid_kkt_ablation.png", flush=True)


if __name__ == "__main__":
    main()
