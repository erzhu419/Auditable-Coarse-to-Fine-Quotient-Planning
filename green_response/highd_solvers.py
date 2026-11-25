"""4D / 6D Physics-Mean GP Value Distillation & Scoped 4D Kinetic Extensions (`green_response.highd_solvers`).

Audit Closures over `v4`:
1. Explicit `ProblemSpec` capability guard at solver entry: rejects unsupported finite `u_max` or
   anisotropic `r_diag`, while supporting exact isotropic scalar `R = r I` consistently across
   `lam = r * sigma^2`, `kappa = sqrt(2 * q0 / r) / sigma^2`, `u = -grad V / r`, collar PDE residual,
   and stochastic Girsanov weight (`GPT6 highd_v4_spec_guard_probe.py` discrepancy `0.65 -> < 1e-11`!).
2. Explicit Physics-Mean Prior framing (`m(x) = V_0(x)`) + Nontrivial Geometric/Eikonal Distance Cone
   Mean Prior (`EikonalConeMeanGuide`) + Exact Frozen-Label Refit API (`refit_frozen_fk_with_prior`)
   isolating prior-mean structure from continuation-bootstrap label differences!
3. Scoped 4D Kinetic Double-Integrator: replaces hardcoded `unaccounted_guide_jump: 0.0` with an
   independent floating-point path-sum vs endpoint-telescoping discrepancy check, uses 6 continuation
   rounds by default, exposes `value_fn`, and logs boundary/specular/action-cap scope diagnostics.
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_continuous_are
from scipy.optimize import nnls
from scipy.special import kv
from scipy.stats import norm, qmc

from .core import (
    GoalBall,
    KrigingWorldModel,
    ProblemSpec,
    QueryTask,
    eval_goal_union,
    eval_hazard_features,
    reflect_into_box,
    reflect_kinetic_into_box,
)


def even_collar_warp_c2(X: np.ndarray, half_width: float, collar_delta: float = 0.22) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Even-periodic `C^2` collar map `w(X)` on `R^d` (`4L`-periodic, even across `+/- L`).
    Returns `(Xw, dw_dx, d2w_dx2)`.
    """
    L = float(half_width)
    delta = float(collar_delta)
    L0 = L - delta
    period = 4.0 * L
    m = np.mod(X + L, period)
    odd = m > 2.0 * L
    u = np.where(odd, 3.0 * L - m, m - L)
    du_dx = np.where(odd, -1.0, 1.0)

    au = np.abs(u)
    in_collar = au > L0
    if not np.any(in_collar):
        return u, du_dx, np.zeros_like(X, dtype=float)

    s = np.clip((au - L0) / delta, 0.0, 1.0)
    half_pi_s = 0.5 * np.pi * s
    warped_mag = L0 + (2.0 * delta / np.pi) * np.sin(half_pi_s)
    sgn_u = np.sign(u)

    Xw = np.where(in_collar, sgn_u * warped_mag, u)
    dw_du = np.where(in_collar, np.cos(half_pi_s), 1.0)
    d2w_du2 = np.where(in_collar, -sgn_u * (0.5 * np.pi / delta) * np.sin(half_pi_s), 0.0)
    return Xw, dw_du * du_dx, d2w_du2


class MirrorNeumannMatern52GP:
    """SPD Anisotropic/Isotropic Matérn-5/2 GP on `[-L, L]^d` via smooth Neumann pullback,
    supporting optional explicit analytical mean prior `prior_fn(X) -> (m_val, m_grad)` so
    `GP(y_tot; mean=m)` and `m + GP(y_tot - m; mean=const)` are algebraically identical!
    """

    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        half_width: float,
        length_scale: float | Sequence[float] = 0.58,
        noise_vec: Optional[np.ndarray] = None,
        neumann_axes: Optional[Sequence[int]] = None,
        prior_val_and_grad_fn: Optional[Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]] = None,
    ):
        self.X_raw = np.atleast_2d(np.asarray(X, dtype=float))
        self.y_raw = np.asarray(y, dtype=float)
        self.L = float(half_width)
        self.d = self.X_raw.shape[1]
        ell = np.atleast_1d(np.asarray(length_scale, dtype=float))
        self.ell = np.full(self.d, float(ell[0])) if ell.size == 1 else ell.copy()
        self.neumann_axes = tuple(range(self.d)) if neumann_axes is None else tuple(neumann_axes)
        self.prior_fn = prior_val_and_grad_fn

        if self.prior_fn is not None:
            m_train, _ = self.prior_fn(self.X_raw)
            y_eff = self.y_raw - m_train
        else:
            y_eff = self.y_raw

        self.y_mean = float(np.mean(y_eff))
        yc = y_eff - self.y_mean
        self.y_scale = float(max(np.std(yc), 1e-6))
        yn = yc / self.y_scale

        self.Phi_X, _ = self._feature_map(self.X_raw)
        diff = self.Phi_X[:, None, :] - self.Phi_X[None, :, :]
        s = np.sqrt(5.0 * np.sum(diff ** 2, axis=2))
        K = (1.0 + s + (s ** 2) / 3.0) * np.exp(-s)
        if noise_vec is None:
            K[np.diag_indices_from(K)] += 2e-3
        else:
            K[np.diag_indices_from(K)] += np.asarray(noise_vec, dtype=float)
        c, low = cho_factor(K, lower=True)
        self.alpha = cho_solve((c, low), yn) * self.y_scale

    def _feature_map(self, X: np.ndarray) -> Tuple[np.ndarray, List[Tuple]]:
        L = self.L
        feats = []
        jac_info = []
        for j in range(self.d):
            xj = X[:, j:j + 1]
            ej = self.ell[j]
            if j in self.neumann_axes:
                a1 = (0.5 * np.pi / L) * xj
                a2 = (np.pi / L) * xj
                p1 = ((2.0 * L / np.pi) * np.sin(a1)) / ej
                p2 = ((0.35 * L / np.pi) * np.cos(a2)) / ej
                dp1 = np.cos(a1) / ej
                dp2 = (-0.35 * np.sin(a2)) / ej
                col_idx = len(feats)
                feats.extend([p1, p2])
                jac_info.append((j, col_idx, dp1[:, 0], dp2[:, 0]))
            else:
                col_idx = len(feats)
                feats.append(xj / ej)
                jac_info.append((j, col_idx, np.full(len(X), 1.0 / ej), None))
        return np.hstack(feats), jac_info

    def predict_val_and_grad(self, Xq: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        Xq = np.atleast_2d(np.asarray(Xq, dtype=float))
        Phi_q, jac_info = self._feature_map(Xq)
        diff = Phi_q[:, None, :] - self.Phi_X[None, :, :]
        r2 = np.sum(diff ** 2, axis=2)
        s = np.sqrt(5.0 * r2)
        exp_s = np.exp(-s)
        k_mat = (1.0 + s + (s ** 2) / 3.0) * exp_s
        val = self.y_mean + k_mat @ self.alpha

        coeff = -(5.0 / 3.0) * (1.0 + s) * exp_s
        weighted = coeff * self.alpha[None, :]
        grad_phi = np.einsum("ij,ijd->id", weighted, diff)
        grad_x = np.zeros((len(Xq), self.d), dtype=float)
        for j, c_idx, dp1, dp2 in jac_info:
            if dp2 is None:
                grad_x[:, j] = grad_phi[:, c_idx] * dp1
            else:
                grad_x[:, j] = grad_phi[:, c_idx] * dp1 + grad_phi[:, c_idx + 1] * dp2

        if self.prior_fn is not None:
            m_v, m_g = self.prior_fn(Xq)
            val = val + m_v
            grad_x = grad_x + m_g
        return val, grad_x


class EikonalConeMeanGuide:
    """Nontrivial Geometric / Eikonal Distance-Cone Mean Prior (`green_response`):
    Shares the EXACT SAME `C^2` even reflecting collar warp `w(x)` and asymptotic free-space slope
    `sqrt(2 q_0 r)` as `V_0`, WITHOUT the `d`-dimensional Helmholtz/Bessel radial curvature `(d - 1)/r`.
    Supports:
      - `smooth_tau > 0.0` with softmin (`calibrate_nnls=False`, original smooth cone);
      - `calibrate_nnls=True` (36-point per-goal boundary NNLS calibration in desirability space, matching
        `BoxNeumannBesselBaseGuide` point-for-point!) with either `smooth_tau = 0.035` (matched smooth cone)
        or `smooth_tau = 0.0` (matched sharp cone with exact finite exterior slope!).
    """

    def __init__(
        self,
        spec: ProblemSpec,
        query: QueryTask,
        collar_delta: float = 0.22,
        smooth_tau: float = 0.035,
        calibrate_nnls: bool = False,
    ):
        self.r_scalar = spec.validate_cole_hopf_lmdp("EikonalConeMeanGuide", allow_scalar_r=True)
        self.spec = spec
        self.query = query
        self.d = spec.dim
        self.L = spec.half_width
        self.delta = float(collar_delta)
        self.tau = float(max(0.0, smooth_tau))
        self.calibrate_nnls = bool(calibrate_nnls)
        self.slope = float(np.sqrt(2.0 * spec.q0 * self.r_scalar))
        self.lam = spec.lam
        self.g_centers = np.array([g.center for g in query.goals], dtype=float)
        self.g_phis = np.array([g.phi for g in query.goals], dtype=float)
        self.g_radii = np.array([g.radius for g in query.goals], dtype=float)
        self.weights: Optional[np.ndarray] = None

        if self.calibrate_nnls:
            m_g = len(query.goals)
            rng = np.random.default_rng(17)
            coll_pts, coll_rhs = [], []
            n_per_goal = 36
            for j in range(m_g):
                dirs = rng.normal(size=(n_per_goal, self.d))
                dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
                pts_j = reflect_into_box(self.g_centers[j][None, :] + self.g_radii[j] * dirs, self.L)
                coll_pts.append(pts_j)
                coll_rhs.append(np.full(n_per_goal, np.exp(-self.g_phis[j] / self.lam)))
            P_coll = np.vstack(coll_pts)
            w_coll = np.concatenate(coll_rhs)
            Psi_coll, _ = self._eval_cone_modes(P_coll)
            c_nnls, _ = nnls(Psi_coll, w_coll)
            if np.all(c_nnls <= 1e-14):
                c_nnls = np.exp(-self.g_phis / self.lam)
            self.weights = np.maximum(c_nnls, 1e-12)

    def _eval_cone_modes(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        Xw, dw, _ = even_collar_warp_c2(X, self.L, self.delta)
        n_pts = len(Xw)
        m_g = len(self.g_centers)
        Psi = np.empty((n_pts, m_g), dtype=float)
        dPsi = np.empty((n_pts, m_g, self.d), dtype=float)
        kappa_eff = self.slope / self.lam

        for j in range(m_g):
            diff = Xw - self.g_centers[j][None, :]
            r = np.linalg.norm(diff, axis=1)
            rj = self.g_radii[j]
            s_pos = np.maximum(0.0, r - rj)
            if self.tau > 0.0:
                hyp = np.sqrt(s_pos ** 2 + self.tau ** 2)
                dist_sm = hyp - self.tau
                ds_dr = np.where(r > rj + 1e-12, s_pos / hyp, 0.0)
            else:
                dist_sm = s_pos
                ds_dr = np.where(r > rj + 1e-12, 1.0, 0.0)
            phi_val = np.exp(-kappa_eff * dist_sm)
            dphi_dr = -kappa_eff * phi_val * ds_dr
            unit_v = diff / np.maximum(r[:, None], 1e-12)
            Psi[:, j] = phi_val
            dPsi[:, j, :] = (dphi_dr[:, None] * unit_v) * dw
        return Psi, dPsi

    def val_and_grad(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X2 = np.atleast_2d(np.asarray(X, dtype=float))
        if self.calibrate_nnls and self.weights is not None:
            Psi, dPsi = self._eval_cone_modes(X2)
            Z0 = np.maximum(Psi @ self.weights, 1e-300)
            grad_Z0 = np.einsum("nmd,m->nd", dPsi, self.weights)
            val = -self.lam * np.log(Z0)
            grad = -self.lam * (grad_Z0 / Z0[:, None])
            return val, grad

        Xw, dw, _ = even_collar_warp_c2(X2, self.L, self.delta)
        n_pts = len(Xw)
        m_g = len(self.g_centers)
        E_mat = np.empty((n_pts, m_g), dtype=float)
        dE_mat = np.empty((n_pts, m_g, self.d), dtype=float)

        for j in range(m_g):
            diff = Xw - self.g_centers[j][None, :]
            r = np.linalg.norm(diff, axis=1)
            rj = self.g_radii[j]
            s_pos = np.maximum(0.0, r - rj)
            if self.tau > 0.0:
                hyp = np.sqrt(s_pos ** 2 + self.tau ** 2)
                dist_sm = hyp - self.tau
                ds_dr = np.where(r > rj + 1e-12, s_pos / hyp, 0.0)
            else:
                dist_sm = s_pos
                ds_dr = np.where(r > rj + 1e-12, 1.0, 0.0)
            E_mat[:, j] = self.g_phis[j] + self.slope * dist_sm
            unit_v = diff / np.maximum(r[:, None], 1e-12)
            dE_dw = (self.slope * ds_dr)[:, None] * unit_v
            dE_mat[:, j, :] = dE_dw * dw

        scaled = -E_mat / self.lam
        mx = np.max(scaled, axis=1, keepdims=True)
        ex = np.exp(scaled - mx)
        sum_ex = np.maximum(np.sum(ex, axis=1, keepdims=True), 1e-300)
        soft_w = ex / sum_ex
        val = -self.lam * (mx[:, 0] + np.log(sum_ex[:, 0]))
        grad = np.einsum("nm,nmd->nd", soft_w, dE_mat)
        return val, grad


class BoxNeumannBesselBaseGuide:
    """Even-Reflected `C^2` Boundary-Collar Helmholtz/Bessel Physics Mean Prior (`green_response`):
    Supports isotropic `R = r I` (`r > 0`) with explicit capability guard at entry!
    """

    def __init__(self, spec: ProblemSpec, query: QueryTask, collar_delta: float = 0.22):
        self.r_scalar = spec.validate_cole_hopf_lmdp("BoxNeumannBesselBaseGuide", allow_scalar_r=True)
        self.spec = spec
        self.query = query
        self.d = spec.dim
        self.L = spec.half_width
        self.delta = float(collar_delta)
        self.L0 = self.L - self.delta
        self.nu = 0.5 * self.d - 1.0
        self.lam = spec.lam  # == r_scalar * sigma^2
        self.kappa = float(np.sqrt(2.0 * spec.q0 / self.r_scalar) / (spec.sigma ** 2))
        self.g_centers = np.array([g.center for g in query.goals], dtype=float)
        self.g_phis = np.array([g.phi for g in query.goals], dtype=float)
        self.g_radii = np.array([g.radius for g in query.goals], dtype=float)
        self.base_denom = kv(self.nu, self.kappa * self.g_radii)

        m_g = len(query.goals)
        rng = np.random.default_rng(17)
        coll_pts, coll_rhs = [], []
        n_per_goal = 36
        for j in range(m_g):
            dirs = rng.normal(size=(n_per_goal, self.d))
            dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
            pts_j = reflect_into_box(self.g_centers[j][None, :] + self.g_radii[j] * dirs, self.L)
            coll_pts.append(pts_j)
            coll_rhs.append(np.full(n_per_goal, np.exp(-self.g_phis[j] / self.lam)))
        P_coll = np.vstack(coll_pts)
        w_coll = np.concatenate(coll_rhs)
        Psi_coll, _, _ = self._eval_collar_modes_and_lap(P_coll, need_lap=False)
        c_nnls, _ = nnls(Psi_coll, w_coll)
        if np.all(c_nnls <= 1e-14):
            c_nnls = np.exp(-self.g_phis / self.lam)
        self.weights = np.maximum(c_nnls, 1e-12)

    def _eval_collar_modes_and_lap(
        self, X: np.ndarray, need_lap: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
        Xw, dw, d2w = even_collar_warp_c2(X, self.L, self.delta)
        n_pts = len(Xw)
        m_g = len(self.g_centers)
        Psi = np.empty((n_pts, m_g), dtype=float)
        dPsi = np.empty((n_pts, m_g, self.d), dtype=float)
        lapPsi = np.empty((n_pts, m_g), dtype=float) if need_lap else None
        dw2 = dw ** 2

        for j in range(m_g):
            diff = Xw - self.g_centers[j][None, :]
            r = np.linalg.norm(diff, axis=1)
            rj = self.g_radii[j]
            r_eff = np.maximum(r, rj)
            kr = self.kappa * r_eff
            kv_nu = kv(self.nu, kr)
            kv_nu1 = kv(self.nu + 1.0, kr)
            ratio_r = (r_eff / rj) ** (-self.nu)
            phi_val = ratio_r * (kv_nu / self.base_denom[j])
            dphi_dr = -self.kappa * ratio_r * (kv_nu1 / self.base_denom[j])

            Psi[:, j] = phi_val
            outside = r > rj + 1e-12
            inv_r = 1.0 / np.maximum(r, 1e-12)
            unit_vec = diff * inv_r[:, None]
            dPsi_dtilde = np.where(outside[:, None], dphi_dr[:, None] * unit_vec, 0.0)
            dPsi[:, j, :] = dPsi_dtilde * dw

            if need_lap:
                d2phi_dr2 = (self.kappa ** 2) * phi_val - (self.d - 1.0) * inv_r * dphi_dr
                u2 = unit_vec ** 2
                d2Psi_dtilde2 = d2phi_dr2[:, None] * u2 + (dphi_dr * inv_r)[:, None] * (1.0 - u2)
                lap_j = np.sum(d2Psi_dtilde2 * dw2 + dPsi_dtilde * d2w, axis=1)
                lapPsi[:, j] = np.where(outside, lap_j, 0.0)

        return Psi, dPsi, lapPsi

    def val_and_grad(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X2 = np.atleast_2d(np.asarray(X, dtype=float))
        Psi, dPsi, _ = self._eval_collar_modes_and_lap(X2, need_lap=False)
        Z0 = np.maximum(Psi @ self.weights, 1e-300)
        grad_Z0 = np.einsum("nmd,m->nd", dPsi, self.weights)
        V0 = -self.lam * np.log(Z0)
        grad_V0 = -self.lam * (grad_Z0 / Z0[:, None])
        return V0, grad_V0

    def val_grad_and_base_pde_residual(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Exact base HJB residual for `R = r I`:
            `r_base(x) = q_0 + 0.5 * sigma^2 * Lap_x V_0(x) - (1 / (2 r)) * ||grad_x V_0(x)||^2`
                       `= q_0 - 0.5 * sigma^2 * lam * (Lap_x Z_0(x) / Z_0(x))`!
        """
        X2 = np.atleast_2d(np.asarray(X, dtype=float))
        X_fold = reflect_into_box(X2, self.L)
        in_collar_any = np.any(np.abs(X_fold) > self.L0, axis=1)
        if not np.any(in_collar_any):
            V0, grad_V0 = self.val_and_grad(X_fold)
            return V0, grad_V0, np.zeros(len(X2), dtype=float)

        Psi, dPsi, lapPsi = self._eval_collar_modes_and_lap(X_fold, need_lap=True)
        Z0 = np.maximum(Psi @ self.weights, 1e-300)
        grad_Z0 = np.einsum("nmd,m->nd", dPsi, self.weights)
        lap_Z0 = lapPsi @ self.weights
        V0 = -self.lam * np.log(Z0)
        grad_V0 = -self.lam * (grad_Z0 / Z0[:, None])
        r_base = self.spec.q0 - 0.5 * (self.spec.sigma ** 2) * self.lam * (lap_Z0 / Z0)
        r_base[~in_collar_any] = 0.0
        return V0, grad_V0, r_base

    def step_continuum_collar_residual(
        self, X_cur: np.ndarray, q_pert: np.ndarray, b_cur: np.ndarray, dt: float
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        V0, gv0, r_base = self.val_grad_and_base_pde_residual(X_cur)
        r_step = (r_base + q_pert + np.sum(b_cur * gv0, axis=1)) * dt
        return V0, gv0, r_step

    def step_discrete_telescoping_reference(
        self,
        X_cur: np.ndarray,
        V0_cur: np.ndarray,
        grad_V0_cur: np.ndarray,
        q_pert: np.ndarray,
        X_reflected_next: np.ndarray,
        dW_step: np.ndarray,
        dt: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        u0 = -grad_V0_cur / self.r_scalar
        q_tot = self.spec.q0 + q_pert
        V0_next, _ = self.val_and_grad(X_reflected_next)
        rtilde = (
            (q_tot + 0.5 * self.r_scalar * np.sum(u0 ** 2, axis=1)) * dt
            + self.r_scalar * self.spec.sigma * np.sum(u0 * dW_step, axis=1)
            + (V0_next - V0_cur)
        )
        return rtilde, V0_next


def fit_gp_value_with_prior(
    spec: ProblemSpec,
    query: QueryTask,
    X_all: np.ndarray,
    y_total_v: np.ndarray,
    noise_vec: np.ndarray,
    prior_mode: str = "helmholtz_bessel",
    ell_gp: Optional[float] = None,
) -> dict:
    """Fits `MirrorNeumannMatern52GP` on IDENTICAL frozen total-value labels `(X_all, y_total_v)`
    under different mean priors (`"helmholtz_bessel"`, `"eikonal_cone"`, `"zero_mean"`), isolating
    the exact effect of the analytical physics mean prior with ZERO label-continuation drift!
    """
    r_sc = spec.validate_cole_hopf_lmdp("fit_gp_value_with_prior", allow_scalar_r=True)
    L = spec.half_width
    ell = (0.48 if spec.dim <= 4 else 0.68) if ell_gp is None else ell_gp

    if prior_mode == "helmholtz_bessel":
        prior_obj = BoxNeumannBesselBaseGuide(spec, query)
        prior_fn = prior_obj.val_and_grad
    elif prior_mode == "eikonal_cone":
        prior_obj = EikonalConeMeanGuide(spec, query)
        prior_fn = prior_obj.val_and_grad
    elif prior_mode == "matched_smooth_cone":
        prior_obj = EikonalConeMeanGuide(spec, query, smooth_tau=0.035, calibrate_nnls=True)
        prior_fn = prior_obj.val_and_grad
    elif prior_mode == "matched_sharp_cone":
        prior_obj = EikonalConeMeanGuide(spec, query, smooth_tau=0.0, calibrate_nnls=True)
        prior_fn = prior_obj.val_and_grad
    elif prior_mode == "zero_mean":
        prior_obj = None
        prior_fn = None
    else:
        raise ValueError(f"Unknown prior_mode: {prior_mode}")

    gp = MirrorNeumannMatern52GP(
        X_all, y_total_v, L, length_scale=ell, noise_vec=noise_vec, prior_val_and_grad_fn=prior_fn
    )

    def raw_value_and_grad(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X2 = reflect_into_box(np.atleast_2d(X), L)
        return gp.predict_val_and_grad(X2)

    def value_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        val, _ = raw_value_and_grad(X2)
        hit, phi_u = eval_goal_union(X2, query.goals)
        if np.any(hit):
            val[hit] = phi_u[hit]
        return val

    def policy_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        _, grad_v = raw_value_and_grad(X2)
        u = -grad_v / r_sc
        hit, _ = eval_goal_union(X2, query.goals)
        if np.any(hit):
            u[hit] = 0.0
        return u

    return {
        "gp": gp,
        "prior_mode": prior_mode,
        "prior_obj": prior_obj,
        "raw_value_and_grad": raw_value_and_grad,
        "value_fn": value_fn,
        "policy": policy_fn,
    }


def solve_highd_fk_distillation(
    spec: ProblemSpec,
    km: KrigingWorldModel,
    query: QueryTask,
    n_interior_anchors: int = 88,
    n_boundary_per_goal: int = 64,
    n_mc_paths: int = 64,
    n_steps_fk: int = 75,
    dt_fk: float = 0.045,
    n_continuation_rounds: int = 2,
    residual_mode: str = "continuum_collar",
    prior_mode: str = "helmholtz_bessel",  # "helmholtz_bessel", "eikonal_cone", or "zero_mean"
    guided_proposal: bool = True,
    seed: int = 101,
    design_seed: Optional[int] = None,
    mc_seed: Optional[int] = None,
) -> dict:
    """Unified High-D Reflected Girsanov-FK Value Distillation (`green_response`, `ddd19c5 Stage E`):
      - Explicit entry guard via `spec.validate_cole_hopf_lmdp`;
      - Decouples `design_seed` (Sobol/corridor anchors + boundary collocation) from `mc_seed`
        (Feynman-Kac Brownian trajectories) when supplied;
      - Exports exact recorder-owned `budget_counters` (`n_interior_actual`, `n_boundary_actual`,
        `n_gp_rows_total`, `n_fk_paths_launched_actual`, `n_fk_active_steps_total`, etc.)!
    """
    r_sc = spec.validate_cole_hopf_lmdp("solve_highd_fk_distillation", allow_scalar_r=True)
    t0 = time.perf_counter()
    d = spec.dim
    lam = spec.lam
    L = spec.half_width
    d_seed = int(seed if design_seed is None else design_seed)
    m_seed = int(seed if mc_seed is None else mc_seed)

    base = BoxNeumannBesselBaseGuide(spec, query)
    eik_prior = None
    if prior_mode == "eikonal_cone":
        eik_prior = EikonalConeMeanGuide(spec, query)
    elif prior_mode == "matched_smooth_cone":
        eik_prior = EikonalConeMeanGuide(spec, query, smooth_tau=0.035, calibrate_nnls=True)
    elif prior_mode == "matched_sharp_cone":
        eik_prior = EikonalConeMeanGuide(spec, query, smooth_tau=0.0, calibrate_nnls=True)
    rng_design = np.random.default_rng(d_seed)
    rng_mc = rng_design if (design_seed is None and mc_seed is None) else np.random.default_rng(m_seed + 4099)

    bnd_pts, bnd_phi, bnd_v0 = [], [], []
    sobol_b = qmc.Sobol(d=d, scramble=True, seed=d_seed + 11)
    for g in query.goals:
        gc = np.asarray(g.center, dtype=float)
        u_sob = np.clip(sobol_b.random(n_boundary_per_goal), 1e-6, 1.0 - 1e-6)
        dirs = norm.ppf(u_sob)
        dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
        pj = np.clip(gc[None, :] + (g.radius + 1e-8) * dirs, -L + 1e-4, L - 1e-4)
        in_other, phi_u = eval_goal_union(pj, query.goals)
        target_phi = np.where(in_other, np.minimum(phi_u, g.phi), g.phi)
        v0_j, _ = base.val_and_grad(pj)
        bnd_pts.append(pj)
        bnd_phi.append(target_phi)
        bnd_v0.append(v0_j)
    X_bnd = np.vstack(bnd_pts)
    phi_bnd = np.concatenate(bnd_phi)
    v0_bnd = np.concatenate(bnd_v0)

    sobol = qmc.Sobol(d=d, scramble=True, seed=d_seed)
    n_sob = n_interior_anchors // 2
    X_sob = (sobol.random(n_sob) * 2.0 - 1.0) * 1.20
    if d > 2:
        X_sob[:, 2:] *= 0.78
    starts_arr = np.asarray(query.start_points, dtype=float)
    g_centers = np.array([g.center for g in query.goals], dtype=float)
    cor_pts = []
    for k in range(n_interior_anchors - n_sob):
        s_pt = starts_arr[k % len(starts_arr)]
        g_pt = g_centers[k % len(g_centers)]
        al_w = rng_design.uniform(0.05, 0.94)
        pt = (1.0 - al_w) * s_pt + al_w * g_pt + rng_design.normal(0.0, 0.25, size=d)
        cor_pts.append(np.clip(pt, -1.22, 1.22))
    X_int_raw = np.vstack([starts_arr, X_sob, np.array(cor_pts)])
    in_g_int, _ = eval_goal_union(X_int_raw, [GoalBall(g.center, g.phi, g.radius + 0.025) for g in query.goals])
    X_int = X_int_raw[~in_g_int]
    n_int = len(X_int)
    v0_int, _ = base.val_and_grad(X_int)

    half_m = max(n_mc_paths // 2, 1)
    M_eff = 2 * half_m
    sqrt_dt = np.sqrt(dt_fk)
    pos = np.repeat(X_int[:, None, :], M_eff, axis=1)
    v0_cur = np.repeat(v0_int[:, None], M_eff, axis=1)
    alive = np.ones((n_int, M_eff), dtype=bool)
    acc_tilde = np.zeros((n_int, M_eff), dtype=float)
    term_res = np.zeros((n_int, M_eff), dtype=float)
    collar_steps = 0
    total_steps = 0

    for _st in range(n_steps_fk):
        if not np.any(alive):
            break
        z_half = rng_mc.normal(0.0, sqrt_dt, size=(n_int, half_m, d))
        dW_step = np.concatenate([z_half, -z_half], axis=1)

        ai, aj = np.where(alive)
        pts_a = pos[ai, aj]
        dw_a = dW_step[ai, aj]
        total_steps += len(pts_a)
        collar_steps += int(np.sum(np.any(np.abs(pts_a) > base.L0, axis=1)))

        q_pert = km.predict_q(pts_a) + eval_hazard_features(pts_a, query.local_hazards)
        b_hat = km.predict_b(pts_a)

        if guided_proposal:
            if residual_mode == "continuum_collar":
                _, gv0, r_step = base.step_continuum_collar_residual(pts_a, q_pert, b_hat, dt_fk)
                u_prop = -gv0 / r_sc
                x_next = reflect_into_box(pts_a + (b_hat + u_prop) * dt_fk + spec.sigma * dw_a, L)
                acc_tilde[ai, aj] += r_step
            elif residual_mode == "discrete_telescoping":
                v0_a = v0_cur[ai, aj]
                _, gv0 = base.val_and_grad(pts_a)
                u_prop = -gv0 / r_sc
                x_next = reflect_into_box(pts_a + (b_hat + u_prop) * dt_fk + spec.sigma * dw_a, L)
                r_step, v0_n = base.step_discrete_telescoping_reference(pts_a, v0_a, gv0, q_pert, x_next, dw_a, dt_fk)
                acc_tilde[ai, aj] += r_step
                v0_cur[ai, aj] = v0_n
            else:
                raise ValueError(f"Unknown residual_mode: {residual_mode}")
        else:
            v0_a = v0_cur[ai, aj]
            x_next = reflect_into_box(pts_a + b_hat * dt_fk + spec.sigma * dw_a, L)
            v0_n, _ = base.val_and_grad(x_next)
            acc_tilde[ai, aj] += (spec.q0 + q_pert) * dt_fk + (v0_n - v0_a)
            v0_cur[ai, aj] = v0_n

        pos[ai, aj] = x_next
        hit_post, phi_post = eval_goal_union(x_next, query.goals)
        if np.any(hit_post):
            hl = np.flatnonzero(hit_post)
            v0_hit, _ = base.val_and_grad(x_next[hl])
            term_res[ai[hl], aj[hl]] = phi_post[hl] - v0_hit
            alive[ai[hl], aj[hl]] = False

    survivor_frac = float(np.mean(alive))
    ell_gp = 0.48 if d <= 4 else 0.68
    X_all = np.vstack([X_int, X_bnd])
    noise_vec = np.concatenate([np.full(n_int, 2.5e-3), np.full(len(X_bnd), 1e-7)])

    def _fk_stats(emat: np.ndarray, alive_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        mx = np.max(emat, axis=1, keepdims=True)
        w = np.exp(emat - mx)
        w_sum = np.maximum(np.sum(w, axis=1), 1e-300)
        ess_vec = (w_sum ** 2) / np.maximum(np.sum(w ** 2, axis=1), 1e-300)
        weighted_surv_mass = float(np.mean(np.sum(w * alive_mask, axis=1) / w_sum))
        dv = -lam * (mx[:, 0] + np.log(np.maximum(np.mean(w, axis=1), 1e-300)))
        return dv, ess_vec, weighted_surv_mass

    tail_dv = np.zeros_like(term_res)
    dv_cur, ess_vec, weighted_tail_mass = _fk_stats(-(acc_tilde + np.where(alive, tail_dv, term_res)) / lam, alive)
    cont_diffs = []
    ai_s, aj_s = np.where(alive)
    v0_surv = base.val_and_grad(pos[ai_s, aj_s])[0] if len(ai_s) > 0 else np.empty(0)

    if prior_mode == "helmholtz_bessel":
        prior_fn = base.val_and_grad
    elif prior_mode in ("eikonal_cone", "matched_smooth_cone", "matched_sharp_cone"):
        assert eik_prior is not None
        prior_fn = eik_prior.val_and_grad
    elif prior_mode == "zero_mean":
        prior_fn = None
    else:
        raise ValueError(f"Unknown prior_mode: {prior_mode}")

    gp_model: Optional[MirrorNeumannMatern52GP] = None
    y_tot_final = np.concatenate([v0_int + dv_cur, phi_bnd])
    n_gp_fits = 0
    for _c_it in range(max(1, n_continuation_rounds + 1)):
        y_tot_final = np.concatenate([v0_int + dv_cur, phi_bnd])
        gp_model = MirrorNeumannMatern52GP(
            X_all, y_tot_final, L, length_scale=ell_gp, noise_vec=noise_vec, prior_val_and_grad_fn=prior_fn
        )
        n_gp_fits += 1
        if _c_it == n_continuation_rounds or len(ai_s) == 0:
            break
        pred_tot_surv = gp_model.predict_val_and_grad(pos[ai_s, aj_s])[0]
        tail_dv[ai_s, aj_s] = pred_tot_surv - v0_surv
        dv_next, ess_vec, weighted_tail_mass = _fk_stats(-(acc_tilde + np.where(alive, tail_dv, term_res)) / lam, alive)
        cont_diffs.append(float(np.max(np.abs(dv_next - dv_cur))))
        dv_cur = dv_next

    assert gp_model is not None

    def raw_value_and_grad(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X2 = reflect_into_box(np.atleast_2d(X), L)
        return gp_model.predict_val_and_grad(X2)

    def value_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        val, _ = raw_value_and_grad(X2)
        hit, phi_u = eval_goal_union(X2, query.goals)
        if np.any(hit):
            val[hit] = phi_u[hit]
        return val

    def policy_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        _, grad_v = raw_value_and_grad(X2)
        u = -grad_v / r_sc
        hit, _ = eval_goal_union(X2, query.goals)
        if np.any(hit):
            u[hit] = 0.0
        return u

    budget_counters = {
        "n_interior_proposed_nominal": int(n_interior_anchors),
        "n_start_anchors_added": int(len(starts_arr)),
        "n_near_goal_filtered": int(np.sum(in_g_int)),
        "n_interior_actual": int(n_int),
        "n_boundary_actual": int(len(X_bnd)),
        "n_gp_rows_total": int(len(X_all)),
        "mc_paths_per_anchor_effective": int(M_eff),
        "n_fk_paths_launched_actual": int(n_int * M_eff),
        "n_fk_active_steps_total": int(total_steps),
        "n_world_q_queries": int(total_steps),
        "n_world_b_queries": int(total_steps),
        "n_continuation_gp_fits": int(n_gp_fits),
    }

    return {
        "value_fn": value_fn,
        "raw_value_and_grad": raw_value_and_grad,
        "policy": policy_fn,
        "base": base,
        "gp": gp_model,
        "frozen_X_all": X_all,
        "frozen_y_total_v": y_tot_final,
        "frozen_noise_vec": noise_vec,
        "budget_counters": budget_counters,
        "plan_ms": 1000.0 * (time.perf_counter() - t0),
        "survivor_fraction": survivor_frac,
        "weighted_tail_mass": weighted_tail_mass,
        "collar_step_fraction": float(collar_steps / max(total_steps, 1)),
        "mean_ess": float(np.mean(ess_vec)),
        "min_ess": float(np.min(ess_vec)),
        "median_ess": float(np.median(ess_vec)),
        "continuation_max_diffs": cont_diffs,
    }


def make_antithetic_centered_pimc_policy(
    spec: ProblemSpec,
    km: KrigingWorldModel,
    query: QueryTask,
    n_particles: int = 36,
    horizon_steps: int = 16,
    dt_mpc: float = 0.045,
    seed: int = 777,
) -> Tuple[Callable[[np.ndarray], np.ndarray], float, dict]:
    r_sc = spec.validate_cole_hopf_lmdp("make_antithetic_centered_pimc_policy", allow_scalar_r=True)
    t0 = time.perf_counter()
    lam = spec.lam
    L = spec.half_width
    sqrt_dt = np.sqrt(dt_mpc)
    half_m = max(n_particles // 2, 1)
    M_eff = 2 * half_m
    base = BoxNeumannBesselBaseGuide(spec, query)
    rng = np.random.default_rng(seed)
    init_ms = 1000.0 * (time.perf_counter() - t0)
    ess_log: List[float] = []

    def policy_fn(X: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X)
        n_b = len(X2)
        d = spec.dim
        done0, _ = eval_goal_union(X2, query.goals)
        _, gv0_start, r_base0 = base.val_grad_and_base_pde_residual(X2)
        u_nom0 = -gv0_start / r_sc

        z0_half = rng.normal(0.0, sqrt_dt, size=(n_b, half_m, d))
        eps0 = np.concatenate([z0_half, -z0_half], axis=1)
        pos = np.repeat(X2[:, None, :], M_eff, axis=1)
        alive = np.broadcast_to((~done0)[:, None], (n_b, M_eff)).copy()
        cost_acc = np.zeros((n_b, M_eff), dtype=float)

        for st in range(horizon_steps):
            if not np.any(alive):
                break
            if st == 0:
                dw_full = eps0
            else:
                zh = rng.normal(0.0, sqrt_dt, size=(n_b, half_m, d))
                dw_full = np.concatenate([zh, -zh], axis=1)

            ai, aj = np.where(alive)
            pts = pos[ai, aj]
            dw_a = dw_full[ai, aj]
            q_pert = km.predict_q(pts) + eval_hazard_features(pts, query.local_hazards)
            b_hat = km.predict_b(pts)

            if st == 0:
                gv = np.repeat(gv0_start[:, None, :], M_eff, axis=1)[ai, aj]
                rb = np.repeat(r_base0[:, None], M_eff, axis=1)[ai, aj]
                r_step = (rb + q_pert + np.sum(b_hat * gv, axis=1)) * dt_mpc
            else:
                _, gv, r_step = base.step_continuum_collar_residual(pts, q_pert, b_hat, dt_mpc)

            u_prop = -gv / r_sc
            x_next = reflect_into_box(pts + (b_hat + u_prop) * dt_mpc + spec.sigma * dw_a, L)
            cost_acc[ai, aj] += r_step
            pos[ai, aj] = x_next

            hp, pp = eval_goal_union(x_next, query.goals)
            if np.any(hp):
                hl = np.flatnonzero(hp)
                v0_h, _ = base.val_and_grad(x_next[hl])
                cost_acc[ai[hl], aj[hl]] += pp[hl] - v0_h
                alive[ai[hl], aj[hl]] = False

        exps = -cost_acc / lam
        exps -= np.max(exps, axis=1, keepdims=True)
        w_raw = np.exp(exps)
        w_sum = np.maximum(np.sum(w_raw, axis=1, keepdims=True), 1e-30)
        w = w_raw / w_sum
        active_rows = ~done0
        if np.any(active_rows):
            ess_step = 1.0 / np.maximum(np.sum(w[active_rows] ** 2, axis=1), 1e-30)
            ess_log.append(float(np.mean(ess_step)))
        w_centered = w - (1.0 / M_eff)
        # Repaired scalar-R innovation (`GPT6 85e2323 Audit Finding 2.5`, Kappen & Ruiz 2016 Eq. 7):
        # For `dX = (b + u) dt + sigma dW`, `c_u = 0.5 * r ||u||^2`, `lam = r * sigma^2`, and
        # `eps0 ~ N(0, dt * I)`, `r` cancels identically between `lam = r * sigma^2` and `-grad(V)/r`,
        # leaving `du = (sigma / dt) * E_w[dW_0]`!
        du = (spec.sigma / dt_mpc) * np.einsum("bm,bmd->bd", w_centered, eps0)
        u = u_nom0 + du
        if np.any(done0):
            u[done0] = 0.0
        return u

    diag = {"ess_log": ess_log, "n_particles": M_eff, "horizon_steps": horizon_steps}
    return policy_fn, init_ms, diag


def build_kinetic_lqr_base_guide(
    goal_pos: Sequence[float],
    q0: float = 0.35,
    gamma: float = 0.55,
    vel_weight: float = 0.06,
) -> Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray]]:
    A = np.array([
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, -gamma, 0.0],
        [0.0, 0.0, 0.0, -gamma],
    ])
    B = np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    Q = np.diag([q0, q0, vel_weight, vel_weight])
    R = np.eye(2)
    P = solve_continuous_are(A, B, Q, R)
    xg = np.array([goal_pos[0], goal_pos[1], 0.0, 0.0], dtype=float)

    def v0_and_grad(X4: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        X2 = np.atleast_2d(X4)
        rel = X2 - xg[None, :]
        g = rel @ P
        v = 0.5 * np.einsum("ni,ni->n", rel, g)
        return v, g

    return v0_and_grad


def solve_kinetic_underactuated_greenres(
    km_pos: KrigingWorldModel,
    goal_pos: Tuple[float, float] = (0.75, 0.65),
    r_pos: float = 0.28,
    r_vel: float = 0.85,
    half_width: float = 1.65,
    v_max: float = 3.5,
    sigma: float = 0.42,
    q0: float = 0.35,
    gamma: float = 0.55,
    inward_boundary: bool = True,
    anisotropic_kernel: bool = True,
    extra_braking_anchors: bool = True,
    n_continuation_rounds: int = 6,
    seed: int = 404,
) -> dict:
    """Scoped Empirical 4D Kinetic Double-Integrator Extension (`green_response`):
      - Replaces hardcoded `0.0` jump assertion with an INDEPENDENT floating-point path-action vs
        endpoint-telescoping discrepancy check (`measured_telescoping_discrepancy`);
      - Uses 6 continuation rounds by default (eliminating stiff narrow-barrier early-stop residual);
      - Exposes `value_fn` directly and logs honest velocity-cap & specular-wall mismatch diagnostics.
    """
    t0 = time.perf_counter()
    lam = sigma ** 2
    v0_fn = build_kinetic_lqr_base_guide(goal_pos, q0=q0, gamma=gamma)
    gp_c = np.asarray(goal_pos, dtype=float)

    rng_bnd = np.random.default_rng(seed + 1)
    rng_brk = np.random.default_rng(seed + 2)
    rng_fk = np.random.default_rng(seed + 3)

    n_bnd = 64
    ang_p = np.linspace(0.0, 2.0 * np.pi, n_bnd, endpoint=False)
    n_out = np.column_stack([np.cos(ang_p), np.sin(ang_p)])
    p_bnd = gp_c[None, :] + (r_pos + 1e-6) * n_out
    v_mag = rng_bnd.uniform(0.08, 0.92 * r_vel, size=(n_bnd, 1))
    tang = np.column_stack([-n_out[:, 1], n_out[:, 0]]) * rng_bnd.uniform(-0.35, 0.35, size=(n_bnd, 1))
    if inward_boundary:
        v_bnd = -n_out * v_mag + tang
    else:
        sgn = np.where((np.arange(n_bnd) % 2) == 0, -1.0, 1.0)[:, None]
        v_bnd = sgn * n_out * v_mag + tang
    v_nrm = np.linalg.norm(v_bnd, axis=1, keepdims=True)
    v_bnd = np.where(v_nrm > 0.96 * r_vel, v_bnd * (0.96 * r_vel / np.maximum(v_nrm, 1e-12)), v_bnd)
    X_bnd = np.hstack([p_bnd, v_bnd])
    y_bnd = np.zeros(len(X_bnd), dtype=float)  # Total V target on boundary is 0.0 (`prior_fn` handles `-V0`!)

    sob = qmc.Sobol(d=4, scramble=True, seed=seed + 10)
    u_s = sob.random(64) * 2.0 - 1.0
    X_base_int = np.column_stack([
        u_s[:, 0] * 1.25, u_s[:, 1] * 1.25,
        u_s[:, 2] * 1.35, u_s[:, 3] * 1.35,
    ])
    starts_ref = np.array([[-0.85, -0.75, 0.0, 0.0], [-0.70, 0.80, 0.0, 0.0]])
    if extra_braking_anchors:
        rad_b = rng_brk.uniform(r_pos + 0.04, r_pos + 0.45, size=24)
        th_b = rng_brk.uniform(0.0, 2.0 * np.pi, size=24)
        pb = np.clip(gp_c[None, :] + rad_b[:, None] * np.column_stack([np.cos(th_b), np.sin(th_b)]), -1.55, 1.55)
        vb = rng_brk.uniform(-1.1, 1.1, size=(24, 2))
        X_int_cand = np.vstack([starts_ref, X_base_int, np.hstack([pb, vb])])
    else:
        X_int_cand = np.vstack([starts_ref, X_base_int])

    in_goal_i = (np.linalg.norm(X_int_cand[:, :2] - gp_c[None, :], axis=1) <= r_pos + 0.02) & (
        np.linalg.norm(X_int_cand[:, 2:4], axis=1) <= r_vel
    )
    X_int = X_int_cand[~in_goal_i]
    n_int = len(X_int)
    v0_init = v0_fn(X_int)[0]

    M_eff = 48
    half_m = M_eff // 2
    dt_f = 0.04
    sq = np.sqrt(dt_f)
    pos4 = np.repeat(X_int[:, None, :], M_eff, axis=1)
    v0_cur = np.repeat(v0_init[:, None], M_eff, axis=1)
    alive = np.ones((n_int, M_eff), dtype=bool)
    acc_tilde = np.zeros((n_int, M_eff), dtype=float)
    raw_action_only = np.zeros((n_int, M_eff), dtype=float)  # Independent non-telescoped path action!
    term_res = np.zeros((n_int, M_eff), dtype=float)
    wall_bounces = 0
    vel_clips = 0

    for _st in range(90):
        if not np.any(alive):
            break
        zh = rng_fk.normal(0.0, sq, size=(n_int, half_m, 2))
        dw = np.concatenate([zh, -zh], axis=1)
        ai, aj = np.where(alive)
        x_a = pos4[ai, aj]
        p_a = x_a[:, :2]
        v_a = x_a[:, 2:4]
        dw_a = dw[ai, aj]
        v0_a = v0_cur[ai, aj]

        _, gv0 = v0_fn(x_a)
        u0 = -gv0[:, 2:4]
        qp = km_pos.predict_q(p_a)
        bh = km_pos.predict_b(p_a)

        p_raw = p_a + v_a * dt_f
        v_raw = v_a + (-gamma * v_a + bh + u0) * dt_f + sigma * dw_a
        p_next, v_next, w_hit, v_cl = reflect_kinetic_into_box(p_raw, v_raw, half_width, v_max)
        wall_bounces += int(np.sum(w_hit))
        vel_clips += int(np.sum(v_cl))

        x_next = np.hstack([p_next, v_next])
        v0_n, _ = v0_fn(x_next)

        q_tot_step = q0 + qp + 0.06 * np.sum(v_a ** 2, axis=1)
        step_act = (q_tot_step + 0.5 * np.sum(u0 ** 2, axis=1)) * dt_f + sigma * np.sum(u0 * dw_a, axis=1)
        raw_action_only[ai, aj] += step_act
        acc_tilde[ai, aj] += step_act + (v0_n - v0_a)
        pos4[ai, aj] = x_next
        v0_cur[ai, aj] = v0_n

        hit = (np.linalg.norm(p_next - gp_c[None, :], axis=1) <= r_pos) & (np.linalg.norm(v_next, axis=1) <= r_vel)
        if np.any(hit):
            hl = np.flatnonzero(hit)
            term_res[ai[hl], aj[hl]] = 0.0 - v0_n[hl]
            alive[ai[hl], aj[hl]] = False

    # Independent endpoint telescoping check (`pos4` holds exact stopping/final state of every particle!):
    v0_stop = v0_fn(pos4.reshape(-1, 4))[0].reshape(n_int, M_eff)
    independent_endpoint_acc = raw_action_only + (v0_stop - v0_init[:, None])
    measured_telescoping_discrepancy = float(np.max(np.abs(acc_tilde - independent_endpoint_acc)))

    surv_frac = float(np.mean(alive))
    ell_vec = np.array([0.42, 0.42, 0.90, 0.90]) if anisotropic_kernel else np.full(4, 0.68)
    X_all = np.vstack([X_int, X_bnd])
    nv = np.concatenate([np.full(n_int, 3e-3), np.full(len(X_bnd), 1e-6)])

    def _lme_ua(emat: np.ndarray) -> Tuple[np.ndarray, float, float]:
        mx = np.max(emat, axis=1, keepdims=True)
        w = np.exp(emat - mx)
        ws = np.maximum(np.sum(w, axis=1), 1e-300)
        ess = float(np.mean((ws ** 2) / np.maximum(np.sum(w ** 2, axis=1), 1e-300)))
        wtail = float(np.mean(np.sum(w * alive, axis=1) / ws))
        return -lam * (mx[:, 0] + np.log(np.maximum(np.mean(w, axis=1), 1e-300))), ess, wtail

    tail = np.zeros_like(term_res)
    dv_cur, mean_ess, wtail = _lme_ua(-(acc_tilde + np.where(alive, tail, term_res)) / lam)
    ai_s, aj_s = np.where(alive)
    v0_surv = v0_stop[ai_s, aj_s] if len(ai_s) > 0 else np.empty(0)
    cont_diffs = []
    gp_ua: Optional[MirrorNeumannMatern52GP] = None

    for _it in range(n_continuation_rounds + 1):
        y_tot_ua = np.concatenate([v0_init + dv_cur, y_bnd])
        gp_ua = MirrorNeumannMatern52GP(
            X_all, y_tot_ua, half_width,
            length_scale=ell_vec, noise_vec=nv, neumann_axes=(),
            prior_val_and_grad_fn=v0_fn,
        )
        if _it == n_continuation_rounds or len(ai_s) == 0:
            break
        pred_tot = gp_ua.predict_val_and_grad(pos4[ai_s, aj_s])[0]
        tail[ai_s, aj_s] = pred_tot - v0_surv
        dv_next, mean_ess, wtail = _lme_ua(-(acc_tilde + np.where(alive, tail, term_res)) / lam)
        cont_diffs.append(float(np.max(np.abs(dv_next - dv_cur))))
        dv_cur = dv_next

    assert gp_ua is not None

    def value_fn(X4: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X4)
        val, _ = gp_ua.predict_val_and_grad(X2)
        hit = (np.linalg.norm(X2[:, :2] - gp_c[None, :], axis=1) <= r_pos) & (
            np.linalg.norm(X2[:, 2:4], axis=1) <= r_vel
        )
        if np.any(hit):
            val[hit] = 0.0
        return val

    def raw_value_fn(X4: np.ndarray) -> np.ndarray:
        return gp_ua.predict_val_and_grad(np.atleast_2d(X4))[0]

    def policy_fn(X4: np.ndarray) -> np.ndarray:
        X2 = np.atleast_2d(X4)
        _, g_tot = gp_ua.predict_val_and_grad(X2)
        u = -g_tot[:, 2:4]
        hit = (np.linalg.norm(X2[:, :2] - gp_c[None, :], axis=1) <= r_pos) & (
            np.linalg.norm(X2[:, 2:4], axis=1) <= r_vel
        )
        if np.any(hit):
            u[hit] = 0.0
        return u

    # Honest boundary & specular scope diagnostics (`GPT6 kinetic_v4_boundary_and_tail_probe.py`):
    th_chk = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    dirs_chk = np.column_stack([np.cos(th_chk), np.sin(th_chk)])
    X_inw_chk = np.hstack([gp_c[None, :] + (r_pos + 1e-6) * dirs_chk, -0.4 * dirs_chk])
    X_vcap_chk = np.hstack([np.broadcast_to(gp_c, (64, 2)), (r_vel + 1e-4) * dirs_chk])
    X_wall_p = np.column_stack([np.full(64, half_width), np.linspace(-1.1, 1.1, 64), np.full(64, 0.6), np.linspace(-0.8, 0.8, 64)])
    X_wall_m = X_wall_p.copy(); X_wall_m[:, 2] *= -1.0

    inw_rms = float(np.sqrt(np.mean(raw_value_fn(X_inw_chk) ** 2)))
    vcap_rms = float(np.sqrt(np.mean(raw_value_fn(X_vcap_chk) ** 2)))
    spec_wall_rms = float(np.sqrt(np.mean((raw_value_fn(X_wall_p) - raw_value_fn(X_wall_m)) ** 2)))

    return {
        "policy": policy_fn,
        "value_fn": value_fn,
        "raw_value_fn": raw_value_fn,
        "lqr_base_fn": v0_fn,
        "scope_grade": "empirical_extension_not_boundary_exact",
        "plan_ms": 1000.0 * (time.perf_counter() - t0),
        "fk_survivor_fraction": surv_frac,
        "weighted_tail_mass": wtail,
        "mean_ess": mean_ess,
        "wall_bounce_events": wall_bounces,
        "velocity_clip_events": vel_clips,
        "measured_telescoping_discrepancy": measured_telescoping_discrepancy,
        "continuation_max_diffs": cont_diffs,
        "scope_diagnostics": {
            "incoming_pos_boundary_raw_rms": inw_rms,
            "unanchored_vel_cap_boundary_raw_rms": vcap_rms,
            "specular_wall_pair_raw_rms": spec_wall_rms,
        },
    }
