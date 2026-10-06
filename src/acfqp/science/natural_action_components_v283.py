"""Retained-board H2 components and exact reweighting without new feedback."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_frozen_leaf_planning_v135 import COUNT_NAMES as V135_COUNTS
from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .controlled_predictive_paired_ntuple_v130 import _same_query

COUNT_NAMES = V135_COUNTS + ('full_leaf_action_comparisons', 'short_leaf_action_comparisons',
                            'rank_mean_products', 'rank_mean_sums')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V283 builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        library_path = build_dir / f'natural_action_components_v283_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(library_path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=3)
        library = ctypes.CDLL(str(library_path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.natural_action_components_v283.argtypes = [ip, ip, ip, ci, ci, dp, ip, lp, ip,
            cd, cd, cd, cd, cd, ci, ip, lp, ip, dp, dp, dp, dp, up]
        library.natural_action_components_v283.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def compose(payload, p_four, tail='full'):
    """Reproduce V135 cell→rank accumulation, preserving floating-point ties.

    The rank means describe the affine law mathematically. Original cell
    values, rather than regrouped means, reproduce its floating-point scores.
    """
    if tail not in ('full', 'short'):
        raise ValueError('tail must be full or short')
    values, products = {}, 0
    for action, component in payload['action_components'].items():
        spawns = component['spawn_leaf_values']
        if not spawns:
            continuation = payload['goal_bonus']
        else:
            continuation = 0.
            for spawn in spawns:
                for index, probability in enumerate((1. - p_four, p_four)):
                    continuation += (probability / len(spawns)) * spawn[tail][index]
            products += 2 * len(spawns)
        value = component['score'] / 2048. + continuation
        values[action] = dict(afterstate=component['afterstate'], score=component['score'],
                              tail_value=continuation, value=value)
    operations = dict(compose_calls=1)
    if products:
        operations.update(compose_probability_products=products, compose_probability_sums=products)
    if not values:
        terminal = payload['goal_bonus'] if payload['status'] == 'WON' else -payload['failure_penalty']
        return dict(action=None, afterstate=payload['board'], score=0, value=terminal,
            tail_value=terminal, action_values={}, status=payload['status'], counts=operations)
    action = min(values, key=lambda name: (-values[name]['value'], name))
    return dict(action=action, **values[action], action_values=values,
                status='ACTIVE', counts=operations)


class ActionComponents:
    """One native second-ply evaluation supplies both full and short readouts."""
    def __init__(self, leaf, build_dir):
        if leaf.weights.flags.writeable:
            raise ValueError('V283 requires an already frozen value leaf')
        if leaf.rule.spawn_location != 'uniform':
            raise ValueError('V283 decomposes the existing uniform-cell spawn law')
        started = perf_counter()
        self.leaf, self.counts, self.setup_counts = leaf, Counter(), Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.extra_cells = getattr(leaf.model, 'extra_cells', np.zeros((4, 8), dtype=np.int32))
        self.mode = getattr(leaf.model, 'mode', -1)
        self.convert = int(leaf.kind == 'PRIOR' and not _same_query(leaf.source_query, leaf.target_query))
        self.setup_seconds = perf_counter() - started

    def components(self, board):
        started = perf_counter()
        leaf, native = self.leaf, self.leaf.model
        board = native._board(board, terminal_allowed=True)
        moved = np.empty((4, 16), dtype=np.int32)
        scores, legal = np.zeros(4, dtype=np.int64), np.zeros(4, dtype=np.int32)
        full, short = np.zeros((4, 16, 2)), np.zeros((4, 16, 2))
        full_means, short_means = np.zeros((4, 2)), np.zeros((4, 2))
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        raw_query = leaf.source_query if leaf.kind == 'PRIOR' else leaf.target_query
        goal, failure = (float(leaf.target_query.get(key, 0.)) for key in ('goal_bonus', 'failure_penalty'))
        status = self.library.natural_action_components_v283(board, native.patterns, self.extra_cells,
            leaf.radix, self.mode, leaf.weights, native.table, native.scores, native.cells,
            float(raw_query.get('goal_bonus', 0.)), goal, failure, leaf.failure_shift,
            leaf.success_shift, self.convert, moved, scores, legal, full, short, full_means, short_means, counts)
        work = {name: int(value) for name, value in zip(COUNT_NAMES, counts) if value}
        work['component_calls'] = 1
        self.counts.update(work)
        actions = {}
        if status == 0:
            for index, action in enumerate(ACTIONS):
                if not legal[index]:
                    continue
                terminal = int(moved[index].max()) >= leaf.radix
                spawns = [] if terminal else [dict(cell=cell, full=full[index, cell].tolist(),
                    short=short[index, cell].tolist()) for cell in range(16) if moved[index, cell] == 0]
                actions[action] = dict(afterstate=moved[index].tolist(), score=int(scores[index]),
                    rank1_tail=float(full_means[index, 0]), rank2_tail=float(full_means[index, 1]),
                    short_rank1_tail=float(short_means[index, 0]), short_rank2_tail=float(short_means[index, 1]),
                    spawn_leaf_values=spawns)
        return dict(board=board.tolist(), status='ACTIVE' if status == 0 else 'WON' if status == -2 else 'LOST',
            goal_bonus=goal, failure_penalty=failure, action_components=actions,
            counts=work, seconds=perf_counter() - started)

    def compose(self, payload, p_four, tail='full'):
        result = compose(payload, p_four, tail)
        self.counts.update(result['counts'])
        return result
