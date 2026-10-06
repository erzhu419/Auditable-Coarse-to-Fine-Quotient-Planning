"""Full-game Monte Carlo consequences conditioned on one fixed source policy.

Each afterstate stores remaining normalized score, terminal failure and terminal
success. New query weights combine the three consequences of the same policy.
The action's immediate score is added exactly once during action evaluation.
"""
from collections import Counter
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ALPHA, ACTIONS, PATTERNS, symmetry_patterns
from .controlled_predictive_relational_dynamics_v69 import _cells
from .controlled_predictive_rollout_consequences_v119 import _tables

SCHEMA = 'acfqp.policy_consequences.v126'
COMPONENTS = ('reward', 'failure', 'success')
_LIBRARIES = {}
_COUNTS = ('learned_swipe_calls', 'line_table_lookups', 'legal_swipes',
           'learned_terminal_checks', 'component_predictions', 'table_lookups',
           'terminal_goal_bypasses')


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V126 build directory must be inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir / f'policy_consequences_v126_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC',
            '-ffp-contract=off', str(source), '-o', str(path)], check=True,
            capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(build_dir)))
        library = ctypes.CDLL(str(path)); counts['cpp_compilations'] += 1
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        library.consequences_value_v126.argtypes = [ip, ip, ctypes.c_int, dp, dp]
        library.consequences_value_v126.restype = None
        library.consequences_update_v126.argtypes = [ip, ip, ctypes.c_int, dp, dp, ctypes.c_double, dp, ip]
        library.consequences_update_v126.restype = None
        library.consequences_actions_v126.argtypes = [ip, ip, ctypes.c_int, dp, ip, lp, ip, ip, lp, dp, ip, up]
        library.consequences_actions_v126.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def query_value(score, consequences, query):
    reward, failure, success = consequences
    return (float(query.get('reward_weight', 1.)) * (score / 2048. + reward)
        - float(query.get('failure_penalty', 0.)) * failure
        + float(query.get('goal_bonus', 0.)) * success)


def mc_targets(scores, status):
    """All tails exclude their own immediate reward and count a terminal once."""
    if status == 'CUTOFF':
        return []
    if status not in ('WON', 'LOST'):
        raise ValueError('MC targets require an ended game')
    reward = 0.; result = []
    for score in reversed(scores):
        result.append([reward, float(status == 'LOST'), float(status == 'WON')])
        reward += score / 2048.
    return list(reversed(result))


class PolicyConsequences:
    def __init__(self, rule, build_dir):
        started = perf_counter()
        self.rule, self.radix = rule, int(rule.goal_rank)
        self.counts, self.setup_counts = Counter(), Counter()
        self.updates = 0
        self.library = _backend(build_dir, self.setup_counts)
        self.table, self.scores = _tables(rule, self.setup_counts)
        self.patterns = symmetry_patterns()
        self.cells = np.asarray([[_cells(action, line) for line in range(4)] for action in ACTIONS], dtype=np.int32)
        self.weights = np.zeros((3, len(PATTERNS), self.radix**6), dtype=np.float64)
        self.setup_counts['allocated_weight_parameters'] += self.weights.size
        self.setup_counts['allocated_weight_bytes'] += self.weights.nbytes
        self.setup_seconds = perf_counter() - started

    def _board(self, board):
        result = np.ascontiguousarray(board, dtype=np.int32)
        if result.shape != (16,) or np.any(result < 0):
            raise ValueError('board must have 16 nonnegative ranks')
        return result

    def value(self, board):
        board = self._board(board)
        self.counts['vector_predictions'] += 1
        if np.max(board) >= self.radix:
            self.counts['terminal_goal_bypasses'] += 1
            return [0., 0., 1.]
        output = np.empty(3, dtype=np.float64)
        self.library.consequences_value_v126(board, self.patterns, self.radix, self.weights, output)
        self.counts['component_predictions'] += 3
        self.counts['table_lookups'] += 96
        return output.tolist()

    def vectors(self, afterstates):
        return [self.value(board) for board in afterstates]

    def update(self, afterstate, target):
        if not self.weights.flags.writeable:
            raise RuntimeError('evaluation consequences cannot update parameters')
        board = self._board(afterstate)
        if np.max(board) >= self.radix:
            raise ValueError('winning afterstates are analytic, not trainable')
        target = np.ascontiguousarray(target, dtype=np.float64)
        if target.shape != (3,):
            raise ValueError('one policy requires its joint three-component target')
        error = np.empty(3, dtype=np.float64); unique = np.empty(1, dtype=np.int32)
        self.library.consequences_update_v126(board, self.patterns, self.radix,
            self.weights, target, ALPHA, error, unique)
        self.updates += 1
        self.counts.update(mc_updates=1, component_updates=3, component_predictions=3,
            table_lookups=96, table_update_occurrences=96, table_updates=3 * int(unique[0]))
        return error.tolist()

    def train_episode(self, afterstates, scores, status):
        if len(afterstates) != len(scores):
            raise ValueError('MC afterstates and scores must align')
        self.counts['training_games'] += 1
        self.counts['training_observed_afterstates'] += len(afterstates)
        if status == 'CUTOFF':
            self.counts['censored_games'] += 1
            self.counts['censored_afterstates'] += len(afterstates)
            return dict(status=status, observed_afterstates=len(afterstates), updates=0,
                analytic_goals=0, censored_afterstates=len(afterstates),
                target_sums=[0., 0., 0.], head_updates=[0, 0, 0])
        targets = mc_targets(scores, status)
        before, goals = self.updates, 0
        target_sums = np.zeros(3)
        for board, target in zip(afterstates, targets):
            if max(board) >= self.radix:
                goals += 1; self.counts['training_analytic_goals'] += 1
            else:
                self.update(board, target)
                target_sums += target
        return dict(status=status, observed_afterstates=len(afterstates),
            updates=self.updates - before, analytic_goals=goals, censored_afterstates=0,
            target_sums=target_sums.tolist(), head_updates=[self.updates - before] * 3)

    def action_vectors(self, board):
        board = self._board(board)
        self.counts['action_vector_calls'] += 1
        self.counts['learned_terminal_checks'] += 1
        if np.max(board) >= self.radix:
            self.counts['terminal_goal_bypasses'] += 1
            return {}
        moved = np.empty((4, 16), dtype=np.int32); scores = np.zeros(4, dtype=np.int64)
        vectors = np.empty((4, 3), dtype=np.float64); legal = np.zeros(4, dtype=np.int32)
        counts = np.zeros(len(_COUNTS), dtype=np.uint64)
        self.library.consequences_actions_v126(board, self.patterns, self.radix,
            self.weights, self.table, self.scores, self.cells, moved, scores, vectors, legal, counts)
        self.counts.update({key: int(value) for key, value in zip(_COUNTS, counts)})
        self.counts['vector_predictions'] += int(counts[2])
        return {action: dict(afterstate=moved[i].tolist(), score=int(scores[i]),
            consequences=vectors[i].tolist()) for i, action in enumerate(ACTIONS) if legal[i]}

    def choose(self, board, query):
        self.counts['choose_calls'] += 1
        actions = self.action_vectors(board)
        if not actions:
            won = max(board) >= self.radix
            consequences = [0., 0., 1.] if won else [0., 1., 0.]
            return dict(action=None, afterstate=list(board), score=0,
                consequences=consequences, value=query_value(0, consequences, query),
                action_values={}, status='WON' if won else 'LOST')
        values = {a: dict(row, value=query_value(row['score'], row['consequences'], query))
                  for a, row in actions.items()}
        action = max(values, key=lambda a: values[a]['value'])
        return dict(action=action, **values[action], action_values=values, status='ACTIVE')

    def save(self, path):
        started = perf_counter(); path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.weights.reshape(-1); indices = np.flatnonzero(flat)
        self.counts.update(checkpoint_saves=1, checkpoint_scanned_parameters=flat.size,
            checkpoint_saved_parameters=len(indices))
        metadata = dict(schema=SCHEMA, radix=self.radix, patterns=PATTERNS,
            components=COMPONENTS, updates=self.updates, head_updates=[self.updates] * 3,
            counts=dict(self.counts),
            setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds)
        with path.open('wb') as stream:
            np.savez_compressed(stream, indices=indices, values=flat[indices], metadata=json.dumps(metadata, sort_keys=True))
        return dict(path=str(path), parameter_count=int(flat.size), nonzero_weights=len(indices),
            updates=self.updates, bytes=path.stat().st_size, seconds=perf_counter() - started)


def choose_gpi(models, board, query):
    """Compare whole policy-conditioned vectors, then use lexicographic ties."""
    choices = [model.choose(board, query) for model in models]
    candidates = [(value['value'], action, index, value)
        for index, choice in enumerate(choices) for action, value in choice['action_values'].items()]
    if not candidates:
        return dict(choices[0], policy_index=0,
            per_policy_action_values=[choice['action_values'] for choice in choices])
    _, action, index, value = min(candidates, key=lambda row: (-row[0], row[1], row[2]))
    action_values = {}
    for _, candidate_action, candidate_index, candidate in candidates:
        if candidate_action not in action_values or candidate['value'] > action_values[candidate_action]['value']:
            action_values[candidate_action] = dict(candidate, policy_index=candidate_index)
    return dict(action=action, **value, policy_index=index, action_values=action_values,
        per_policy_action_values=[choice['action_values'] for choice in choices], status='ACTIVE')
