"""Fixed query parents and normalized paired n-tuple residual learning."""
from collections import Counter
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ACTIONS, PATTERNS

SCHEMA = 'acfqp.paired_ntuple.v130'
_LIBRARIES = {}
_PAIR_COUNTS = ('pair_feature_occurrences', 'pair_distinct_addresses',
    'pair_nonzero_difference_addresses', 'pair_signed_difference_occurrences',
    'pair_table_lookups', 'pair_table_updates', 'pair_update_occurrences',
    'pair_terminal_goal_bypasses')


def _delta(after, before):
    return {key: value-before.get(key, 0) for key, value in after.items()
            if value != before.get(key, 0)}


def _same_query(left, right):
    return all(left.get(key, default) == right.get(key, default) for key, default in
        (('reward_weight', 1.), ('failure_penalty', 0.), ('goal_bonus', 0.)))


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V130 build directory must be inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        path = build_dir/f'paired_ntuple_v130_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(Path(__file__).with_suffix('.cpp')), '-o', str(path)], check=True,
            capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(build_dir)))
        library = ctypes.CDLL(str(path)); counts['cpp_compilations'] += 1
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.residual_predict_v130.argtypes = [ip, ci, ip, ci, dp, dp]
        library.residual_predict_v130.restype = None
        library.residual_pair_fit_v130.argtypes = [ip, ip, ci, dp, cd, cd, cd, dp, up]
        library.residual_pair_fit_v130.restype = None
        library.residual_actions_v130.argtypes = [ip, ci, ip, lp, ip, ip, lp, ip]
        library.residual_actions_v130.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class QueryParent:
    """V127 CONSTANT single-policy readout without the success-count tables."""
    def __init__(self, source, source_query, target_query, constant):
        if source_query.get('reward_weight', 1.) != 1. or target_query.get('reward_weight', 1.) != 1.:
            raise ValueError('V130 fixed query parents require reward weight one')
        if not 0. <= constant <= 1.:
            raise ValueError('the fixed success constant must be a probability')
        self.source, self.source_query = source, dict(source_query)
        self.target_query, self.constant = dict(target_query), float(constant)
        self.rule, self.radix = source.rule, source.radix
        self.counts = Counter()

    @property
    def updates(self):
        return self.source.updates

    def choose(self, board, query=None):
        if query is not None and not _same_query(query, self.target_query):
            raise ValueError('the parent query is fixed')
        before, source_before = self.counts.copy(), self.source.counts.copy()
        choice = self.source.choose(board, self.source_query)
        self.counts.update({f'source_{key}': value
            for key, value in _delta(self.source.counts, source_before).items()})
        self.counts['choose_calls'] += 1
        same = _same_query(self.source_query, self.target_query)
        failure, goal = (self.target_query.get(key, 0.) for key in ('failure_penalty', 'goal_bonus'))
        if not choice['action_values']:
            value = choice['value'] if same else float(goal if choice['status'] == 'WON' else -failure)
            return dict(choice, value=value, tail_value=value, anchor_value=choice['value'],
                success_probability=None if same else float(choice['status'] == 'WON'),
                counts=_delta(self.counts, before))
        fs, gs = (self.source_query.get(key, 0.) for key in ('failure_penalty', 'goal_bonus'))
        values = {}
        for action, row in choice['action_values'].items():
            probability = 1. if max(row['afterstate']) >= self.radix else self.constant
            value = row['value'] if same else (row['score']/2048. + goal
                if max(row['afterstate']) >= self.radix else
                row['value'] + (fs-failure) + ((failure+goal)-(fs+gs))*probability)
            values[action] = dict(row, value=float(value), anchor_value=row['value'],
                success_probability=None if same else probability,
                tail_value=row['tail_value'] if same else float(value)-row['score']/2048.)
        if same:
            self.counts['exact_anchor_bypasses'] += 1
        else:
            self.counts['constant_probability_predictions'] += len(values)
        action = min(values, key=lambda a: (-values[a]['value'], a))
        return dict(action=action, **values[action], action_values=values,
            status='ACTIVE', counts=_delta(self.counts, before))


class PairResidual:
    def __init__(self, parent, kind='PRIOR', build_dir=None):
        if kind not in ('PRIOR', 'SCRATCH'):
            raise ValueError('paired residual kind must be PRIOR or SCRATCH')
        if build_dir is None:
            raise ValueError('a project-local build directory is required')
        started = perf_counter()
        self.parent, self.kind, self.source = parent, kind, parent.source
        self.rule, self.radix, self.patterns = parent.rule, parent.radix, parent.source.patterns
        self.counts, self.setup_counts = Counter(), Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.weights = np.zeros((len(PATTERNS), self.radix**6), dtype=np.float64)
        self.updates = 0
        self.setup_counts.update(allocated_weight_parameters=self.weights.size,
            allocated_weight_bytes=self.weights.nbytes)
        self.setup_seconds = perf_counter()-started

    def _boards(self, boards):
        result = np.ascontiguousarray(boards, dtype=np.int32)
        if result.size == 0:
            return np.empty((0, 16), dtype=np.int32)
        if result.ndim != 2 or result.shape[1] != 16 or np.any(result < 0):
            raise ValueError('afterstates must be N by 16 nonnegative ranks')
        return result

    def residuals(self, afterstates):
        boards = self._boards(afterstates); output = np.empty(len(boards), dtype=np.float64)
        self.library.residual_predict_v130(boards, len(boards), self.patterns,
            self.radix, self.weights, output)
        goals = int(np.count_nonzero(np.max(boards, axis=1) >= self.radix)) if len(boards) else 0
        self.counts.update(residual_predictions=len(boards)-goals,
            residual_table_lookups=32*(len(boards)-goals), residual_terminal_goal_bypasses=goals)
        return output.tolist()

    def _scratch_actions(self, board):
        board = self._boards([board])[0]
        query = self.parent.target_query
        self.counts['learned_terminal_checks'] += 1
        if int(board.max()) >= self.radix:
            return dict(action=None, afterstate=board.tolist(), score=0,
                value=float(query.get('goal_bonus', 0.)), action_values={}, status='WON')
        moved = np.empty((4, 16), dtype=np.int32)
        scores, legal = np.empty(4, dtype=np.int64), np.empty(4, dtype=np.int32)
        self.library.residual_actions_v130(board, self.radix, self.source.table,
            self.source.scores, self.source.cells, moved, scores, legal)
        self.counts.update(learned_swipe_calls=4, line_table_lookups=16,
            legal_swipes=int(legal.sum()), learned_terminal_checks=int(legal.sum()))
        values = {action: dict(afterstate=moved[i].tolist(), score=int(scores[i]),
            value=float(scores[i]/2048. + (query.get('goal_bonus', 0.) if int(moved[i].max()) >= self.radix else 0.)))
            for i, action in enumerate(ACTIONS) if legal[i]}
        return dict(action=None, afterstate=board.tolist(), score=0,
            value=-float(query.get('failure_penalty', 0.)), action_values=values,
            status='ACTIVE' if values else 'LOST')

    def choose(self, board, query=None):
        if query is not None and not _same_query(query, self.parent.target_query):
            raise ValueError('the residual query is fixed')
        before = self.counts.copy(); self.counts['choose_calls'] += 1
        if self.kind == 'PRIOR':
            parent_before = self.parent.counts.copy(); choice = self.parent.choose(board)
            self.counts.update({f'parent_{key}': value
                for key, value in _delta(self.parent.counts, parent_before).items()})
        else:
            choice = self._scratch_actions(board)
        if not choice['action_values']:
            return dict(choice, base_value=choice['value'], residual=0., tail_value=choice['value'],
                counts=_delta(self.counts, before))
        residuals = self.residuals([row['afterstate'] for row in choice['action_values'].values()])
        values = {}
        for (action, row), residual in zip(choice['action_values'].items(), residuals):
            value = row['value'] + residual
            values[action] = dict(row, base_value=row['value'], residual=residual,
                value=value, tail_value=value-row['score']/2048.)
        action = min(values, key=lambda a: (-values[a]['value'], a))
        return dict(action=action, **values[action], action_values=values,
            status='ACTIVE', counts=_delta(self.counts, before))

    def fit_pair(self, after_a, after_b, base_gap, target_gap, rate=.1):
        if not self.weights.flags.writeable:
            raise RuntimeError('evaluation residual weights cannot be updated')
        started = perf_counter(); boards = self._boards([after_a, after_b])
        output, native = np.empty(3, dtype=np.float64), np.zeros(len(_PAIR_COUNTS), dtype=np.uint64)
        self.library.residual_pair_fit_v130(boards, self.patterns, self.radix, self.weights,
            float(base_gap), float(target_gap), float(rate), output, native)
        residual_gap, error, denominator = map(float, output)
        applied = denominator != 0.
        work = Counter({key: int(value) for key, value in zip(_PAIR_COUNTS, native)})
        work.update(pair_fit_calls=1, pair_updates=int(applied), unidentifiable_pairs=int(not applied))
        self.counts.update(work); self.updates += int(applied)
        return dict(base_gap=float(base_gap), target_gap=float(target_gap), rate=float(rate),
            residual_gap=residual_gap, predicted_gap=float(base_gap)+residual_gap,
            error=error, denominator=denominator, applied=applied, unidentifiable=not applied,
            work=dict(work), seconds=perf_counter()-started)

    def save(self, path):
        started = perf_counter(); path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.weights.reshape(-1); indices = np.flatnonzero(flat)
        self.counts.update(checkpoint_saves=1, checkpoint_scanned_parameters=flat.size,
            checkpoint_saved_parameters=len(indices))
        metadata = dict(schema=SCHEMA, kind=self.kind, radix=self.radix, patterns=PATTERNS,
            source_query=self.parent.source_query, target_query=self.parent.target_query,
            constant=self.parent.constant, source_updates=self.parent.updates, updates=self.updates,
            counts=dict(self.counts), setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds)
        with path.open('wb') as stream:
            np.savez_compressed(stream, indices=indices, values=flat[indices], metadata=json.dumps(metadata, sort_keys=True))
        self.last_save_seconds = perf_counter()-started
        return dict(path=str(path), parameter_count=flat.size, nonzero_weights=len(indices),
            updates=self.updates, bytes=path.stat().st_size, seconds=self.last_save_seconds)

    @classmethod
    def load(cls, path, parent, build_dir):
        started = perf_counter()
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data['metadata']))
            if (metadata['schema'] != SCHEMA or metadata['radix'] != parent.radix
                    or metadata['patterns'] != [list(p) for p in PATTERNS]
                    or metadata['source_query'] != parent.source_query
                    or metadata['target_query'] != parent.target_query
                    or metadata['constant'] != parent.constant or metadata['source_updates'] != parent.updates):
                raise ValueError('paired residual checkpoint does not match its fixed parent')
            model = cls(parent, metadata['kind'], build_dir)
            model.weights.reshape(-1)[data['indices']] = data['values']
            model.updates = int(metadata['updates'])
            model.load_counts = dict(checkpoint_loads=1, checkpoint_loaded_parameters=len(data['indices']))
            model.counts.update(model.load_counts)
        model.loaded_metadata, model.last_load_seconds = metadata, perf_counter()-started
        return model
