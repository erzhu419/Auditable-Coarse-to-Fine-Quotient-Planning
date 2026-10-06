"""Real terminal continuation of retained V319 FIRST-teacher target branches."""
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

CALIBRATION_COUNTS = ('rollouts_started', 'reused_start_spawns', 'rollout_rng_starts',
    'prescribed_direct_actions', 'h2_choose_calls', 'terminal_wins', 'terminal_losses',
    'action_cutoffs', 'trace_rows_written', 'trace_uncompressed_bytes_written',
    'boundary_probe_snapshots', 'boundary_probe_bytes_copied')
TRACE_COLUMNS = ('root_local_index', 'member', 'action_number_1based', 'action', 'gained_score',
    'new_spawn_cell', 'new_spawn_rank', 'ground_status_after_spawn')
_LIBRARIES = {}


def _backend(runtime, counts):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V320 native builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = runtime / f'native_teacher_calibration_v320_{os.getpid()}.so'
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
        library.continue_targets_v320.argtypes = [ip, ci, ci, ip, ip, ip, ip, up,
            ip, ci, dp, dp, ip, lp, ip, cd, cd, ci, ctypes.c_char_p,
            ip, lp, ip, ip, ip, lp, dp, dp, ip, ip, up, up, up, up]
        library.continue_targets_v320.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def continue_targets(first, roots, spawn_cells, spawn_ranks, selected_action, targetkind,
                     rollout_seeds, runtime, trace_path, *, p_model, p_true, max_steps=8192):
    """Replay the paid first spawn/action; acquire only subsequent real-world spawns."""
    if first.kind != 'LOCAL_RISK' or first.reward_weights.flags.writeable or first.risk_weights.flags.writeable:
        raise ValueError('V320 continuation uses the actual frozen FIRST LOCAL teacher')
    started, cpu = perf_counter(), process_time()
    roots = np.ascontiguousarray(roots, dtype=np.int32)
    arrays = [np.ascontiguousarray(value, dtype=np.int32)
        for value in (spawn_cells, spawn_ranks, selected_action, targetkind)]
    seeds = np.ascontiguousarray(rollout_seeds, dtype=np.uint64)
    if roots.ndim != 2 or roots.shape[1] != 16 or np.any(np.max(roots, axis=1) >= first.radix):
        raise ValueError('V320 calibration roots are retained nonwinning 16-cell afterstates')
    if seeds.ndim != 2 or seeds.shape[0] != len(roots) or any(value.shape != seeds.shape for value in arrays):
        raise ValueError('V320 retained spawn/action replicas and continuation seeds must match the roots')
    if int(max_steps) < 1:
        raise ValueError('V320 total-action limit includes the prescribed DIRECT action')
    trace_path = Path(trace_path).resolve()
    if not trace_path.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V320 retained traces belong inside the research worktree')
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
    final = np.empty((n, repeats, 16), dtype=np.int32)
    environment, planning, representation, work = (np.zeros(len(names), dtype=np.uint64)
        for names in (ENVIRONMENT_COUNTS, PLANNING_COUNTS, REPRESENTATION_COUNTS, CALIBRATION_COUNTS))
    setup = Counter(); library = _backend(runtime, setup)
    code = library.continue_targets_v320(roots, n, repeats, *arrays, seeds,
        first.model.patterns, first.radix, first.reward_weights, first.risk_weights,
        first.model.table, first.model.scores, first.model.cells, float(p_model), float(p_true),
        int(max_steps), os.fsencode(temporary), slots, metrics, final, preboards, moved,
        scores, tails, values, legal, info, environment, planning, representation, work)
    if code:
        raise ValueError(f'V320 retained branch or continuation failed (native code {code}); partial trace: {temporary}')
    trace = np.fromfile(temporary, dtype=np.int32).reshape(-1, 8)
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
    count_receipt = _work(CALIBRATION_COUNTS, work)
    planning_receipt = _work(PLANNING_COUNTS, planning)
    planning_receipt['choose_calls'] = count_receipt.get('h2_choose_calls', 0)
    result_scores = metrics[:, :, 0].copy(); actions = metrics[:, :, 1].copy()
    status = metrics[:, :, 2].astype(np.int32); new_raw = metrics[:, :, 3].copy()
    reward_return = np.where(status == 0, np.nan, result_scores / 2048.)
    win = np.where(status == 0, np.nan, (status == 1).astype(np.float64))
    utility = reward_return + 8.*(win-.5)
    return dict(scores=result_scores, actions=actions, status=status, new_raw_tiles=new_raw,
        final_boards=final, reward_return=reward_return, win=win, utility=utility,
        status_codes={'WON': 1, 'LOST': -1, 'CUTOFF': 0}, max_steps=int(max_steps),
        p_model=float(p_model), p_true=float(p_true), teacher_updates=first.updates,
        continuation_rule='SAVED_DIRECT_THEN_FROZEN_FIRST_H2_TRUE_WORLD',
        counts=count_receipt, environment_counts=_work(ENVIRONMENT_COUNTS, environment),
        planning_counts=planning_receipt, representation_counts=_work(REPRESENTATION_COUNTS, representation),
        boundary_probes=probes, trace_artifact=dict(file=str(trace_path), rows=len(trace),
            columns=list(TRACE_COLUMNS), dtype='int32', compressed_bytes=compressed_bytes,
            uncompressed_bytes=raw_bytes, packing_rule='GROUP_MEMBER_CHRONOLOGICAL_EXECUTED_ACTIONS',
            reused_start_spawn_included=False, all_new_spawns_included=True), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
