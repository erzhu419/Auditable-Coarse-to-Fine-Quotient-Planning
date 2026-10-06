"""Keep an immutable scalar policy anchor and learn bounded success slopes."""
from collections import Counter
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ACTIONS, PATTERNS, symmetry_patterns

SCHEMA = 'acfqp.anchored_success.v127'
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V127 build directory must be inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        path = build_dir / f'anchored_success_v127_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(Path(__file__).with_suffix('.cpp')), '-o', str(path)], check=True,
            capture_output=True, text=True, env=dict(os.environ, TMPDIR=str(build_dir)))
        library = ctypes.CDLL(str(path)); counts['cpp_compilations'] += 1
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci = ctypes.c_int
        library.success_fit_v127.argtypes = [ip, ci, ip, ci, up, up, ci]
        library.success_fit_v127.restype = ctypes.c_uint64
        library.success_predict_v127.argtypes = [ip, ci, ip, ci, up, up, ctypes.c_double, dp]
        library.success_predict_v127.restype = None
        library.success_replay_v127.argtypes = [ip, ip, ip, ip, lp, ci, ci, ip, lp, ip, ip, ip, up, ip]
        library.success_replay_v127.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _delta(after, before):
    return {key: value - before.get(key, 0) for key, value in after.items() if value != before.get(key, 0)}


class AnchoredSuccess:
    def __init__(self, source_model, source_query, build_dir):
        started = perf_counter()
        if source_query.get('reward_weight', 1.) != 1.:
            raise ValueError('V127 scalar anchors require reward weight one')
        self.source, self.source_query = source_model, dict(source_query)
        self.rule, self.radix = source_model.rule, source_model.radix
        self.counts, self.setup_counts = Counter(), Counter()
        self.library = _backend(build_dir, self.setup_counts)
        self.patterns = symmetry_patterns()
        self.visits = np.zeros((len(PATTERNS), self.radix**6), dtype=np.uint64)
        self.wins = np.zeros_like(self.visits)
        self.updates = self.successes = 0
        self.setup_counts.update(allocated_count_entries=self.visits.size + self.wins.size,
            allocated_count_bytes=self.visits.nbytes + self.wins.nbytes)
        self.setup_seconds = perf_counter() - started

    @property
    def global_success_rate(self):
        return self.successes / self.updates if self.updates else .5

    def _boards(self, boards):
        result = np.ascontiguousarray(boards, dtype=np.int32)
        if result.size == 0:
            return np.empty((0, 16), dtype=np.int32)
        if result.ndim != 2 or result.shape[1] != 16 or np.any(result < 0):
            raise ValueError('afterstates must be an N by 16 array of nonnegative ranks')
        return result

    def replay(self, row):
        """Recover afterstates from existing actions and spawn records only."""
        n = len(row['actions'])
        if any(len(row[name]) != n for name in ('spawned_cells', 'spawned_ranks', 'scores')):
            raise ValueError('retained replay arrays must align')
        initial = self._boards([row['initial_board']])[0]
        final = self._boards([row['final_board']])[0]
        actions = np.ascontiguousarray([ACTIONS.index(a) for a in row['actions']], dtype=np.int32)
        cells = np.ascontiguousarray(row['spawned_cells'], dtype=np.int32)
        ranks = np.ascontiguousarray(row['spawned_ranks'], dtype=np.int32)
        scores = np.ascontiguousarray(row['scores'], dtype=np.int64)
        afterstates = np.empty((n, 16), dtype=np.int32)
        work = np.zeros(3, dtype=np.uint64); failed_step = np.empty(1, dtype=np.int32)
        error = self.library.success_replay_v127(initial, actions, cells, ranks, scores,
            n, self.radix, self.source.table, self.source.scores, self.source.cells,
            final, afterstates, work, failed_step)
        self.counts['replay_games'] += 1
        self.counts.update({key: int(value) for key, value in zip(
            ('replay_swipe_calls', 'replay_line_table_lookups', 'replay_recorded_spawns'), work)})
        if error:
            reason = {1: 'action', 2: 'board rank or action after terminal', 3: 'illegal swipe',
                4: 'score', 5: 'spawn', 6: 'final board'}[error]
            raise ValueError(f'retained replay disagrees at step {int(failed_step[0])}: {reason}')
        return afterstates

    def train_episode(self, afterstates, status):
        if not self.visits.flags.writeable or not self.wins.flags.writeable:
            raise RuntimeError('evaluation success counts cannot be updated')
        boards = self._boards(afterstates); n = len(boards)
        self.counts.update(training_games=1, training_observed_afterstates=n)
        if status == 'CUTOFF':
            self.counts.update(censored_games=1, censored_afterstates=n)
            return dict(status=status, observed_afterstates=n, updates=0, successes=0,
                success_afterstates=0, unique_feature_updates=0,
                analytic_goals=0, censored_afterstates=n)
        if status not in ('WON', 'LOST'):
            raise ValueError('success labels require a complete terminal game')
        goals = int(np.count_nonzero(np.max(boards, axis=1) >= self.radix)) if n else 0
        eligible, success = n - goals, int(status == 'WON')
        unique = int(self.library.success_fit_v127(boards, n, self.patterns, self.radix,
            self.visits, self.wins, success))
        self.updates += eligible; self.successes += success * eligible
        self.counts.update(success_observation_updates=eligible, unique_feature_updates=unique,
            count_array_writes=2 * unique, feature_address_occurrences=32 * eligible,
            training_analytic_goals=goals)
        return dict(status=status, observed_afterstates=n, updates=eligible,
            successes=success * eligible, success_afterstates=success * eligible,
            unique_feature_updates=unique,
            analytic_goals=goals, censored_afterstates=0)

    def probabilities(self, afterstates):
        boards = self._boards(afterstates); output = np.empty(len(boards))
        self.library.success_predict_v127(boards, len(boards), self.patterns, self.radix,
            self.visits, self.wins, self.global_success_rate, output)
        goals = int(np.count_nonzero(np.max(boards, axis=1) >= self.radix)) if len(boards) else 0
        self.counts.update(success_predictions=len(boards), terminal_goal_bypasses=goals,
            probability_feature_occurrences=32 * (len(boards) - goals),
            count_array_reads=64 * (len(boards) - goals))
        return output.tolist()

    def choose(self, board, query, mode='LEARNED'):
        if mode not in ('LEARNED', 'CONSTANT'):
            raise ValueError('success prediction mode must be LEARNED or CONSTANT')
        if query.get('reward_weight', 1.) != 1.:
            raise ValueError('V127 anchored queries require reward weight one')
        before = self.source.counts.copy()
        choice = self.source.choose(board, self.source_query)
        self.counts.update({f'source_{key}': value for key, value in _delta(self.source.counts, before).items()})
        self.counts['choose_calls'] += 1
        same = all(query.get(k, default) == self.source_query.get(k, default)
            for k, default in (('reward_weight', 1.), ('failure_penalty', 0.), ('goal_bonus', 0.)))
        if same:
            self.counts['exact_anchor_bypasses'] += 1
            values = {action: dict(row, anchor_value=row['value'], success_probability=None)
                      for action, row in choice['action_values'].items()}
            return dict(choice, action_values=values, anchor_value=choice['value'], success_probability=None)
        f_source = self.source_query.get('failure_penalty', 0.)
        g_source = self.source_query.get('goal_bonus', 0.)
        failure, goal = query.get('failure_penalty', 0.), query.get('goal_bonus', 0.)
        if not choice['action_values']:
            value = goal if choice['status'] == 'WON' else -failure
            return dict(choice, value=float(value), tail_value=float(value),
                anchor_value=choice['value'], success_probability=float(choice['status'] == 'WON'))
        actions = choice['action_values']
        if mode == 'LEARNED':
            probabilities = self.probabilities([row['afterstate'] for row in actions.values()])
        else:
            probabilities = [1. if max(row['afterstate']) >= self.radix else self.global_success_rate
                             for row in actions.values()]
            self.counts['constant_probability_predictions'] += len(probabilities)
        values = {}
        for (action, row), probability in zip(actions.items(), probabilities):
            if max(row['afterstate']) >= self.radix:
                value = row['score'] / 2048. + goal
            else:
                value = row['value'] + (f_source - failure) + ((failure + goal) - (f_source + g_source)) * probability
            values[action] = dict(row, value=float(value), success_probability=probability,
                anchor_value=row['value'], tail_value=float(value) - row['score'] / 2048.)
        action = max(values, key=lambda key: values[key]['value'])
        return dict(action=action, **values[action], action_values=values, status='ACTIVE')

    def save(self, path):
        started = perf_counter(); path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        flat_visits, flat_wins = self.visits.reshape(-1), self.wins.reshape(-1)
        indices = np.flatnonzero(flat_visits)
        self.counts.update(checkpoint_saves=1, checkpoint_scanned_entries=flat_visits.size,
            checkpoint_saved_addresses=len(indices), checkpoint_saved_count_entries=2 * len(indices))
        metadata = dict(schema=SCHEMA, radix=self.radix, patterns=PATTERNS,
            source_query=self.source_query, source_updates=self.source.updates,
            updates=self.updates, successes=self.successes, global_success_rate=self.global_success_rate,
            counts=dict(self.counts), setup_counts=dict(self.setup_counts), setup_seconds=self.setup_seconds)
        with path.open('wb') as stream:
            np.savez_compressed(stream, indices=indices, visits=flat_visits[indices],
                wins=flat_wins[indices], metadata=json.dumps(metadata, sort_keys=True))
        return dict(path=str(path), address_count=int(flat_visits.size), nonzero_addresses=len(indices),
            updates=self.updates, successes=self.successes, bytes=path.stat().st_size,
            seconds=perf_counter() - started)


def choose_gpi(models, board, query, mode='LEARNED'):
    choices = [model.choose(board, query, mode=mode) for model in models]
    candidates = [(row['value'], action, index, row) for index, choice in enumerate(choices)
                  for action, row in choice['action_values'].items()]
    if not candidates:
        return dict(choices[0], policy_index=0, per_policy_action_values=[c['action_values'] for c in choices])
    _, action, index, row = min(candidates, key=lambda item: (-item[0], item[1], item[2]))
    values = {}
    for _, a, policy, candidate in candidates:
        if a not in values or candidate['value'] > values[a]['value']:
            values[a] = dict(candidate, policy_index=policy)
    return dict(action=action, **row, policy_index=index, action_values=values,
        per_policy_action_values=[choice['action_values'] for choice in choices], status='ACTIVE')
