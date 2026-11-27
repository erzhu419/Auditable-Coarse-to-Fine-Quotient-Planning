"""Generates Publication-Grade Mechanism & Counterexample Figure (`m233_fig1_mechanism_and_counterexamples.png`)
Directly from Real 3D Discrete Upwind KL-LMDP Solver Computations (Zero Synthetic/Hand-Drawn Curves).

Panels:
  A. Adaptive Sub-Portal Quadtree Cut on an `11x11` 3D Doorway Behind an Asymmetric Room Baffle
     (overlaying true desirability `z^*_Gamma` contours and the adaptive `L1..L4` quadtree partition).
  B. Why Naive Coarse Projection Fails vs. 1-Step Smooth `W_lo = K L v_lo + r_hat`:
     Plots cross-doorway slice of `L v_lo <= W_lo <= z^* <= W_hi` (top) and exact Schur residual
     `S_Gamma z - r_Gamma` (bottom), showing `O(1/h^2)` positive seam violations for `S_Gamma (L v_lo)`
     vs. strictly non-positive `-B(W_lo - L v_lo) <= 0` for `W_lo`.
  C. Monotone Nested Refinement Tightening (`L0 -> L1 -> L2 -> L3 -> L4`):
     Demonstrates `L(B_0) <= L(B_1) <= ... <= V^*(s_0) <= J^{mu_r}(s_0) <= ... <= U(B_0)` shrinking
     monotonically to machine precision at `L4`.
  D. Complete Directed Goal-Ring Support vs. Room-Only Support on Portal-Adjacent Slabs (`eps = 0.001`):
     Shows actual deployed policy regret across slab thickness `1, 2, 3` (`9.51e-3 > eps` failure under
     incomplete support for thickness >= 2 vs. `2.29e-7 <= eps` under complete support `R_G`).
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_k] = "1"

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse.linalg as spla

from green_response import ProblemSpec
from green_response.port_solvers import build_grid_points
from quotient_phase2.m23_m24_3d_portal_scale import (
    SeamFreePortal3DPlanner,
    build_3d_reflecting_obstacle_mmatrix,
    build_portal_level_blocks,
    evaluate_3d_deployed_policy_exact,
    extract_directed_goal_ring_in_room,
    solve_and_verify_portal_howard_bounds,
)


def generate_mechanism_figure() -> Path:
    # Build a clean 21^3 two-room 3D domain with an 11x11 doorway at x=10 and an asymmetric partial baffle at x=12
    gn = 21
    spec = ProblemSpec(dim=3)
    free = np.ones((gn, gn, gn), dtype=bool)
    free[10, :, :] = False
    free[10, 5:16, 5:16] = True  # 11x11 doorway (121 nodes)
    # Asymmetric partial baffle right behind lower-left quadrant of doorway
    free[12, 5:11, 5:12] = False

    nodes = np.flatnonzero(free.ravel()).astype(np.int64)
    fpos = np.full(gn ** 3, -1, dtype=np.int64)
    fpos[nodes] = np.arange(len(nodes), dtype=np.int64)
    _, pts, _ = build_grid_points(3, spec.half_width, gn)
    q = 0.45 + 0.20 * np.exp(-np.sum((pts[nodes] - np.array([[0.15, -0.2, -0.1]])) ** 2, axis=1) / 0.18)
    b = np.zeros((len(nodes), 3), dtype=float)
    b[:] = (0.06, 0.14, -0.09)
    A_csr = build_3d_reflecting_obstacle_mmatrix(spec, gn, free.ravel(), q, b).tocsr()

    def _idx(x: int, y: int, z: int) -> int:
        return int(fpos[(x * gn + y) * gn + z])

    s0 = _idx(4, 11, 10)
    goal_3d = np.zeros((gn, gn, gn), dtype=bool)
    goal_3d[13:16, 11:14, 9:12] = True  # 3x3x3 interior target in upper-right doorway corridor
    goal = goal_3d.ravel()[nodes]

    ext = np.flatnonzero(~goal)
    z_true = np.ones(len(nodes), dtype=float)
    z_true[ext] = spla.spsolve(A_csr[ext, :][:, ext].tocsc(), np.asarray((-A_csr[ext, :][:, goal]).sum(axis=1)).ravel())
    v_true_s0 = -spec.lam * float(np.log(z_true[s0]))

    pl = SeamFreePortal3DPlanner(spec, gn, free, nodes, pts[nodes], A_csr, eps_tol=0.02)
    gam = pl.gamma_f
    n_g = len(gam)
    assert n_g == 121

    # Exact Schur operator S_gg and r_gam for this 3x3x3 goal
    c_g = int(pl.room_of_f[np.flatnonzero(goal)[0]])
    rn_g = pl.room_nodes[c_g]
    tl_g = pl.room_tl[c_g]
    in_g_loc, ring_r = extract_directed_goal_ring_in_room(A_csr, goal, rn_g, gam[tl_g])
    RHS_rg = np.zeros((len(rn_g), len(ring_r)), dtype=float)
    RHS_rg[ring_r, np.arange(len(ring_r))] = 1.0
    U_rg = pl.hq_lus[c_g].solve(RHS_rg)
    K_inv = np.linalg.inv(U_rg[ring_r, :])
    h_goal_r = U_rg @ (K_inv @ np.ones(len(ring_r), dtype=float))

    D_mat = A_csr[gam, :][:, gam].toarray()
    B_mat = np.zeros((n_g, n_g), dtype=float)
    for c in range(pl.n_rooms):
        tl = pl.room_tl[c]
        Yc = pl.hq_lus[c].solve(pl.room_Arg[c].toarray())
        if c == c_g:
            Yc = Yc - U_rg @ (K_inv @ Yc[ring_r, :])
        B_mat[np.ix_(tl, tl)] += pl.room_NegAgr[c] @ Yc
    S_gg = D_mat - B_mat
    r_gam = np.zeros(n_g, dtype=float)
    r_gam[tl_g] = pl.room_NegAgr[c_g] @ h_goal_r
    K_gg = np.linalg.solve(D_mat, B_mat)
    r_hat = np.linalg.solve(D_mat, r_gam)
    z_gam_true = z_true[gam]

    # Start-room readout
    c_s = int(pl.room_of_f[s0])
    rn_s = pl.room_nodes[c_s]
    e_s = np.zeros(len(rn_s), dtype=float)
    e_s[int(np.searchsorted(rn_s, s0))] = 1.0
    lam_s = pl.hq_lus[c_s].solve(e_s, trans="T")
    h_s = np.asarray(pl.room_Arg[c_s].T @ lam_s).ravel()

    # Evaluate L0, L1, L2, L3, L4 nested levels
    p_ids = np.arange(n_g, dtype=np.int64)
    p_pts = pts[gam]
    lv_bounds_lo, lv_bounds_hi, lv_pol_j = [], [], []
    L1_data = {}

    for lv in range(5):
        blks = build_portal_level_blocks(p_ids, p_pts, lv)
        L_mat = np.zeros((n_g, len(blks)), dtype=float)
        for j, bl in enumerate(blks):
            L_mat[bl, j] = 1.0
        hw = solve_and_verify_portal_howard_bounds(K_gg @ L_mat, r_hat, blks, max_iters=40)
        W_lo = hw["W_lo"]
        W_hi = hw["W_hi"]
        Lv_lo = L_mat @ hw["v_lo"]
        lo_v = -spec.lam * float(np.log(float(h_s @ W_hi)))
        hi_v = -spec.lam * float(np.log(float(h_s @ W_lo)))

        z_sub = np.ones(len(nodes), dtype=float)
        z_sub[gam] = W_lo
        for c in range(pl.n_rooms):
            rn_c = pl.room_nodes[c]
            yc = pl.hq_lus[c].solve(pl.room_Arg[c] @ W_lo[pl.room_tl[c]])
            if c == c_g:
                yc = h_goal_r + yc - U_rg @ (K_inv @ yc[ring_r])
                yc[in_g_loc] = 1.0
            z_sub[rn_c] = yc
        z_sub[goal] = 1.0
        j_v = evaluate_3d_deployed_policy_exact(A_csr, goal, 0.0, z_sub, spec.lam, s0)
        lv_bounds_lo.append(lo_v)
        lv_bounds_hi.append(hi_v)
        lv_pol_j.append(j_v)

        if lv == 2:
            L1_data = {
                "Lv_lo": Lv_lo,
                "W_lo": W_lo,
                "W_hi": W_hi,
                "res_naive": (S_gg @ Lv_lo) - r_gam,
                "res_smooth": (S_gg @ W_lo) - r_gam,
            }

    # Build adaptive sub-portal quadtree cut for Panel A (splitting blocks with largest oscillation)
    blks_by_lv = [build_portal_level_blocks(p_ids, p_pts, lv) for lv in range(5)]
    children = {}
    for lv in range(4):
        ch_map = np.empty(n_g, dtype=np.int64)
        for ci, carr in enumerate(blks_by_lv[lv + 1]):
            ch_map[carr] = ci
        for bi, barr in enumerate(blks_by_lv[lv]):
            children[(lv, bi)] = [(lv + 1, int(x)) for x in sorted(set(ch_map[barr]))] if len(barr) > 1 else []

    active_cut = [(0, 0)]
    for _ in range(3):
        scores = []
        for idx_k, (lv_k, bi_k) in enumerate(active_cut):
            bl = blks_by_lv[lv_k][bi_k]
            if lv_k < 3 and len(bl) > 1:
                osc = float(np.max(z_gam_true[bl]) - np.min(z_gam_true[bl]))
                scores.append((osc, idx_k))
        scores.sort(reverse=True)
        split_set = {x[1] for x in scores[: min(3, len(scores))]}
        nxt_cut = []
        for idx_k, key_k in enumerate(active_cut):
            if idx_k in split_set and children[key_k]:
                nxt_cut.extend(children[key_k])
            else:
                nxt_cut.append(key_k)
        active_cut = nxt_cut

    # Panel D: Complete vs. Incomplete Goal-Ring Support (`17^3`, thickness 1, 2, 3 at eps = 0.001)
    gn17 = 17
    free17 = np.ones((gn17, gn17, gn17), dtype=bool)
    free17[8, :, :] = False
    free17[8, 6:11, 6:11] = True
    n17 = np.flatnonzero(free17.ravel()).astype(np.int64)
    fp17 = np.full(gn17 ** 3, -1, dtype=np.int64)
    fp17[n17] = np.arange(len(n17), dtype=np.int64)
    _, pts17, _ = build_grid_points(3, spec.half_width, gn17)
    b17 = np.zeros((len(n17), 3), dtype=float)
    b17[:, 1] = 0.13
    A17 = build_3d_reflecting_obstacle_mmatrix(spec, gn17, free17.ravel(), np.full(len(n17), 0.5), b17).tocsr()
    s17 = int(fp17[(3 * gn17 + 8) * gn17 + 8])
    reg_complete, reg_room_only = [], []
    for thick in (1, 2, 3):
        g_slab = np.zeros((gn17, gn17, gn17), dtype=bool)
        g_slab[9 : 9 + thick, 6:11, 6:11] = True
        gm17 = g_slab.ravel()[n17]
        ext17 = np.flatnonzero(~gm17)
        zt17 = np.ones(len(n17), dtype=float)
        zt17[ext17] = spla.spsolve(A17[ext17, :][:, ext17].tocsc(), np.asarray((-A17[ext17, :][:, gm17]).sum(axis=1)).ravel())
        vt17 = -spec.lam * float(np.log(zt17[s17]))

        pl_ok = SeamFreePortal3DPlanner(spec, gn17, free17, n17, pts17[n17], A17, eps_tol=0.001)
        r_ok = pl_ok.solve_unseen_goal(s17, gm17, materialize_full_z_sub=True)
        j_ok = evaluate_3d_deployed_policy_exact(A17, gm17, 0.0, r_ok["z_guide_full"], spec.lam, s17)
        reg_complete.append(max(1e-8, float(j_ok - vt17)))

        # Simulate incomplete room-only ring `A_rr[ext_r, g_r]`
        c_g17 = int(pl_ok.room_of_f[np.flatnonzero(gm17)[0]])
        rn17 = pl_ok.room_nodes[c_g17]
        in_g17 = gm17[rn17]
        g_r17 = np.flatnonzero(in_g17)
        ext_r17 = np.flatnonzero(~in_g17)
        A_rr17 = A17[rn17, :][:, rn17]
        bad_ring = g_r17[np.asarray((A_rr17[ext_r17, :][:, g_r17] < 0.0).sum(axis=0)).ravel() > 0]
        RHS_bad = np.zeros((len(rn17), len(bad_ring)), dtype=float)
        RHS_bad[bad_ring, np.arange(len(bad_ring))] = 1.0
        U_bad = pl_ok.hq_lus[c_g17].solve(RHS_bad)
        K_bad_inv = np.linalg.inv(U_bad[bad_ring, :])
        h_bad = U_bad @ (K_bad_inv @ np.ones(len(bad_ring), dtype=float))
        D17 = A17[pl_ok.gamma_f, :][:, pl_ok.gamma_f].toarray()
        B17 = np.zeros((len(pl_ok.gamma_f), len(pl_ok.gamma_f)), dtype=float)
        for c in range(pl_ok.n_rooms):
            tl = pl_ok.room_tl[c]
            Yc = pl_ok.hq_lus[c].solve(pl_ok.room_Arg[c].toarray())
            if c == c_g17:
                Yc = Yc - U_bad @ (K_bad_inv @ Yc[bad_ring, :])
            B17[np.ix_(tl, tl)] += pl_ok.room_NegAgr[c] @ Yc
        rg17 = np.zeros(len(pl_ok.gamma_f), dtype=float)
        rg17[pl_ok.room_tl[c_g17]] = pl_ok.room_NegAgr[c_g17] @ h_bad
        w_bad = np.linalg.solve(D17 - B17, rg17)
        z_bad = np.ones(len(n17), dtype=float)
        z_bad[pl_ok.gamma_f] = w_bad
        for c in range(pl_ok.n_rooms):
            yc = pl_ok.hq_lus[c].solve(pl_ok.room_Arg[c] @ w_bad[pl_ok.room_tl[c]])
            if c == c_g17:
                yc = h_bad + yc - U_bad @ (K_bad_inv @ yc[bad_ring])
                yc[in_g17] = 1.0
            z_bad[pl_ok.room_nodes[c]] = yc
        z_bad[gm17] = 1.0
        j_bad = evaluate_3d_deployed_policy_exact(A17, gm17, 0.0, np.maximum(z_bad, 1e-30), spec.lam, s17)
        reg_room_only.append(max(1e-8, float(j_bad - vt17)))

    # Render 4-panel Mechanism & Counterexample Figure with wide inter-column spacing (zero label overlap)
    fig = plt.figure(figsize=(14.8, 10.0), dpi=180)
    gs = fig.add_gridspec(2, 2, hspace=0.33, wspace=0.35)

    # Panel A: 11x11 Doorway Desirability Field + Sub-Portal Adaptive Quadtree Cut
    ax_a = fig.add_subplot(gs[0, 0])
    z_grid = z_gam_true.reshape(11, 11)
    im = ax_a.imshow(z_grid.T, origin="lower", cmap="viridis", extent=[-0.5, 10.5, -0.5, 10.5])
    cb = fig.colorbar(im, ax=ax_a, fraction=0.044, pad=0.03)
    cb.formatter.set_powerlimits((-2, 2))
    cb.update_ticks()
    cb.set_label("True Doorway Desirability $z^*_\\Gamma$", fontsize=8.4)
    for lv_k, bi_k in active_cut:
        bl = blks_by_lv[lv_k][bi_k]
        ys = bl // 11
        zs = bl % 11
        rect = patches.Rectangle(
            (float(np.min(ys)) - 0.5, float(np.min(zs)) - 0.5),
            float(np.max(ys) - np.min(ys) + 1),
            float(np.max(zs) - np.min(zs) + 1),
            linewidth=1.5,
            edgecolor="white",
            facecolor="none",
        )
        ax_a.add_patch(rect)
    ax_a.set_xlabel("Doorway Tangential Index $y$ (0..10)")
    ax_a.set_ylabel("Doorway Tangential Index $z$ (0..10)")
    ax_a.set_title(f"A. Sub-Portal Quadtree Cut on 11x11 Doorway ({len(active_cut)} Active Blocks vs 121 Nodes)", fontsize=9.4, fontweight="bold", pad=10)

    # Panel B: 1D Cross-Doorway Slice through Peak Seam Violation — Naive Jump vs 1-Step Smooth Subsolution
    gs_b = gs[0, 1].subgridspec(2, 1, height_ratios=[1.12, 1.0], hspace=0.15)
    ax_b1 = fig.add_subplot(gs_b[0])
    ax_b2 = fig.add_subplot(gs_b[1], sharex=ax_b1)
    peak_node = int(np.argmax(L1_data["res_naive"]))
    z_sl = int(peak_node % 11)
    sl_idx = np.array([y * 11 + z_sl for y in range(11)], dtype=np.int64)
    xs_sl = np.arange(11)
    ax_b1.step(xs_sl, L1_data["Lv_lo"][sl_idx], where="mid", linestyle="--", color="#c0392b", linewidth=1.9, label="Piecewise-Constant $L v_{\\mathrm{lo}}$ (L2)")
    ax_b1.plot(xs_sl, L1_data["W_lo"][sl_idx], "-o", markersize=4, color="#27ae60", linewidth=2.1, label="1-Step Smooth $W_{\\mathrm{lo}} = K L v_{\\mathrm{lo}} + \\hat{r}$")
    ax_b1.plot(xs_sl, z_gam_true[sl_idx], "-s", markersize=3.8, color="#2c3e50", linewidth=1.8, label="Exact $z^*_\\Gamma$")
    ax_b1.plot(xs_sl, L1_data["W_hi"][sl_idx], "-^", markersize=4, color="#2980b9", linewidth=1.8, label="1-Step Smooth $W_{\\mathrm{hi}}$")
    ax_b1.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
    ax_b1.set_ylabel("Desirability", fontsize=8.5)
    ax_b1.set_title("B. Doorway Seam Singularity vs. Seam-Free 1-Step Smoothing", fontsize=9.4, fontweight="bold", pad=10)
    ax_b1.legend(fontsize=7.1, ncol=2, loc="upper left")
    ax_b1.grid(True, alpha=0.28)
    plt.setp(ax_b1.get_xticklabels(), visible=False)

    res_n_sl = L1_data["res_naive"][sl_idx]
    res_s_sl = L1_data["res_smooth"][sl_idx]
    ymax_b2 = max(float(np.max(res_n_sl)) * 1.38, 1e-4)
    ymin_b2 = min(float(np.min(res_n_sl)), float(np.min(res_s_sl))) * 1.15
    ax_b2.axhspan(0.0, ymax_b2, color="#fadbd8", alpha=0.45)
    ax_b2.axhline(0.0, color="black", linewidth=1.0, linestyle=":")
    ax_b2.plot(xs_sl, res_n_sl, "--x", color="#c0392b", linewidth=1.9, label="Naive $(S L v_{\\mathrm{lo}} - r)$: $>0$ Seam Violation")
    ax_b2.plot(xs_sl, res_s_sl, "-o", markersize=4, color="#27ae60", linewidth=2.1, label="Smooth $(S W_{\\mathrm{lo}} - r) = -B(W_{\\mathrm{lo}} - L v_{\\mathrm{lo}}) \\leq 0$")
    ax_b2.set_ylim(ymin_b2, ymax_b2)
    ax_b2.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
    ax_b2.set_xlabel(f"Doorway Cross-Section Node $y$ (Slice $z={z_sl}$ Across Coarse Block Seams)")
    ax_b2.set_ylabel("Schur Residual", fontsize=8.5)
    ax_b2.legend(fontsize=7.0, loc="lower right")
    ax_b2.grid(True, alpha=0.28)

    # Panel C: Monotone Nested Refinement Tightening (`L0 -> L4`)
    ax_c = fig.add_subplot(gs[1, 0])
    lvs = np.arange(5)
    ax_c.plot(lvs, lv_bounds_hi, "-^", color="#d35400", linewidth=2.2, label="Certified Upper Bound $U(\\mathcal{B}_\\ell)$")
    ax_c.plot(lvs, lv_pol_j, "-o", color="#27ae60", linewidth=2.2, label="Deployed Policy Cost $J^{\\hat{\\mu}_\\ell}(s_0)$")
    ax_c.axhline(v_true_s0, color="#2c3e50", linestyle="--", linewidth=1.6, label="Optimal Value $V^*(s_0)$")
    ax_c.plot(lvs, lv_bounds_lo, "-v", color="#2980b9", linewidth=2.2, label="Certified Lower Bound $L(\\mathcal{B}_\\ell)$")
    ax_c.fill_between(lvs, lv_bounds_lo, lv_bounds_hi, color="#3498db", alpha=0.13)
    ax_c.set_xticks(lvs)
    ax_c.set_xticklabels(["L0\n(1 blk)", "L1\n(4 blks)", "L2\n(16 blks)", "L3\n(64 blks)", "L4\n(121 exact)"])
    ax_c.set_ylabel("Control Cost at $s_0$")
    ax_c.set_title("C. Monotone Nested-Partition Tightening ($L \\leq V^* \\leq J^{\\hat{\\mu}} \\leq U$)", fontsize=9.5, fontweight="bold")
    ax_c.grid(True, alpha=0.28)
    ax_c.legend(fontsize=7.8)

    # Panel D: Complete vs. Incomplete Goal-Ring Support (`eps = 0.001`)
    ax_d = fig.add_subplot(gs[1, 1])
    tx = np.arange(3)
    w = 0.34
    ax_d.bar(tx - w / 2, reg_room_only, width=w, color="#c0392b", alpha=0.88, label="Room-Only Ring $\\tilde{R}_G^{\\mathrm{bad}}$ (Omits Portal Edges)")
    ax_d.bar(tx + w / 2, reg_complete, width=w, color="#27ae60", alpha=0.88, label="Complete Exterior Ring $R_G$ (Proposition 1)")
    ax_d.axhline(0.001, color="#8e44ad", linestyle="--", linewidth=1.8, label="Target Budget $\\varepsilon_{\\mathrm{tol}} = 10^{-3}$")
    ax_d.text(0, max(reg_room_only[0], reg_complete[0]) * 1.45, "thick=1:\nrings coincide", ha="center", va="bottom", fontsize=7.4, color="#34495e")
    ax_d.set_yscale("log")
    ax_d.set_xticks(tx)
    ax_d.set_xticklabels(["Thickness 1\n(25 nodes)", "Thickness 2\n(50 nodes)", "Thickness 3\n(75 nodes)"])
    ax_d.set_ylabel("Deployed Policy Regret $J^{\\hat{\\mu}}(s_0) - V^*(s_0)$ (log scale)")
    ax_d.set_title("D. Portal-Adjacent Slab Counterexample: Complete Goal-Ring Support", fontsize=9.5, fontweight="bold")
    ax_d.set_ylim(1e-8, 5e-2)
    ax_d.grid(True, which="both", axis="y", alpha=0.25)
    ax_d.legend(fontsize=7.6, loc="upper left")

    out_path = Path(__file__).resolve().parent / "m233_fig1_mechanism_and_counterexamples.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(
        f"[OK] Wrote {out_path.name} | slice max naive pos residual={float(np.max(res_n_sl)):.3e}, "
        f"max smooth residual={float(np.max(res_s_sl)):.3e}, V*(s0)={v_true_s0:.4f}"
    )
    return out_path


if __name__ == "__main__":
    generate_mechanism_figure()
