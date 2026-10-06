"""Fixed-horizon afterstate TD on the learner's own resumable game stream.

Each non-goal afterstate is fitted once, when its horizon is observed or the
episode ends. Budget boundaries retain the entire unresolved queue. The tail
is the one action value selected before that decision's updates.
"""
from collections import Counter, deque
from time import perf_counter

from . import controlled_predictive_online_query_td_v131 as single
from .controlled_predictive_paired_ntuple_v130 import _delta

SCHEMA = 'acfqp.multistep_query_td.v133'
HORIZON = 32


class MultiStepTDStream(single.TDStream):
    """A fixed n-step target, with analytic termination and no extra samples."""

    def __init__(self, model, seed_fn, horizon=HORIZON, max_steps=2000, p_four=.1):
        if not isinstance(horizon, int) or horizon < 1:
            raise ValueError('the TD horizon must be a positive integer')
        super().__init__(model, seed_fn, max_steps, p_four)
        self.horizon = horizon
        self.queue = deque()
        self.target_counts = Counter()

    def _start(self):
        initial_spawns = super()._start()
        self.queue.clear()
        return initial_spawns

    def queue_state(self):
        return [dict(step=entry['step'], afterstate=list(entry['afterstate']),
                     score_prefix=entry['score_prefix']) for entry in self.queue]

    def _fit_oldest(self, kind, phase, end_step, score_prefix, tail):
        entry = self.queue.popleft()
        reward_score = score_prefix-entry['score_prefix']
        target = reward_score/2048.+tail
        update = self.model.update(entry['afterstate'], target)
        self.target_counts.update(queue_removals=1, target_constructions=1)
        self.target_counts[f'{kind.lower()}_updates'] += 1
        return dict(start_step=entry['step'], end_step=end_step, type=kind, phase=phase,
            afterstate=list(entry['afterstate']), reward_score=reward_score,
            tail=float(tail), **update)

    def advance(self, n_transitions):
        if not isinstance(n_transitions, int) or n_transitions < 0:
            raise ValueError('advance requires a nonnegative integer transition budget')
        rows, remaining = [], n_transitions
        while remaining:
            started = perf_counter()
            env_before, model_before = self.environment_counts.copy(), self.model.counts.copy()
            target_before_counts = self.target_counts.copy()
            updates_before = self.model.updates
            initial_spawns = self._start() if self.status != 'ACTIVE' else None
            start_board, start_step = list(self.board), self.step
            queue_before, start_return_score = self.queue_state(), self.return_score
            actions, scores, cells, ranks, values, raw_values = [], [], [], [], [], []
            update_records, censored_updates = [], 0
            while remaining and self.status == 'ACTIVE':
                # This value is captured once, before all fits at this decision.
                chosen = self.model.choose(self.board)
                winning = max(chosen['afterstate']) >= self.model.rule.goal_rank
                if self.queue and self.step-self.queue[0]['step'] >= self.horizon:
                    kind = 'WIN_BOUNDARY' if winning else 'BOOTSTRAP'
                    update_records.append(self._fit_oldest(kind, 'PRE_ACTION', self.step,
                        self.return_score, chosen['value']))

                action = single.ground.Swipe2048Action(chosen['action'])
                self.environment_counts.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
                afterstate, score, changed = single.ground.swipe_board_v1(self.board, action)
                if not changed:
                    raise ValueError(f'illegal action {action.value} at episode {self.episode} step {self.step}')
                self.board, cell, rank = single._spawn(afterstate, self.rng,
                    self.environment_counts, self.p_four)
                self.environment_counts['sampled_transitions'] += 1
                self.status = single._status(self.board, self.environment_counts)
                self.return_score += score
                if not winning:
                    self.queue.append(dict(step=self.step, afterstate=tuple(chosen['afterstate']),
                        score_prefix=self.return_score))
                    self.target_counts['queue_appends'] += 1
                if self.status == 'WON':
                    while self.queue:
                        update_records.append(self._fit_oldest('WIN_BOUNDARY', 'POST_TERMINAL',
                            self.step, self.return_score, self.model.target_query['goal_bonus']))
                elif self.status == 'LOST':
                    while self.queue:
                        update_records.append(self._fit_oldest('LOSS', 'POST_TERMINAL', self.step,
                            self.return_score, -self.model.target_query['failure_penalty']))
                self.transitions += 1
                self.step += 1
                remaining -= 1
                actions.append(action.value); scores.append(score); cells.append(cell); ranks.append(rank)
                values.append(chosen['value']); raw_values.append(chosen['raw_value'])
                if self.status == 'ACTIVE' and self.step == self.max_steps:
                    self.status, censored_updates = 'CUTOFF', len(self.queue)
                    censored_queue = self.queue_state()
                    self.target_counts['censored_updates'] += censored_updates
                    self.queue.clear()
                if self.status != 'ACTIVE':
                    self.episodes_completed += 1
            environment_counts = _delta(self.environment_counts, env_before)
            model_counts = _delta(self.model.counts, model_before)
            self.training_counts.update(model_counts)
            row = dict(episode=self.episode, seed=self.seed, start_step=start_step, end_step=self.step,
                start_board=start_board, end_board=list(self.board), actions=actions, scores=scores,
                spawned_cells=cells, spawned_ranks=ranks, chosen_values=values, chosen_raw_values=raw_values,
                horizon=self.horizon, update_records=update_records,
                queue_before=queue_before, queue_after=self.queue_state(),
                updates_before=updates_before, updates_after=self.model.updates,
                cumulative_transitions=self.transitions, cumulative_updates=self.model.updates,
                environment_counts=environment_counts, model_counts=model_counts,
                target_counts=_delta(self.target_counts, target_before_counts), status=self.status,
                budget_status='BUDGET_END' if self.status == 'ACTIVE' else 'EPISODE_END',
                censored_updates=censored_updates, start_return_score=start_return_score,
                return_score=self.return_score, seconds=perf_counter()-started)
            if initial_spawns is not None:
                row['initial_spawns'] = initial_spawns
            if self.status == 'CUTOFF':
                row['censored_queue'] = censored_queue
            rows.append(row)
        return rows
