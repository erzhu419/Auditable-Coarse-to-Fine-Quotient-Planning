"""Query-specific scalar afterstate TD with four spatial six-cell n-tuples.

Each table is shared across the eight board symmetries. Repeated addresses
remain repeated features: one update uses their multiplicity and the same
pre-update TD error. Dynamics are the supplied identified line program only.
The caller owns the query, sampled experience, and terminal TD targets.
"""
from collections import Counter
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_relational_dynamics_v69 import ACTION_ORDER, _cells
from .controlled_predictive_rollout_consequences_v119 import _tables

PATTERNS = ((0, 1, 2, 4, 5, 6), (4, 5, 6, 8, 9, 10),
            (0, 1, 2, 3, 4, 5), (4, 5, 6, 7, 8, 9))
ALPHA = 0.0025
ACTIONS = tuple(sorted(ACTION_ORDER))
SCHEMA = 'controlled_predictive_ntuple_td_v120'
_LIBRARIES = {}
_COUNT_NAMES = ('learned_swipe_calls', 'line_table_lookups', 'legal_swipes',
                'learned_terminal_checks', 'value_predictions', 'table_lookups',
                'terminal_goal_bypasses')


def symmetry_patterns():
    result = []
    for pattern in PATTERNS:
        variants = []
        for reflected in (False, True):
            for rotations in range(4):
                cells = []
                for cell in pattern:
                    row, col = divmod(cell, 4)
                    if reflected:
                        col = 3 - col
                    for _ in range(rotations):
                        row, col = col, 3 - row
                    cells.append(4 * row + col)
                variants.append(cells)
        result.append(variants)
    return np.asarray(result, dtype=np.int32)


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    project = Path(__file__).resolve().parents[3]
    if not build_dir.is_relative_to(project):
        raise ValueError('V120 build_dir must be inside the research worktree')
    key = (str(build_dir), os.getpid())
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_name('controlled_predictive_ntuple_kernel_v120.cpp')
        path = build_dir / f'ntuple_kernel_v120_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC',
            '-ffp-contract=off', str(source), '-o', str(path)], check=True,
            capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(build_dir)))
        counts['cpp_compilations'] += 1
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.ntuple_value_v120.argtypes = [ip, ip, ci, dp]
        library.ntuple_value_v120.restype = cd
        library.ntuple_update_v120.argtypes = [ip, ip, ci, dp, cd, cd, ip]
        library.ntuple_update_v120.restype = cd
        library.ntuple_choose_v120.argtypes = [ip, ip, ci, dp, ip, lp, ip,
            cd, cd, ip, lp, dp, dp, ip, up]
        library.ntuple_choose_v120.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class NtupleValue:
    """Dense float64 trainable afterstate value for exactly one caller's query."""

    def __init__(self, rule, build_dir):
        started = perf_counter()
        self.rule, self.radix = rule, int(rule.goal_rank)
        self.counts, self.setup_counts = Counter(), Counter()
        self.updates = 0
        self.library = _backend(build_dir, self.setup_counts)
        self.table, self.scores = _tables(rule, self.setup_counts)
        self.patterns = symmetry_patterns()
        self.weights = np.zeros((len(PATTERNS), self.radix**6), dtype=np.float64)
        self.cells = np.asarray([[_cells(action, line) for line in range(4)]
                                 for action in ACTIONS], dtype=np.int32)
        self.setup_counts['allocated_weight_parameters'] += self.weights.size
        self.setup_counts['allocated_weight_bytes'] += self.weights.nbytes
        self.setup_seconds = perf_counter() - started

    def _board(self, board, terminal_allowed=False):
        result = np.ascontiguousarray(board, dtype=np.int32)
        if result.shape != (16,) or np.any(result < 0):
            raise ValueError('board must have 16 nonnegative ranks')
        if not terminal_allowed and np.any(result >= self.radix):
            raise ValueError('terminal goals are analytic, outside the n-tuple tables')
        return result

    def feature_indices(self, board):
        """Flattened addresses, including all 32 feature occurrences."""
        board = self._board(board)
        indices = np.zeros((len(PATTERNS), 8), dtype=np.int64)
        for position in range(6):
            indices = indices * self.radix + board[self.patterns[:, :, position]]
        indices += np.arange(len(PATTERNS), dtype=np.int64)[:, None] * self.radix**6
        return indices.reshape(-1)

    def value(self, board):
        board = self._board(board)
        self.counts['value_predictions'] += 1
        self.counts['table_lookups'] += 32
        return float(self.library.ntuple_value_v120(board, self.patterns,
                                                    self.radix, self.weights))

    def update(self, afterstate, target, alpha=ALPHA):
        board = self._board(afterstate)
        unique = np.zeros(1, dtype=np.int32)
        error = self.library.ntuple_update_v120(board, self.patterns,
            self.radix, self.weights, float(target), float(alpha), unique)
        self.updates += 1
        self.counts['td_updates'] += 1
        self.counts['value_predictions'] += 1
        self.counts['table_lookups'] += 32
        self.counts['table_updates'] += int(unique[0])
        self.counts['table_update_occurrences'] += 32
        return float(error)

    def choose(self, board, query):
        board = self._board(board, terminal_allowed=True)
        before = self.counts.copy()
        self.counts['choose_calls'] += 1
        self.counts['learned_terminal_checks'] += 1
        goal = float(query.get('goal_bonus', 0.0))
        failure = float(query.get('failure_penalty', 0.0))
        if int(board.max()) >= self.radix:
            self.counts['terminal_goal_bypasses'] += 1
            return dict(action=None, afterstate=board.tolist(), score=0,
                value=goal, tail_value=goal, action_values={}, status='WON',
                counts=dict(self.counts-before))
        moved = np.empty((4, 16), dtype=np.int32)
        scores = np.zeros(4, dtype=np.int64)
        tails, values = np.zeros(4), np.zeros(4)
        legal = np.zeros(4, dtype=np.int32)
        counts = np.zeros(len(_COUNT_NAMES), dtype=np.uint64)
        best = self.library.ntuple_choose_v120(board, self.patterns, self.radix,
            self.weights, self.table, self.scores, self.cells,
            float(query.get('reward_weight', 1.0)), goal,
            moved, scores, tails, values, legal, counts)
        self.counts.update({name: int(value) for name, value in zip(_COUNT_NAMES, counts)})
        if best < 0:
            return dict(action=None, afterstate=board.tolist(), score=0,
                value=-failure, tail_value=-failure, action_values={}, status='LOST',
                counts=dict(self.counts-before))
        action_values = {action: dict(afterstate=moved[index].tolist(),
            score=int(scores[index]), tail_value=float(tails[index]),
            value=float(values[index])) for index, action in enumerate(ACTIONS) if legal[index]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]],
            action_values=action_values, status='ACTIVE', counts=dict(self.counts-before))

    def save(self, path):
        """Store only nonzero parameters; all dense scans and writes are charged."""
        started = perf_counter()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.weights.reshape(-1)
        indices = np.flatnonzero(flat)
        self.counts['checkpoint_saves'] += 1
        self.counts['checkpoint_scanned_parameters'] += flat.size
        self.counts['checkpoint_saved_parameters'] += len(indices)
        metadata = dict(schema=SCHEMA, patterns=PATTERNS, radix=self.radix,
                        counts=dict(self.counts), updates=self.updates,
                        setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds)
        with path.open('wb') as stream:
            np.savez_compressed(stream, indices=indices, values=flat[indices],
                                metadata=json.dumps(metadata, sort_keys=True))
        self.last_save_seconds = perf_counter()-started
        return dict(path=str(path), parameter_count=int(flat.size),
                    nonzero_weights=len(indices), updates=self.updates,
                    bytes=path.stat().st_size, seconds=self.last_save_seconds)

    @classmethod
    def load(cls, path, rule, build_dir):
        started = perf_counter()
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data['metadata']))
            if (metadata['schema'] != SCHEMA or metadata['radix'] != rule.goal_rank
                    or metadata['patterns'] != [list(pattern) for pattern in PATTERNS]):
                raise ValueError('checkpoint does not match V120 model shape')
            model = cls(rule, build_dir)
            model.weights.reshape(-1)[data['indices']] = data['values']
            model.counts = Counter(metadata['counts'])
            model.updates = int(metadata['updates'])
            model.counts['checkpoint_loads'] += 1
            model.counts['checkpoint_loaded_parameters'] += len(data['indices'])
            model.loaded_setup_counts = metadata['setup_counts']
            model.loaded_setup_seconds = metadata['setup_seconds']
        model.last_load_seconds = perf_counter()-started
        return model
