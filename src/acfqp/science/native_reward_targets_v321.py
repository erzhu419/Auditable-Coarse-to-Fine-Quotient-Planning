"""Bounded FIRST-policy reward labels; WIN targets remain the old V319 labels."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .native_retained_critic_v287 import _work
from .native_split_risk_v301 import PLANNING_COUNTS, REPRESENTATION_COUNTS
from .native_value_stream_v286 import ENVIRONMENT_COUNTS

REWARD_COUNTS = ('rollouts_started', 'reused_start_spawns', 'rollout_rng_starts',
    'prescribed_direct_actions', 'h2_choose_calls', 'terminal_wins', 'terminal_losses',
    'reward_bootstrap_predictions', 'reward_bootstrap_table_lookups',
    'trace_rows_written', 'trace_uncompressed_bytes_written',
    'boundary_probe_snapshots', 'boundary_probe_bytes_copied')
TRACE_COLUMNS = ('root_local_index', 'member', 'action_number_1based', 'action',
    'gained_score', 'new_spawn_cell', 'new_spawn_rank',
    'ground_status_after_optional_spawn', 'endpoint_kind')
_LIBRARIES = {}


def _backend(runtime, counts):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V321 native builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = runtime / f'native_reward_targets_v321_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(output)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(runtime)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=4)
        library = ctypes.CDLL(str(output))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.acquire_rewards_v321.argtypes = [ip, ci, ci, ip, ip, ip, ip, up,
            ip, ci, dp, dp, ip, lp, ip, cd, cd, ci, ctypes.c_char_p,
            ip, lp, ip, ip, ip, ip, dp, dp, ip, ip, lp, dp, dp, ip, ip, up, up, up, up]
        library.acquire_rewards_v321.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def acquire_rewards(first, roots, spawn_cells, spawn_ranks, selected_action, targetkind,
                    rollout_seeds, runtime, trace_path, *, p_model, p_true, horizon=4):
    """Reuse saved spawn/DIRECT, acquire <= H−1 spawns, bootstrap before the last spawn.

    Only ``target_reward`` changes: this routine neither returns nor substitutes WIN
    labels. ``status=0`` denotes a planned bootstrap, never a terminal reward return.
    """
    if first.kind != 'LOCAL_RISK' or first.reward_weights.flags.writeable or first.risk_weights.flags.writeable:
        raise ValueError('V321 acquisition uses the actual frozen FIRST LOCAL teacher')
    started, cpu = perf_counter(), process_time()
    roots = np.ascontiguousarray(roots, dtype=np.int32)
    arrays = [np.ascontiguousarray(value, dtype=np.int32)
        for value in (spawn_cells, spawn_ranks, selected_action, targetkind)]
    seeds = np.ascontiguousarray(rollout_seeds, dtype=np.uint64)
    if roots.ndim != 2 or roots.shape[1] != 16 or np.any(roots < 0) or np.any(np.max(roots, axis=1) >= first.radix):
        raise ValueError('V321 roots are retained nonwinning 16-cell afterstates')
    if seeds.ndim != 2 or seeds.shape[0] != len(roots) or any(value.shape != seeds.shape for value in arrays):
        raise ValueError('V321 retained spawn/action replicas and continuation seeds must match the roots')
    if int(horizon) < 1:
        raise ValueError('V321 action horizon includes the prescribed DIRECT action')
    trace_path = Path(trace_path).resolve()
    if not trace_path.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V321 retained traces belong inside the research worktree')
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = trace_path.with_suffix('.moves.i32')
    n, repeats = seeds.shape; rollouts = n * repeats
    probe_indices = sorted(set(range(min(8, rollouts))) | set(range(max(0, rollouts-8), rollouts)))
    slots = np.full(rollouts, -1, dtype=np.int32)
    slots[probe_indices] = np.arange(len(probe_indices), dtype=np.int32)
    shape = (len(probe_indices), 2)
    preboards = np.zeros(shape+(16,), dtype=np.int32)
    moved = np.zeros(shape+(4, 16), dtype=np.int32)
    scores = np.zeros(shape+(4,), dtype=np.int64)
    tails, values = np.zeros(shape+(4,)), np.zeros(shape+(4,))
    legal = np.zeros(shape+(4,), dtype=np.int32)
    info = np.full(shape+(2,), -1, dtype=np.int32)
    metrics = np.empty((n, repeats, 4), dtype=np.int64)
    final, last_pre, last_after, bootstrap = (np.empty((n, repeats, 16), dtype=np.int32) for _ in range(4))
    target_reward, tail_reward = np.empty((n, repeats)), np.empty((n, repeats))
    environment, planning, representation, work = (np.zeros(len(names), dtype=np.uint64)
        for names in (ENVIRONMENT_COUNTS, PLANNING_COUNTS, REPRESENTATION_COUNTS, REWARD_COUNTS))
    setup = Counter(); library = _backend(runtime, setup)
    code = library.acquire_rewards_v321(roots, n, repeats, *arrays, seeds,
        first.model.patterns, first.radix, first.reward_weights, first.risk_weights,
        first.model.table, first.model.scores, first.model.cells, float(p_model), float(p_true),
        int(horizon), os.fsencode(temporary), slots, metrics, final, last_pre, last_after,
        bootstrap, target_reward, tail_reward, preboards, moved, scores, tails, values,
        legal, info, environment, planning, representation, work)
    if code:
        raise ValueError(f'V321 retained branch or bounded continuation failed (native code {code}); partial trace: {temporary}')
    trace = np.fromfile(temporary, dtype=np.int32).reshape(-1, len(TRACE_COLUMNS))
    np.savez_compressed(trace_path, moves=trace)
    compressed_bytes, raw_bytes = trace_path.stat().st_size, temporary.stat().st_size
    temporary.unlink()

    def decision(slot, boundary):
        step, action = map(int, info[slot, boundary])
        if step < 0:
            return None
        action_values = {name: dict(afterstate=moved[slot, boundary, j].tolist(),
            score=int(scores[slot, boundary, j]), tail_value=float(tails[slot, boundary, j]),
            value=float(values[slot, boundary, j])) for j, name in enumerate(ACTIONS) if legal[slot, boundary, j]}
        return dict(step=step, preboard=preboards[slot, boundary].tolist(),
            chosen_action=ACTIONS[action], chosen_afterstate=moved[slot, boundary, action].tolist(),
            chosen_h2_value=float(values[slot, boundary, action]), action_values=action_values, p_model=float(p_model))

    probes = [dict(root_local_index=index//repeats, member=index%repeats,
        first_h2_decision=decision(slot, 0), last_h2_decision=decision(slot, 1))
        for slot, index in enumerate(probe_indices)]
    count_receipt = _work(REWARD_COUNTS, work)
    planning_receipt = _work(PLANNING_COUNTS, planning)
    planning_receipt['choose_calls'] = count_receipt.get('h2_choose_calls', 0)
    return dict(target_reward=target_reward, scores=metrics[:, :, 0].copy(),
        actions=metrics[:, :, 1].copy(), status=metrics[:, :, 2].astype(np.int32),
        new_raw_tiles=metrics[:, :, 3].copy(), tail_reward=tail_reward,
        bootstrap_afterstates=bootstrap, last_preboards=last_pre, last_afterstates=last_after,
        final_boards=final, rollout_seeds=seeds,
        status_codes={'WON': 1, 'LOST': -1, 'BOOTSTRAPPED': 0}, horizon=int(horizon),
        p_model=float(p_model), p_true=float(p_true), teacher_updates=first.updates,
        continuation_rule='SAVED_DIRECT_THEN_FROZEN_FIRST_H2_LAST_AFTERSTATE_REWARD_BOOTSTRAP',
        counts=count_receipt, environment_counts=_work(ENVIRONMENT_COUNTS, environment),
        planning_counts=planning_receipt, representation_counts=_work(REPRESENTATION_COUNTS, representation),
        boundary_probes=probes, trace_artifact=dict(file=str(trace_path), rows=len(trace),
            columns=list(TRACE_COLUMNS), dtype='int32', compressed_bytes=compressed_bytes,
            uncompressed_bytes=raw_bytes, packing_rule='GROUP_MEMBER_CHRONOLOGICAL_EXECUTED_ACTIONS',
            endpoint_codes={'CONTINUE': 0, 'WON': 1, 'LOST': -1, 'BOOTSTRAPPED': 2},
            reused_start_spawn_included=False, all_new_spawns_included=True), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
