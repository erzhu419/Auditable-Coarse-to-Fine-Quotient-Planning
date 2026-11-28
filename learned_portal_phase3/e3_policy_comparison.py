"""Replay the frozen E3 policy deliveries without evaluating a controlled trajectory."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[1]
OLD_V3_COMMIT = "67532c91d6c43a32d0f4d0277ad28cd059e5a28b"
METHODS = ("SPQL", "Uncompressed_PAC", "PlugIn_CE", "Scalar_Portal_Ablation",
           "SVD_Resolvent_Ablation", "Sampled_Desirability_TD", "SPQL_UniformPortals")
INPUTS = ("X_curr", "X_next", "q_obs", "landmarks", "landmark_running_q")
TOL = 1e-12
FROZEN_V3 = "p3_v3_r747_delivery_verified_results.json"
PACKAGES = ("green_response", "quotient_phase2", "learned_portal_phase3")


def goal_id(gm):
    return hashlib.sha256(np.flatnonzero(gm).astype("<i8").tobytes()).hexdigest()


def csr_id(policy):
    ordered = policy.sorted_indices()
    h = hashlib.sha256()
    for values, dtype in ((ordered.indptr, "<i8"), (ordered.indices, "<i8"), (ordered.data, "<f8")):
        h.update(np.asarray(values, dtype=dtype).tobytes())
    return h.hexdigest()


def _dump(repo, directory, seeds):
    """Run this checkout's benchmark and capture the policy at its control adapter."""
    sys.path.insert(0, str(repo))
    from learned_portal_phase3 import continuous_manifold_spql as benchmark

    original_build = benchmark.build_voronoi_quotient_from_continuous_trajectories
    def build(x, next_x, q, **kwargs):
        result = original_build(x, next_x, q, **kwargs)
        arrays.update(X_curr=x, X_next=next_x, q_obs=q, landmarks=result[0])
        return result

    def capture(landmarks, tree, policy, gm, goal_center, dt, u_clip, landmark_running_q, **kwargs):
        if policy is None:
            raise ValueError("No policy delivered at the continuous control adapter")
        arrays["landmark_running_q"] = landmark_running_q
        delivered.append((goal_id(gm), goal_center.tolist(), policy.tocsr().sorted_indices()))
        # The rollout hook below never calls a controller.
        return None

    def skip_rollout(*args, **kwargs):
        # These placeholders are consumed only by the unused benchmark summary.
        return dict(mean_cost=np.nan, success_rate=np.nan, collision_audit_performed=False,
                    blocked_segments=0, exact_chord_hits=0, total_segments=0)

    benchmark.build_voronoi_quotient_from_continuous_trajectories = build
    benchmark.make_continuous_control_from_landmark_policy = capture
    benchmark.evaluate_continuous_policy_rollouts = skip_rollout
    for seed in seeds:
        arrays, delivered = {}, []
        run = benchmark.run_single_continuous_rotated_map_benchmark(
            seed, n_explore_steps=30600, n_goals=12, verify_zero_tunneling=True,
            include_uniform_portal_spql=True)
        rows = []
        for ev, (goal, center, policy) in zip(run["task_events"], delivered, strict=True):
            key = f"t{ev['task_index']}_{ev['method_id']}"
            for name in ("indptr", "indices", "data", "shape"):
                arrays[f"{key}_{name}"] = getattr(policy, name)
            rows.append(dict(task_index=ev["task_index"], method_id=ev["method_id"],
                start_landmark=ev["start_landmark"], goal_landmark_count=ev["goal_landmark_count"],
                goal_sha256=goal, goal_center=center, fallback_used=ev["fallback_used"],
                fallback_method=ev["fallback_method"], policy_present=ev["policy_present"],
                solver_status=ev["solver_status"], finite_certificate=ev["finite_certificate"]))
        arrays["event_json"] = np.array(json.dumps(rows))
        np.savez(directory/f"seed_{seed}.npz", **arrays)


def _worker(repo, out, seeds):
    env = os.environ.copy()
    env.update({k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")})
    subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), str(repo), str(out),
                    *map(str, seeds)], cwd=repo, env=env, check=True)


@contextmanager
def prior_dumps(seeds):
    """Yield verified old-source policy snapshots while the caller compares them."""
    scratch = ROOT / ".tmp"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="e3_replay_", dir=scratch) as tmp:
        directory = Path(tmp)
        old = directory/"old"
        old.mkdir()
        # Restrict the read to the three participating packages.
        proc = subprocess.run(["git", "archive", OLD_V3_COMMIT, *PACKAGES], cwd=ROOT,
                              capture_output=True)
        if proc.returncode:
            raise RuntimeError(f"comparison_unavailable_without_prior_csr: need Git object {OLD_V3_COMMIT}")
        subprocess.run(["tar", "-x", "-C", str(old)], input=proc.stdout, check=True)
        frozen = json.loads((old/"learned_portal_phase3"/FROZEN_V3).read_text())
        old_out = directory/"prior"
        old_out.mkdir()
        _worker(old, old_out, seeds)
        yield old_out, frozen["block_e3_continuous_surrogate_7controls"]["task_events"]


def index_events(rows, seed):
    expected = {(task, method) for task in range(12) for method in METHODS}
    indexed = {(r["task_index"], r["method_id"]): r for r in rows}
    if len(rows) != len(indexed) or indexed.keys() != expected:
        raise ValueError(f"Incomplete or duplicate E3 task/method roster for seed {seed}")
    return indexed


def load_dump(directory, seed):
    with np.load(directory/f"seed_{seed}.npz", allow_pickle=False) as z:
        arrays = {key: z[key] for key in z.files}
    return arrays, index_events(json.loads(str(arrays.pop("event_json"))), seed)


def read_csr(arrays, task, method):
    key = f"t{task}_{method}"
    return sp.csr_matrix(tuple(arrays[f"{key}_{n}"] for n in ("data", "indices", "indptr")),
                         shape=tuple(arrays[f"{key}_shape"]))


def require_inputs(arrays, actual, seed):
    for key in INPUTS:
        old, new = arrays[key], actual[key]
        if old.shape != new.shape or old.dtype != new.dtype or old.tobytes() != new.tobytes():
            raise ValueError(f"E3 replay {seed}: unequal {key}")


def require_old_event(old, archived):
    # The v3 ledger retained these identities, but did not save the CSR bytes.
    for field in ("start_landmark", "goal_landmark_count", "fallback_used", "fallback_method",
                  "policy_present", "solver_status", "finite_certificate"):
        if old[field] != archived[field]:
            raise ValueError(f"E3 frozen v3 ledger differs on {field}")


def compare_event(old, new, previous, current):
    """Separately bind the task, fallback and both numerical CSR tolerances."""
    if previous is None or old is None:
        return dict(comparison_status="comparison_unavailable_without_prior_csr", equivalent=False,
                    max_abs_entry_diff=None, matrix_infinity_norm_diff=None)
    if current is None or previous.shape != current.shape:
        return dict(comparison_status="policy_missing_or_shape_changed", equivalent=False,
                    max_abs_entry_diff=None, matrix_infinity_norm_diff=None)
    if not all(np.isfinite(p.data).all() for p in (previous, current)):
        raise ValueError("Cannot compare a non-finite E3 policy")
    delta = previous-current
    entry = float(np.max(np.abs(delta.data), initial=0.))
    row_l1 = float(np.max(np.asarray(abs(delta).sum(axis=1)), initial=0.))
    same_task = all(old[k] == new[k] for k in ("start_landmark", "goal_landmark_count",
                                               "goal_sha256", "goal_center"))
    same_fallback = all(old[k] == new[k] for k in ("fallback_used", "fallback_method"))
    equivalent = (same_task and same_fallback and old["policy_present"] and new["policy_present"]
                  and entry <= TOL and row_l1 <= TOL)
    return dict(comparison_status="verified_actual_cross_commit_csr" if equivalent else "changed_policy_or_task",
        equivalent=bool(equivalent), same_start=old["start_landmark"] == new["start_landmark"],
        same_goal=old["goal_sha256"] == new["goal_sha256"] and old["goal_center"] == new["goal_center"],
        same_fallback=same_fallback, max_abs_entry_diff=entry, matrix_infinity_norm_diff=row_l1)


def run_actual_cross_commit_e3_policy_comparison():
    seeds = range(6000,6008)
    with prior_dumps(seeds) as (old_out, archived):
        current_dir = old_out.parent/"new"
        current_dir.mkdir()
        # A single immutable source snapshot per worker even on a dirty checkout.
        for package in PACKAGES:
            shutil.copytree(ROOT/package, current_dir/package,
                            ignore=lambda path, files: [f for f in files if not f.endswith(".py")])
        source = current_dir/"learned_portal_phase3"
        original_dynamics = old_out.parent/"old/learned_portal_phase3/continuous_manifold_spql.py"
        same_controller_and_simulator = (original_dynamics.read_bytes() ==
                                        (source/"continuous_manifold_spql.py").read_bytes())
        sources = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source.glob("*.py")}
        revision = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        new_out = old_out.parent/"candidate"
        new_out.mkdir()
        _worker(current_dir, new_out, seeds)
        rows = []
        for seed in seeds:
            arr_a, old = load_dump(old_out, seed)
            arr_b, new = load_dump(new_out, seed)
            require_inputs(arr_a, arr_b, seed)
            archive = index_events([row for row in archived if row["seed"] == seed], seed)
            for (task,method), oa in sorted(old.items()):
                nb = new[task,method]
                require_old_event(oa, archive[task,method])
                pa, pb = read_csr(arr_a, task, method), read_csr(arr_b, task, method)
                result = compare_event(oa, nb, pa, pb)
                if not result["equivalent"]:
                    raise ValueError(f"E3 {seed}/{task}/{method}: {result}")
                old_hash, new_hash = csr_id(pa), csr_id(pb)
                rows.append(dict(seed=seed, task_index=task, method_id=method,
                    old_solver_status=oa["solver_status"], new_solver_status=nb["solver_status"],
                    old_finite_certificate=oa["finite_certificate"], new_finite_certificate=nb["finite_certificate"],
                    start_landmark=oa["start_landmark"], goal_sha256=oa["goal_sha256"],
                    old_raw_csr_sha256=old_hash, new_raw_csr_sha256=new_hash,
                    same_raw_csr_hash=old_hash == new_hash, **result))
    return dict(old_commit=OLD_V3_COMMIT, new_checkout_head=revision, new_snapshot_phase3_py_sha256=sources,
        comparison_scope="actual_cross_commit_csr_reconstruction_all_672_queries_zero_policy_rollout_reruns",
        controller_and_simulator_source_unchanged=same_controller_and_simulator,
        rollout_reuse_supported=same_controller_and_simulator,
        policy_evaluation_rollouts=0,
        passive_exploration_steps_replayed_per_version=8*30600,
        comparison_count=len(rows), input_data_bitwise_equal_all_8_seeds=True,
        same_fallback_count=sum(r["same_fallback"] for r in rows),
        bitwise_hash_equal_count=sum(r["same_raw_csr_hash"] for r in rows),
        exceeds_entrywise_1e12_count=sum(r["max_abs_entry_diff"] > TOL for r in rows),
        exceeds_rowwise_1e12_count=sum(r["matrix_infinity_norm_diff"] > TOL for r in rows),
        max_abs_entry_diff=max(r["max_abs_entry_diff"] for r in rows),
        max_matrix_infinity_norm_diff=max(r["matrix_infinity_norm_diff"] for r in rows), events=rows)


if __name__ == "__main__":
    _dump(Path(sys.argv[1]), Path(sys.argv[2]), list(map(int, sys.argv[3:])))
