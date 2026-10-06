"""V290 whole-game mean updates with the exact V135 H2 afterstate target."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES
from .native_episode_consolidation_v290 import CONSOLIDATION_COUNTS, COUNT_SEMANTICS
from .native_retained_critic_v287 import (
    LEARNING_COUNTS, TARGET_COUNTS, _arrays, _work, _charge)
from .native_value_stream_v286 import _parameters

PLANNING_COUNTS = COUNT_NAMES + (
    'expected_control_target_assignments', 'empty_cell_count_visits',
    'empty_cell_branch_visits', 'spawn_board_cells_copied')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V300 builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir / f'native_b_control_v300_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=3)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.fit_control_v300.argtypes = [ip, dp, lp, ip, ci,
            ip, ip, ci, ci, dp, ip, lp, ip, cd, cd, cd, cd, cd, ci, cd, cd,
            up, up, up, up, lp, dp]
        library.fit_control_v300.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def fit_control(leaf, dataset, model_p_four, build_dir, alpha=.0025):
    """Use only prefix boards and fixed observed spawn belief; no world calls.

    Targets and residuals use each game's start table. Its 32-occurrence
    multiplicities, address denominators and mean write remain V290's kernel.
    """
    if not leaf.weights.flags.writeable:
        raise ValueError('the fitted shadow critic must be writable')
    if not 0. <= model_p_four <= 1.:
        raise ValueError('the observed spawn probability must be in [0, 1]')
    started, cpu_started = perf_counter(), process_time()
    setup = Counter()
    library = _backend(build_dir, setup)
    arrays = _arrays(dataset)
    n_games, fit_end = int(dataset['fit_game_count']), int(dataset['fit_step_end'])
    if (int(arrays[2][n_games-1]) if n_games else 0) != fit_end:
        raise ValueError('the fit boundary must end the prefix of complete games')
    learning = np.zeros(len(LEARNING_COUNTS), dtype=np.uint64)
    targets = np.zeros(len(TARGET_COUNTS), dtype=np.uint64)
    consolidation = np.zeros(len(CONSOLIDATION_COUNTS), dtype=np.uint64)
    planning = np.zeros(len(PLANNING_COUNTS), dtype=np.uint64)
    indices = np.empty((2, 2), dtype=np.int64)
    values = np.empty((2, 4), dtype=np.float64)
    library.fit_control_v300(*arrays, n_games, *_parameters(leaf),
        float(model_p_four), float(alpha), learning, targets, consolidation,
        planning, indices, values)
    work = _work(LEARNING_COUNTS, learning)
    _charge(leaf, work)

    def sample(index):
        if not work.get('td_updates', 0):
            return None
        game, step = map(int, indices[index])
        target, raw_target, error, before = map(float, values[index])
        return dict(episode=game, step=step, target=target, raw_target=raw_target,
                    error=error, raw_prediction_before_update=before)

    semantics = dict(COUNT_SEMANTICS,
        game_parameter_commits='Game-end write batches after all control targets and residuals are read.',
        native_buffer_bytes_peak='Joint native vector capacity including control targets; excludes weights.',
        generated_spawn_outcomes='Enumerated model outcomes; no environment acquisition or random draws.')
    return dict(method='EXPECTED_CONTROL_MEAN', alpha=float(alpha),
        model_p_four=float(model_p_four), game_head_targets_frozen=True,
        fitted_games=n_games, fitted_steps=fit_end,
        trained_afterstates=work.get('td_updates', 0), learning_counts=work,
        target_counts=_work(TARGET_COUNTS, targets),
        consolidation_counts=_work(CONSOLIDATION_COUNTS, consolidation),
        planning_counts=_work(PLANNING_COUNTS, planning), count_semantics=semantics,
        first_sample=sample(0), last_sample=sample(1), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)
