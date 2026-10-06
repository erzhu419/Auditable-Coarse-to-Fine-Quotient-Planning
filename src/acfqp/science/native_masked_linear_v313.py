"""Selected LINEAR_WIN2 samples with complete factual natural-game targets."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .native_linear_win_v311 import (LEARNING_COUNTS, METHOD, NORMALIZATION_COUNTS,
    REPRESENTATION_COUNTS, TARGET_COUNTS, _parameters)
from .native_replay_fit_v307 import SELECTION_COUNTS
from .native_retained_critic_v287 import _arrays, _work

_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V313 native builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = build_dir/f'native_masked_linear_v313_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(output)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=4)
        library = ctypes.CDLL(str(output))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        library.fit_masked_linear_v313.argtypes = [ip, dp, lp, ip, ip, ctypes.c_int,
            ip, ctypes.c_int, dp, dp, ctypes.c_double, up, up, up, up, up, lp, dp]
        library.fit_masked_linear_v313.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def fit_masked_linear(leaf, dataset, selection_mask, build_dir, alpha=.0025):
    if leaf.kind!=METHOD:
        raise ValueError('V313 masked linear fits use the active LINEAR_WIN2 representation')
    if not leaf.reward_weights.flags.writeable or not leaf.win_weights.flags.writeable:
        raise ValueError('Both reward/WIN heads must be writable while fitting')
    started, cpu_started = perf_counter(), process_time()
    arrays = _arrays(dataset)
    n_games, fit_end = int(dataset['fit_game_count']), int(dataset['fit_step_end'])
    if (int(arrays[2][n_games-1]) if n_games else 0)!=fit_end:
        raise ValueError('V313 selects within the complete-game FIT prefix')
    if np.any((arrays[3][:n_games]!=1) & (arrays[3][:n_games]!=-1)):
        raise ValueError('Masked LINEAR supervision requires completed WON/LOST natural games')
    mask = np.ascontiguousarray(selection_mask, dtype=np.int32)
    if mask.shape!=(fit_end,) or np.any((mask!=0) & (mask!=1)):
        raise ValueError('The selection mask has one binary entry per complete FIT step')
    if np.any((mask!=0) & (np.max(arrays[0][:fit_end], axis=1)>=leaf.radix)):
        raise ValueError('Winning afterstates are excluded from supervised updates')
    setup = Counter(); library = _backend(build_dir, setup)
    learning, targets = np.zeros(len(LEARNING_COUNTS), dtype=np.uint64), np.zeros(len(TARGET_COUNTS), dtype=np.uint64)
    normalization = np.zeros(len(NORMALIZATION_COUNTS), dtype=np.uint64)
    representation = np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64)
    selection = np.zeros(len(SELECTION_COUNTS), dtype=np.uint64)
    indices, values = np.empty((2, 2), dtype=np.int64), np.empty((2, 7))
    library.fit_masked_linear_v313(*arrays, mask, n_games, *_parameters(leaf), float(alpha),
        learning, targets, normalization, representation, selection, indices, values)
    work = _work(LEARNING_COUNTS, learning)
    leaf.updates += work.get('td_updates', 0); leaf.counts.update(work)
    def example(index):
        if not work.get('td_updates', 0):
            return None
        game, step = map(int, indices[index])
        reward_target, win_target, reward, win, utility, reward_error, win_error = map(float, values[index])
        return dict(episode=game, step=step, reward_target=reward_target, win_target=win_target,
            reward_prediction=reward, win_prediction=win, combined_prediction=utility,
            reward_error=reward_error, win_error=win_error)
    selection_work = _work(SELECTION_COUNTS, selection)
    return dict(method=METHOD, alpha=float(alpha), fitted_games=n_games, fitted_steps=fit_end,
        trained_afterstates=work.get('td_updates', 0), learning_counts=work,
        reward_trained_afterstates=work.get('td_updates', 0), win_trained_afterstates=work.get('td_updates', 0),
        frozen_game_start_targets=True, target_counts=_work(TARGET_COUNTS, targets),
        normalization_counts=_work(NORMALIZATION_COUNTS, normalization),
        representation_counts=_work(REPRESENTATION_COUNTS, representation),
        first_sample=example(0), last_sample=example(1), setup_counts=dict(setup),
        candidate_fitted_games=n_games, selected_games=selection_work.get('games_with_selected_samples', 0),
        selection_counts=selection_work, seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)
