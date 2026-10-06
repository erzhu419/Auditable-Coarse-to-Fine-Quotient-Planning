"""Two-bank n-tuples with fixed global or outside-tuple occupancy context."""
from collections import Counter
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_ntuple_td_v120 import (
    ACTIONS, ALPHA, PATTERNS, NtupleValue, symmetry_patterns)
from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_paired_ntuple_v130 import _delta
from .controlled_predictive_relational_dynamics_v69 import _cells
from .controlled_predictive_rollout_consequences_v119 import _tables

SCHEMA = 'acfqp.contextual_query_td.v134'
MODEL_SCHEMA = 'acfqp.contextual_ntuple.v134'
GLOBAL_EMPTY_THRESHOLD = 4
CAPACITY_EXTRA_CELLS = (3, 7, 6, 10)
CONTEXT_SPEC = dict(global_empty_threshold=GLOBAL_EMPTY_THRESHOLD,
                    capacity_extra_cells=list(CAPACITY_EXTRA_CELLS))
COUNT_NAMES = ('learned_swipe_calls', 'line_table_lookups', 'legal_swipes',
    'learned_terminal_checks', 'value_predictions', 'table_lookups', 'terminal_goal_bypasses',
    'context_cell_reads', 'context_bank_selections',
    'bank_0_prediction_occurrences', 'bank_1_prediction_occurrences',
    'bank_0_update_occurrences', 'bank_1_update_occurrences',
    'bank_0_unique_updates', 'bank_1_unique_updates', 'context_bank_offset_additions',
    'update_feature_squared_norm')
_LIBRARIES = {}


def symmetry_extra_cells():
    result = []
    for cell in CAPACITY_EXTRA_CELLS:
        variants = []
        for reflected in (False, True):
            for rotations in range(4):
                row, col = divmod(cell, 4)
                if reflected:
                    col = 3-col
                for _ in range(rotations):
                    row, col = col, 3-row
                variants.append(4*row+col)
        result.append(variants)
    return np.asarray(result, dtype=np.int32)


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V134 build_dir must be inside the research worktree')
    key = (str(build_dir), os.getpid())
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'contextual_ntuple_v134_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts['cpp_compilations'] += 1
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        prefix = [ip, ip, ip, ci, ci, dp]
        library.contextual_value_v134.argtypes = prefix+[up]
        library.contextual_value_v134.restype = cd
        library.contextual_update_v134.argtypes = prefix+[cd, cd, ip, up]
        library.contextual_update_v134.restype = cd
        library.contextual_choose_v134.argtypes = prefix+[ip, lp, ip, cd, cd, ip, lp, dp, dp, ip, up]
        library.contextual_choose_v134.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class ContextNtupleValue(NtupleValue):
    def __init__(self, rule, representation, build_dir):
        if representation not in ('GLOBAL', 'CAPACITY'):
            raise ValueError('representation must be GLOBAL or CAPACITY')
        started = perf_counter()
        self.rule, self.radix = rule, int(rule.goal_rank)
        self.representation, self.mode = representation, int(representation == 'CAPACITY')
        self.counts, self.setup_counts, self.updates = Counter(), Counter(), 0
        self.library = _backend(build_dir, self.setup_counts)
        self.table, self.scores = _tables(rule, self.setup_counts)
        self.patterns, self.extra_cells = symmetry_patterns(), symmetry_extra_cells()
        self.weights = np.zeros((2, len(PATTERNS), self.radix**6), dtype=np.float64)
        self.cells = np.asarray([[_cells(action, line) for line in range(4)]
            for action in ACTIONS], dtype=np.int32)
        self.setup_counts.update(allocated_weight_parameters=self.weights.size,
            allocated_weight_bytes=self.weights.nbytes)
        self.setup_seconds = perf_counter()-started

    def _add_counts(self, counts):
        self.counts.update({key: int(value) for key, value in zip(COUNT_NAMES, counts) if value})

    def feature_indices(self, board):
        board = self._board(board)
        indices = np.zeros((len(PATTERNS), 8), dtype=np.int64)
        for position in range(6):
            indices = indices*self.radix+board[self.patterns[:, :, position]]
        indices += np.arange(len(PATTERNS), dtype=np.int64)[:, None]*self.radix**6
        banks = int(np.count_nonzero(board == 0) <= GLOBAL_EMPTY_THRESHOLD) if self.mode == 0 else (
            board[self.extra_cells] > 0)
        indices += banks*(len(PATTERNS)*self.radix**6)
        return indices.reshape(-1)

    def value(self, board):
        board = self._board(board)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        result = self.library.contextual_value_v134(board, self.patterns, self.extra_cells,
            self.radix, self.mode, self.weights, counts)
        self._add_counts(counts)
        self.counts.update(value_predictions=1, table_lookups=32)
        return float(result)

    def update(self, afterstate, target, alpha=ALPHA):
        board = self._board(afterstate)
        unique = np.zeros(1, dtype=np.int32)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        error = self.library.contextual_update_v134(board, self.patterns, self.extra_cells,
            self.radix, self.mode, self.weights, float(target), float(alpha), unique, counts)
        self._add_counts(counts)
        self.updates += 1
        self.counts.update(td_updates=1, value_predictions=1, table_lookups=32,
            table_updates=int(unique[0]), table_update_occurrences=32)
        return float(error)

    def choose(self, board, query):
        board = self._board(board, terminal_allowed=True)
        before = self.counts.copy()
        self.counts.update(choose_calls=1, learned_terminal_checks=1)
        goal, failure = float(query.get('goal_bonus', 0.)), float(query.get('failure_penalty', 0.))
        if int(board.max()) >= self.radix:
            self.counts['terminal_goal_bypasses'] += 1
            return dict(action=None, afterstate=board.tolist(), score=0, value=goal,
                tail_value=goal, action_values={}, status='WON', counts=_delta(self.counts, before))
        moved = np.empty((4, 16), dtype=np.int32)
        scores = np.zeros(4, dtype=np.int64)
        tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4, dtype=np.int32)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        best = self.library.contextual_choose_v134(board, self.patterns, self.extra_cells,
            self.radix, self.mode, self.weights, self.table, self.scores, self.cells,
            float(query.get('reward_weight', 1.)), goal, moved, scores, tails, values, legal, counts)
        self._add_counts(counts)
        if best < 0:
            return dict(action=None, afterstate=board.tolist(), score=0, value=-failure,
                tail_value=-failure, action_values={}, status='LOST', counts=_delta(self.counts, before))
        action_values = {action: dict(afterstate=moved[index].tolist(), score=int(scores[index]),
            tail_value=float(tails[index]), value=float(values[index]))
            for index, action in enumerate(ACTIONS) if legal[index]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
            status='ACTIVE', counts=_delta(self.counts, before))

    def save(self, path):
        started = perf_counter()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.weights.reshape(-1)
        indices = np.flatnonzero(flat)
        self.counts.update(checkpoint_saves=1, checkpoint_scanned_parameters=flat.size,
            checkpoint_saved_parameters=len(indices))
        metadata = dict(schema=MODEL_SCHEMA, patterns=PATTERNS, radix=self.radix,
            representation=self.representation, context_spec=CONTEXT_SPEC,
            counts=dict(self.counts), updates=self.updates, setup_counts=dict(self.setup_counts),
            setup_seconds=self.setup_seconds)
        with path.open('wb') as stream:
            np.savez_compressed(stream, indices=indices, values=flat[indices],
                metadata=json.dumps(metadata, sort_keys=True))
        self.last_save_seconds = perf_counter()-started
        return dict(path=str(path), parameter_count=int(flat.size), nonzero_weights=len(indices),
            updates=self.updates, bytes=path.stat().st_size, seconds=self.last_save_seconds)

    @classmethod
    def load(cls, path, rule, build_dir):
        started = perf_counter()
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data['metadata']))
            if (metadata['schema'] != MODEL_SCHEMA or metadata['radix'] != rule.goal_rank
                    or metadata['patterns'] != [list(pattern) for pattern in PATTERNS]
                    or metadata['context_spec'] != CONTEXT_SPEC):
                raise ValueError('checkpoint does not match V134 representation')
            model = cls(rule, metadata['representation'], build_dir)
            model.weights.reshape(-1)[data['indices']] = data['values']
            model.counts, model.updates = Counter(metadata['counts']), int(metadata['updates'])
            model.counts.update(checkpoint_loads=1, checkpoint_loaded_parameters=len(data['indices']))
            model.loaded_setup_counts = metadata['setup_counts']
            model.loaded_setup_seconds = metadata['setup_seconds']
        model.last_load_seconds = perf_counter()-started
        return model


class ConditionalQueryTD(QueryTD):
    """The unchanged query conversion and TD update around contextual tables."""

    def __init__(self, parent, representation='GLOBAL', build_dir=None):
        started = perf_counter()
        self._configure(parent, 'PRIOR')
        self.representation = representation
        self.model = ContextNtupleValue(parent.rule, representation, build_dir)
        self.setup_counts = self.model.setup_counts.copy()
        for bank in self.model.weights:
            np.copyto(bank, parent.source.weights)
        self.setup_counts.update(source_parameters_copied=self.weights.size,
            source_weight_bytes_copied=self.weights.nbytes)
        self.setup_seconds = perf_counter()-started

    def save(self, path):
        before, inner_before = self.counts.copy(), self.model.counts.copy()
        started = perf_counter()
        saved = self.model.save(path)
        self._charge(inner_before)
        self.counts['checkpoint_saves'] += 1
        sidecar = Path(path).with_suffix(Path(path).suffix+'.query.json')
        metadata = dict(schema=SCHEMA, kind=self.kind, representation=self.representation,
            context_spec=CONTEXT_SPEC, target_query=self.target_query, source_query=self.source_query,
            constant=self.constant, offset=self.offset, failure_shift=self.failure_shift,
            success_shift=self.success_shift, source_updates=self.source_updates,
            source_counts=self.source_counts, updates=self.updates, counts=dict(self.counts),
            setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds,
            frozen=not self.weights.flags.writeable)
        sidecar.write_text(json.dumps(metadata, sort_keys=True, indent=2)+'\n')
        return dict(saved, sidecar=str(sidecar), sidecar_bytes=sidecar.stat().st_size,
            seconds=perf_counter()-started, work=_delta(self.counts, before))

    @classmethod
    def load(cls, path, parent, build_dir):
        started = perf_counter()
        metadata = json.loads(Path(path).with_suffix(Path(path).suffix+'.query.json').read_text())
        result = cls.__new__(cls)
        result._configure(parent, metadata['kind'])
        result.representation = metadata['representation']
        if (metadata['schema'] != SCHEMA or metadata['context_spec'] != CONTEXT_SPEC
                or metadata['target_query'] != result.target_query
                or metadata['source_query'] != result.source_query or metadata['constant'] != result.constant
                or metadata['offset'] != result.offset or metadata['source_updates'] != parent.updates):
            raise ValueError('query checkpoint does not match its V134 source and query')
        result.model = ContextNtupleValue.load(path, parent.rule, build_dir)
        if result.model.representation != result.representation:
            raise ValueError('query and table representations differ')
        result.setup_counts = result.model.setup_counts.copy()
        result.setup_seconds = perf_counter()-started
        result.load_counts = dict(checkpoint_loads=1, inner_checkpoint_loads=1,
            inner_checkpoint_loaded_parameters=result.model.counts['checkpoint_loaded_parameters'])
        result.counts.update(result.load_counts)
        result.loaded_metadata, result.last_load_seconds = metadata, result.setup_seconds
        if metadata['frozen']:
            result.freeze()
        return result
