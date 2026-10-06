"""Target-query TD with an exactly budgeted, resumable stream of natural games.

The source initializes a private n-tuple table. Its fixed query conversion is
part of the prediction and is subtracted once when fitting the raw table.
"""
from collections import Counter
import json
from pathlib import Path
import random
from time import perf_counter

import numpy as np

from acfqp.domains import standard_2048 as ground
from .controlled_predictive_lifelong_experience_v77 import _status
from .controlled_predictive_ntuple_td_v120 import ALPHA, NtupleValue
from .controlled_predictive_paired_ntuple_v130 import _delta, _same_query
from .controlled_predictive_regime_experience_v115 import _spawn

SCHEMA = 'acfqp.online_query_td.v131'


class QueryTD:
    """One target query, with a private trainable copy or zero initialization."""

    def __init__(self, parent, kind='PRIOR', build_dir=None):
        started = perf_counter()
        self._configure(parent, kind)
        self.model = NtupleValue(parent.rule, build_dir)
        self.setup_counts = self.model.setup_counts.copy()
        if kind == 'PRIOR':
            np.copyto(self.model.weights, parent.source.weights)
            self.setup_counts.update(source_parameters_copied=self.model.weights.size,
                source_weight_bytes_copied=self.model.weights.nbytes)
        self.setup_seconds = perf_counter()-started

    def _configure(self, parent, kind):
        if kind not in ('PRIOR', 'SCRATCH'):
            raise ValueError('query TD kind must be PRIOR or SCRATCH')
        self.parent, self.kind = parent, kind
        self.rule, self.radix = parent.rule, parent.radix
        self.target_query = dict(parent.target_query)
        self.source_query = dict(parent.source_query)
        self.constant = parent.constant
        fs, gs = (self.source_query.get(key, 0.) for key in ('failure_penalty', 'goal_bonus'))
        ft, gt = (self.target_query.get(key, 0.) for key in ('failure_penalty', 'goal_bonus'))
        self.failure_shift = float(fs-ft) if kind == 'PRIOR' else 0.
        self.success_shift = float(((ft+gt)-(fs+gs))*self.constant) if kind == 'PRIOR' else 0.
        self.offset = self.failure_shift+self.success_shift
        self.counts = Counter()
        self.source_updates = parent.updates
        self.source_counts = dict(parent.source.counts)

    @property
    def weights(self):
        return self.model.weights

    @property
    def updates(self):
        return self.model.updates

    def _charge(self, before):
        work = {f'inner_{key}': value for key, value in _delta(self.model.counts, before).items()}
        self.counts.update(work)

    def choose(self, board, query=None):
        if query is not None and not _same_query(query, self.target_query):
            raise ValueError('the TD target query is fixed')
        before, inner_before = self.counts.copy(), self.model.counts.copy()
        raw_query = self.source_query if self.kind == 'PRIOR' else self.target_query
        choice = self.model.choose(board, raw_query)
        self._charge(inner_before)
        self.counts['choose_calls'] += 1
        goal, failure = (self.target_query.get(key, 0.) for key in ('goal_bonus', 'failure_penalty'))
        if not choice['action_values']:
            value = float(goal if choice['status'] == 'WON' else -failure)
            return dict(choice, value=value, tail_value=value, raw_value=choice['value'],
                raw_tail_value=choice['tail_value'], base_value=value, offset=0.,
                counts=_delta(self.counts, before))
        values = {}
        same = _same_query(self.source_query, self.target_query)
        for action, row in choice['action_values'].items():
            winning = max(row['afterstate']) >= self.radix
            if winning:
                value, applied_offset = row['score']/2048.+goal, 0.
            elif self.kind == 'SCRATCH' or same:
                value, applied_offset = row['value'], self.offset
            else:
                # Match QueryParent's two additions, including their rounding.
                value = row['value']+self.failure_shift+self.success_shift
                applied_offset = self.offset
            raw_value = row['score']/2048. if winning else row['value']
            values[action] = dict(row, value=float(value), raw_value=raw_value,
                raw_tail_value=0. if winning else row['tail_value'], base_value=raw_value,
                offset=applied_offset, tail_value=float(goal) if winning else value-row['score']/2048.)
        action = min(values, key=lambda name: (-values[name]['value'], name))
        return dict(action=action, **values[action], action_values=values,
            status='ACTIVE', counts=_delta(self.counts, before))

    def update(self, afterstate, target, alpha=ALPHA):
        if not self.weights.flags.writeable:
            raise RuntimeError('frozen query TD weights cannot be updated')
        before, inner_before = self.counts.copy(), self.model.counts.copy()
        raw_target = float(target)-self.offset
        error = self.model.update(afterstate, raw_target, alpha)
        self._charge(inner_before)
        self.counts['td_updates'] += 1
        return dict(target=float(target), raw_target=raw_target, error=error,
            work=_delta(self.counts, before))

    def freeze(self):
        self.weights.flags.writeable = False

    def save(self, path):
        before, inner_before = self.counts.copy(), self.model.counts.copy()
        started = perf_counter()
        saved = self.model.save(path)
        self._charge(inner_before)
        self.counts['checkpoint_saves'] += 1
        sidecar = Path(path).with_suffix(Path(path).suffix+'.query.json')
        metadata = dict(schema=SCHEMA, kind=self.kind, target_query=self.target_query,
            source_query=self.source_query, constant=self.constant, offset=self.offset,
            failure_shift=self.failure_shift, success_shift=self.success_shift,
            source_updates=self.source_updates, source_counts=self.source_counts,
            updates=self.updates, counts=dict(self.counts), setup_counts=dict(self.setup_counts),
            setup_seconds=self.setup_seconds, frozen=not self.weights.flags.writeable)
        sidecar.write_text(json.dumps(metadata, sort_keys=True, indent=2)+'\n')
        return dict(saved, sidecar=str(sidecar), sidecar_bytes=sidecar.stat().st_size,
            seconds=perf_counter()-started, work=_delta(self.counts, before))

    @classmethod
    def load(cls, path, parent, build_dir):
        started = perf_counter()
        metadata = json.loads(Path(path).with_suffix(Path(path).suffix+'.query.json').read_text())
        result = cls.__new__(cls)
        result._configure(parent, metadata['kind'])
        if (metadata['schema'] != SCHEMA or metadata['target_query'] != result.target_query
                or metadata['source_query'] != result.source_query or metadata['constant'] != result.constant
                or metadata['offset'] != result.offset or metadata['source_updates'] != parent.updates):
            raise ValueError('query TD checkpoint does not match its declared source and query')
        result.model = NtupleValue.load(path, parent.rule, build_dir)
        result.setup_counts = result.model.setup_counts.copy()
        result.setup_seconds = perf_counter()-started
        result.load_counts = dict(checkpoint_loads=1,
            inner_checkpoint_loads=1,
            inner_checkpoint_loaded_parameters=result.model.counts['checkpoint_loaded_parameters'])
        result.counts.update(result.load_counts)
        result.loaded_metadata = metadata
        result.last_load_seconds = result.setup_seconds
        if metadata['frozen']:
            result.freeze()
        return result


class TDStream:
    """Suspend only between observed transitions; preserve RNG and pending TD.

    An ACTIVE segment end is a budget boundary, not an environment terminal.
    Its last afterstate awaits the next observed state's chosen value. A real
    2,000-step cutoff instead drops that pending fit and starts a new game.
    """

    def __init__(self, model, seed_fn, max_steps=2000, p_four=.1):
        if max_steps <= 0 or not 0. <= p_four <= 1.:
            raise ValueError('invalid natural-game step limit or spawn probability')
        self.model, self.seed_fn = model, seed_fn
        self.max_steps, self.p_four = max_steps, p_four
        self.environment_counts, self.training_counts = Counter(), Counter()
        self.transitions = self.episodes_started = self.episodes_completed = 0
        self.episode, self.step = -1, 0
        self.board = self.pending = self.rng = self.seed = self.status = None
        self.return_score = 0

    def _start(self):
        self.episode += 1
        self.seed = int(self.seed_fn(self.episode))
        self.rng = random.Random(self.seed)
        self.board, self.pending, self.step, self.return_score = (0,)*16, None, 0, 0
        initial_spawns = []
        for _ in range(2):
            self.board, cell, rank = _spawn(self.board, self.rng, self.environment_counts, self.p_four)
            self.environment_counts['initial_spawns'] += 1
            initial_spawns.append(dict(cell=cell, rank=rank))
        self.status = _status(self.board, self.environment_counts)
        self.episodes_started += 1
        return initial_spawns

    def advance_to(self, total):
        if total < self.transitions:
            raise ValueError('the transition budget cannot go backwards')
        return self.advance(total-self.transitions)

    def advance(self, n_transitions):
        if not isinstance(n_transitions, int) or n_transitions < 0:
            raise ValueError('advance requires a nonnegative integer transition budget')
        rows, remaining = [], n_transitions
        while remaining:
            started = perf_counter()
            env_before, model_before = self.environment_counts.copy(), self.model.counts.copy()
            updates_before = self.model.updates
            initial_spawns = self._start() if self.status != 'ACTIVE' else None
            start_board, start_step = list(self.board), self.step
            pending_before = None if self.pending is None else list(self.pending)
            actions, scores, cells, ranks, values, raw_values = [], [], [], [], [], []
            targets, raw_targets, errors = [], [], []
            terminal_update, censored_last_update = None, False
            while remaining and self.status == 'ACTIVE':
                chosen = self.model.choose(self.board)
                update = None if self.pending is None else self.model.update(self.pending, chosen['value'])
                targets.append(None if update is None else update['target'])
                raw_targets.append(None if update is None else update['raw_target'])
                errors.append(None if update is None else update['error'])
                self.pending = (None if max(chosen['afterstate']) >= self.model.rule.goal_rank
                    else tuple(chosen['afterstate']))
                action = ground.Swipe2048Action(chosen['action'])
                self.environment_counts.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
                afterstate, score, changed = ground.swipe_board_v1(self.board, action)
                if not changed:
                    raise ValueError(f'illegal action {action.value} at episode {self.episode} step {self.step}')
                self.board, cell, rank = _spawn(afterstate, self.rng, self.environment_counts, self.p_four)
                self.environment_counts['sampled_transitions'] += 1
                self.status = _status(self.board, self.environment_counts)
                self.transitions += 1
                self.step += 1
                self.return_score += score
                remaining -= 1
                actions.append(action.value); scores.append(score); cells.append(cell); ranks.append(rank)
                values.append(chosen['value']); raw_values.append(chosen['raw_value'])
                if self.status == 'LOST' and self.pending is not None:
                    terminal_update = self.model.update(self.pending, -self.model.target_query['failure_penalty'])
                    terminal_update['afterstate'] = list(self.pending)
                    self.pending = None
                if self.status == 'ACTIVE' and self.step == self.max_steps:
                    self.status, censored_last_update = 'CUTOFF', self.pending is not None
                    self.pending = None
                if self.status != 'ACTIVE':
                    self.episodes_completed += 1
            environment_counts = _delta(self.environment_counts, env_before)
            model_counts = _delta(self.model.counts, model_before)
            self.training_counts.update(model_counts)
            row = dict(episode=self.episode, seed=self.seed, start_step=start_step, end_step=self.step,
                start_board=start_board, end_board=list(self.board), actions=actions, scores=scores,
                spawned_cells=cells, spawned_ranks=ranks, chosen_values=values, chosen_raw_values=raw_values,
                td_targets=targets, raw_td_targets=raw_targets, td_errors=errors, terminal_update=terminal_update,
                pending_before=pending_before, pending_after=None if self.pending is None else list(self.pending),
                updates_before=updates_before, updates_after=self.model.updates,
                cumulative_transitions=self.transitions, cumulative_updates=self.model.updates,
                environment_counts=environment_counts, model_counts=model_counts,
                status=self.status, budget_status='BUDGET_END' if self.status == 'ACTIVE' else 'EPISODE_END',
                censored_last_update=censored_last_update, return_score=self.return_score,
                seconds=perf_counter()-started)
            if initial_spawns is not None:
                row['initial_spawns'] = initial_spawns
            rows.append(row)
        return rows
