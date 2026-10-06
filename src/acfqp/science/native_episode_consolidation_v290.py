"""Whole-game address normalization with sequential or frozen-start residuals."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .native_retained_critic_v287 import LEARNING_COUNTS, TARGET_COUNTS, _arrays, _parameters, _work, _charge

METHODS = ('NORMALIZED_SEQUENTIAL_MC', 'EPISODE_MEAN_MC')
CONSOLIDATION_COUNTS = (
    'games_processed', 'feature_extractions', 'feature_occurrences', 'feature_digit_reads',
    'feature_address_multiply_adds', 'game_sort_calls', 'game_sort_items', 'game_sort_comparisons',
    'address_occurrence_count_visits', 'address_occurrence_count_comparisons',
    'sample_sort_calls', 'sample_sort_items', 'sample_sort_comparisons',
    'address_denominator_searches', 'address_denominator_search_comparisons',
    'sample_unique_addresses', 'game_unique_addresses', 'weighted_residual_multiplications',
    'weighted_residual_accumulations', 'parameter_update_multiplications', 'normalization_divisions',
    'game_parameter_commits', 'sample_parameter_commits', 'parameter_write_events',
    'feature_index_buffer_int64_peak', 'sorted_feature_buffer_int64_peak', 'sample_step_buffer_int64_peak',
    'game_address_buffer_int64_peak', 'game_denominator_buffer_int64_peak',
    'sample_address_buffer_int64_peak', 'sample_multiplicity_buffer_int64_peak',
    'sample_end_buffer_int64_peak', 'error_buffer_doubles_peak', 'raw_prediction_buffer_doubles_peak',
    'address_gradient_buffer_doubles_peak', 'native_buffer_bytes_peak')
COUNT_SEMANTICS = dict(
    td_updates='Nonwinning training samples processed; also increments model.updates.',
    table_updates='Actual weight-parameter addition events: per sample/address or per game/address.',
    table_update_occurrences='32 feature occurrences contributing to each processed sample; not parameter writes.',
    game_parameter_commits='EPISODE_MEAN_MC game-end write batches with at least one trainable address.',
    sample_parameter_commits='NORMALIZED_SEQUENTIAL_MC per-sample write batches.',
    native_buffer_bytes_peak='Joint capacity of native vector data buffers, including MC targets; excludes weights.')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V290 builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir / f'native_episode_consolidation_v290_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=1)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.fit_consolidated_v290.argtypes = [ip, dp, lp, ip, ci, ip, ci, dp,
            cd, cd, cd, cd, cd, ci, up, up, up, lp, dp]
        library.fit_consolidated_v290.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def fit_consolidated(leaf, dataset, method, build_dir, alpha=.0025):
    if method not in METHODS:
        raise ValueError('V290 uses one of the two frozen consolidation methods')
    if not leaf.weights.flags.writeable:
        raise ValueError('the fitted shadow critic must be writable')
    started, cpu_started = perf_counter(), process_time()
    setup = Counter(); library = _backend(build_dir, setup)
    arrays = _arrays(dataset)
    n_games, fit_end = int(dataset['fit_game_count']), int(dataset['fit_step_end'])
    if (int(arrays[2][n_games-1]) if n_games else 0) != fit_end:
        raise ValueError('the fit boundary must end the frozen prefix of complete games')
    learning = np.zeros(len(LEARNING_COUNTS), dtype=np.uint64)
    targets = np.zeros(len(TARGET_COUNTS), dtype=np.uint64)
    consolidation = np.zeros(len(CONSOLIDATION_COUNTS), dtype=np.uint64)
    indices, values = np.empty((2,2), dtype=np.int64), np.empty((2,4), dtype=np.float64)
    library.fit_consolidated_v290(*arrays, n_games, *_parameters(leaf), float(alpha),
        int(method == 'EPISODE_MEAN_MC'), learning, targets, consolidation, indices, values)
    work = _work(LEARNING_COUNTS, learning)
    _charge(leaf, work)
    def sample(index):
        if not work.get('td_updates', 0):
            return None
        game, step = map(int, indices[index])
        target, raw_target, error, before = map(float, values[index])
        return dict(episode=game, step=step, target=target, raw_target=raw_target,
                    error=error, raw_prediction_before_update=before)
    return dict(method=method, alpha=float(alpha), fitted_games=n_games, fitted_steps=fit_end,
        trained_afterstates=work.get('td_updates',0), learning_counts=work,
        target_counts=_work(TARGET_COUNTS,targets),
        consolidation_counts=_work(CONSOLIDATION_COUNTS,consolidation),
        count_semantics=COUNT_SEMANTICS, first_sample=sample(0), last_sample=sample(1),
        setup_counts=dict(setup), seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)
