"""Exact FIT-board support gates both frozen LOCAL tables at actual H2 leaves."""
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

SUPPORT_COUNTS = ('membership_queries', 'encoded_board_cells', 'key_comparisons',
                  'base_head_queries', 'updated_head_queries')
_LIBRARIES = {}


def support_from_dataset(dataset):
    """Each key encodes the complete 16-cell board, with cell zero in low bits."""
    started, cpu = perf_counter(), process_time()
    boards = np.asarray(dataset['afterstates'], dtype=np.int32)
    fit_end, n_games = int(dataset['fit_step_end']), int(dataset['fit_game_count'])
    ends = np.asarray(dataset['ends'], dtype=np.int64)
    if (int(ends[n_games-1]) if n_games else 0) != fit_end:
        raise ValueError('V318 support is exactly the complete-game FIT prefix')
    fit = boards[:fit_end]
    eligible = np.flatnonzero(np.max(fit, axis=1) < 11)
    encoded = np.zeros(len(eligible), dtype=np.uint64)
    for cell in range(16):
        encoded |= np.asarray(fit[eligible, cell], dtype=np.uint64) << np.uint64(4 * cell)
    keys = np.unique(encoded)
    keys.flags.writeable = False
    return dict(keys=keys, encoding='CELL_0_LOW_NIBBLE_UINT64', goal_rank=11,
        counts=dict(fit_boards_examined=fit_end, fit_board_cells_examined=16*fit_end,
            winning_fit_boards_excluded=fit_end-len(eligible), encoded_fit_boards=len(eligible),
            encoded_fit_board_cells=16*len(eligible), support_sort_calls=1,
            support_sort_input_keys=len(eligible), unique_support_keys=len(keys)),
        bytes=int(keys.nbytes), cpu_seconds=process_time()-cpu, seconds=perf_counter()-started)


def _backend(runtime, counts):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V318 native builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = runtime / f'native_localized_value_v318_{os.getpid()}.so'
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
        ci, cd, cl = ctypes.c_int, ctypes.c_double, ctypes.c_int64
        library.choose_localized_v318.argtypes = [ip, ip, ci, dp, dp, dp, dp, up, cl,
            ip, lp, ip, cd, ip, lp, dp, dp, ip, up, up, up]
        library.choose_localized_v318.restype = ci
        library.evaluate_localized_v318.argtypes = [up, ci, ip, ci, dp, dp, dp, dp, up, cl,
            ip, lp, ip, cd, cd, ci, lp, ip, up, up, up, up]
        library.evaluate_localized_v318.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _parameters(updated, base, support):
    if updated.kind != 'LOCAL_RISK' or base.kind != 'LOCAL_RISK' or updated.model is not base.model:
        raise ValueError('V318 selects LOCAL components on the same actual SOURCE model')
    if any(weights.flags.writeable for leaf in (updated, base)
           for weights in (leaf.reward_weights, leaf.risk_weights)):
        raise ValueError('Both base and updated component pairs must remain frozen')
    return [updated.model.patterns, updated.radix, updated.reward_weights, updated.risk_weights,
        base.reward_weights, base.risk_weights, support['keys'], len(support['keys']),
        updated.model.table, updated.model.scores, updated.model.cells]


def choose_localized(updated, base, support, board, p, runtime):
    started, cpu = perf_counter(), process_time()
    parameters = _parameters(updated, base, support)
    setup = Counter(); library = _backend(runtime, setup)
    board = updated.model._board(board, terminal_allowed=True)
    moved, scores = np.empty((4, 16), dtype=np.int32), np.zeros(4, dtype=np.int64)
    tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4, dtype=np.int32)
    planning, representation = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64), np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64)
    membership = np.zeros(len(SUPPORT_COUNTS), dtype=np.uint64)
    best = library.choose_localized_v318(board, *parameters, float(p), moved, scores, tails,
        values, legal, planning, representation, membership)
    work = _work(PLANNING_COUNTS, planning); work['choose_calls'] = 1
    result = dict(counts=work, representation_counts=_work(REPRESENTATION_COUNTS, representation),
        support_counts=_work(SUPPORT_COUNTS, membership), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
    if best < 0:
        status, value = ('WON', 4.) if best == -2 else ('LOST', -4.)
        return dict(result, action=None, afterstate=board.tolist(), score=0, value=value,
            tail_value=value, action_values={}, status=status)
    action_values = {action:dict(afterstate=moved[index].tolist(), score=int(scores[index]),
        tail_value=float(tails[index]), value=float(values[index])) for index,action in enumerate(ACTIONS) if legal[index]}
    return dict(result, action=ACTIONS[best], **action_values[ACTIONS[best]],
                action_values=action_values, status='ACTIVE')


def evaluate_localized(updated, base, support, p_model, p_true, seeds, runtime, max_steps=8192):
    started, cpu = perf_counter(), process_time()
    parameters = _parameters(updated, base, support)
    setup = Counter(); library = _backend(runtime, setup)
    seeds = np.ascontiguousarray(seeds, dtype=np.uint64)
    results, final = np.empty((len(seeds), 3), dtype=np.int64), np.empty((len(seeds), 16), dtype=np.int32)
    environment, planning = np.zeros(len(ENVIRONMENT_COUNTS), dtype=np.uint64), np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
    representation, membership = np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64), np.zeros(len(SUPPORT_COUNTS), dtype=np.uint64)
    code = library.evaluate_localized_v318(seeds, len(seeds), *parameters, float(p_model),
        float(p_true), int(max_steps), results, final, environment, planning, representation, membership)
    if code:
        raise ValueError('V318 localized H2 selected an illegal standard-world action')
    rows = []
    for seed, row, board in zip(seeds, results, final):
        score, steps, status = map(int, row)
        rows.append(dict(seed=int(seed), score=score, steps=steps,
            status={1:'WON', -1:'LOST', 2:'CUTOFF'}[status], final_board=board.tolist(),
            utility=score/2048.+(4. if status==1 else -4. if status==-1 else 0.)))
    work = dict(environment=_work(ENVIRONMENT_COUNTS, environment), planning=_work(PLANNING_COUNTS, planning))
    work['planning']['choose_calls'] = sum(row['steps'] for row in rows)
    return dict(game_summaries=rows, counts=work,
        representation_counts=_work(REPRESENTATION_COUNTS, representation),
        support_counts=_work(SUPPORT_COUNTS, membership), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
