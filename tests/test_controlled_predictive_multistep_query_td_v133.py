"""Finite scripted streams and native updates; no natural-game sampling."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import controlled_predictive_multistep_query_td_v133 as core
from acfqp.science import controlled_predictive_online_query_td_v131 as single
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_multistep_query_td_v133_build'
TARGET = dict(reward_weight=1., failure_penalty=8., goal_bonus=8.)
STREAMS, MODELS, SOURCES = [], [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_multistep_query_td_v133.core_checks.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        model_work=dict(sum((model.counts for model in MODELS), Counter())),
        source_work=dict(sum((model.counts for model in SOURCES), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in SOURCES+MODELS
            if hasattr(model, 'setup_counts')), Counter())),
        queue_work=dict(sum((stream.target_counts for stream in STREAMS
            if hasattr(stream, 'target_counts')), Counter())),
        scripted_environment_work=dict(sum((stream.environment_counts for stream in STREAMS), Counter())),
        newly_sampled_environment_transitions=0,
        scope='Finite scripted environment, native n-tuple update arithmetic, no natural-game samples.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


class ScriptModel:
    def __init__(self, scenario):
        self.scenario = scenario
        self.rule = SimpleNamespace(goal_rank=scenario.goal)
        self.target_query, self.offset = dict(TARGET), .3
        self.counts, self.updates, self.events = Counter(), 0, []
        self.weights = np.array([.4])

    def choose(self, board):
        self.events.append(('choose', board[0], float(self.weights[0])))
        self.counts['choose_calls'] += 1
        action = 'RIGHT' if self.weights[0] > .3 else 'DOWN'
        afterstate, score, _ = self.scenario.swipe(board, SimpleNamespace(value=action))
        tail = TARGET['goal_bonus'] if max(afterstate) >= self.rule.goal_rank else (
            float(self.weights[0])+board[0]*.2)
        value = score/2048.+tail
        return dict(action=action, afterstate=afterstate, score=score,
            value=value, raw_value=value-self.offset)

    def update(self, afterstate, target):
        self.events.append(('update', afterstate[0], float(self.weights[0]), target))
        error = target-self.offset-float(self.weights[0])
        self.weights[0] += .05*error
        self.updates += 1
        self.counts['td_updates'] += 1
        return dict(target=target, raw_target=target-self.offset, error=error, work=dict(td_updates=1))


class Scenario:
    def __init__(self, monkeypatch, limit=4, ending='LOST', goal=1000):
        self.limit, self.ending, self.goal = limit, ending, goal
        monkeypatch.setattr(single, '_spawn', self.spawn)
        monkeypatch.setattr(single, '_status', self.status)
        monkeypatch.setattr(single.ground, 'swipe_board_v1', self.swipe)

    def spawn(self, board, rng, work, p_four):
        cell_draw, rank_draw = rng.random(), rng.random()
        work['environment_random_draws'] += 2
        board = list(board)
        cell, rank = 14+int(cell_draw >= .5), 1+int(rank_draw >= 1.-p_four)
        board[cell] = rank
        return tuple(board), cell, rank

    def swipe(self, board, action):
        board = list(board)
        board[0] += 1
        if board[0] == self.limit and self.ending == 'WON':
            board[1] = self.goal
        return tuple(board), 4*board[0]+8*int(action.value == 'RIGHT'), True

    def status(self, board, work):
        work['ground_state_status_calls'] += 1
        return self.ending if board[0] == self.limit else 'ACTIVE'

    def native_model(self):
        rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
            ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', self.goal)
        source = NtupleValue(rule, BUILD)
        source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
        source.weights.flags.writeable = False
        SOURCES.append(source)
        parent = QueryParent(source, dict(reward_weight=1., failure_penalty=4., goal_bonus=4.),
            TARGET, .4)
        model = single.QueryTD(parent, 'PRIOR', BUILD)
        model.events = []

        def choose(board):
            # Scripted action candidates, with real native values and unchanged
            # QueryTD.update. This isolates stream ordering from natural games.
            before = model.model.counts.copy()
            prediction = model.model.value(board)
            model.events.append(('choose', board[0], prediction))
            action = 'RIGHT' if prediction > .1 else 'DOWN'
            afterstate, score, _ = self.swipe(board, SimpleNamespace(value=action))
            winning = max(afterstate) >= self.goal
            raw = score/2048.+(0. if winning else model.model.value(afterstate))
            value = score/2048.+TARGET['goal_bonus'] if winning else (
                raw+model.failure_shift+model.success_shift)
            model._charge(before)
            model.counts['choose_calls'] += 1
            return dict(action=action, afterstate=afterstate, score=score, value=value, raw_value=raw)

        model.choose = choose
        return model

    def stream(self, horizon=32, reference=False, max_steps=2000, native=False):
        model = self.native_model() if native else ScriptModel(self)
        MODELS.append(model)
        stream = (single.TDStream(model, lambda episode: 133000+episode, max_steps=max_steps)
            if reference else core.MultiStepTDStream(model, lambda episode: 133000+episode,
                horizon=horizon, max_steps=max_steps))
        STREAMS.append(stream)
        return stream


def flattened(rows, field):
    return [value for row in rows for value in row[field]]


def test_zero_budget_does_not_choose_sample_or_resolve_a_queue(monkeypatch):
    stream = Scenario(monkeypatch).stream()
    assert stream.advance(0) == stream.advance_to(0) == []
    assert not stream.environment_counts and not stream.model.counts and not stream.target_counts
    assert stream.queue_state() == [] and stream.rng is None


def test_fixed_32_step_tail_uses_one_preupdate_choice_and_excludes_own_reward(monkeypatch):
    stream = Scenario(monkeypatch, limit=40).stream()
    first, = stream.advance(32)
    assert first['update_records'] == []
    assert len(stream.queue) == 32 and stream.model.updates == 0
    following, = stream.advance(1)
    record, = following['update_records']
    assert record['start_step'] == 0 and record['end_step'] == 32
    assert record['phase'] == 'PRE_ACTION' and record['type'] == 'BOOTSTRAP'
    assert record['reward_score'] == sum(first['scores'][1:])
    assert record['tail'] == following['chosen_values'][0]
    assert record['target'] == sum(first['scores'][1:])/2048.+following['chosen_values'][0]
    assert record['raw_target'] == record['target']-stream.model.offset
    assert [event[0] for event in stream.model.events[-2:]] == ['choose', 'update']
    assert stream.model.counts['choose_calls'] == 33
    assert len(stream.queue) == 32 and stream.queue[0]['step'] == 1


@pytest.mark.parametrize('ending,expected_sources', [('WON', [0, 1, 2]), ('LOST', [0, 1, 2, 3])])
def test_short_terminal_episode_fits_all_actual_suffixes_oldest_first(monkeypatch, ending, expected_sources):
    stream = Scenario(monkeypatch, limit=4, ending=ending).stream()
    row, = stream.advance(4)
    assert row['status'] == ending and row['queue_after'] == []
    assert [entry['start_step'] for entry in row['update_records']] == expected_sources
    assert stream.model.updates == len(expected_sources)
    for record in row['update_records']:
        suffix_score = sum(row['scores'][record['start_step']+1:])
        tail = 8. if ending == 'WON' else -8.
        assert record['reward_score'] == suffix_score
        assert record['target'] == suffix_score/2048.+tail
        assert record['phase'] == 'POST_TERMINAL'
        assert record['type'] == ('WIN_BOUNDARY' if ending == 'WON' else 'LOSS')
    assert stream.model.counts['choose_calls'] == 4


@pytest.mark.parametrize('ending', ['LOST', 'WON'])
def test_mature_fit_precedes_terminal_flush_without_replacement_or_duplicate(monkeypatch, ending):
    stream = Scenario(monkeypatch, limit=3, ending=ending).stream(horizon=2)
    row, = stream.advance(3)
    first, *terminal = row['update_records']
    assert first['start_step'] == 0 and first['end_step'] == 2
    assert first['phase'] == 'PRE_ACTION'
    assert first['tail'] == row['chosen_values'][2]
    assert first['reward_score'] == row['scores'][1]
    assert first['target'] == row['scores'][1]/2048.+row['chosen_values'][2]
    assert first['type'] == ('WIN_BOUNDARY' if ending == 'WON' else 'BOOTSTRAP')
    assert [item['start_step'] for item in terminal] == ([1] if ending == 'WON' else [1, 2])
    assert all(item['phase'] == 'POST_TERMINAL' for item in terminal)


def test_pause_resume_retains_full_queue_rng_and_exact_learning_history(monkeypatch):
    scenario = Scenario(monkeypatch, limit=9)
    full, split = scenario.stream(horizon=4), scenario.stream(horizon=4)
    whole = full.advance_to(23)
    first = split.advance_to(3)
    before = (split.queue_state(), split.rng.getstate(), split.model.weights.copy(), split.model.updates)
    split.model.choose(split.board)
    assert split.queue_state() == before[0] and split.rng.getstate() == before[1]
    np.testing.assert_array_equal(split.model.weights, before[2])
    assert split.model.updates == before[3]
    pieces = first+split.advance_to(7)+split.advance_to(12)+split.advance_to(23)
    for field in ('actions', 'scores', 'spawned_cells', 'spawned_ranks', 'chosen_values',
                  'chosen_raw_values', 'update_records'):
        assert flattened(pieces, field) == flattened(whole, field)
    np.testing.assert_array_equal(split.model.weights, full.model.weights)
    assert split.rng.getstate() == full.rng.getstate()
    assert split.queue_state() == full.queue_state()
    assert split.environment_counts == full.environment_counts
    assert split.target_counts == full.target_counts
    assert split.training_counts == full.training_counts
    assert first[0]['queue_after'] == pieces[1]['queue_before']
    assert len(first[0]['queue_after']) == 3
    assert 'initial_spawns' not in pieces[1]


def test_true_cutoff_discards_whole_unresolved_queue_and_counts_censoring(monkeypatch):
    stream = Scenario(monkeypatch, limit=9).stream(max_steps=3)
    row, = stream.advance(3)
    assert row['status'] == 'CUTOFF' and row['budget_status'] == 'EPISODE_END'
    assert row['censored_updates'] == 3 and row['queue_after'] == []
    assert stream.model.updates == 0 and stream.target_counts['censored_updates'] == 3
    next_row, = stream.advance(1)
    assert next_row['episode'] == 1 and next_row['queue_before'] == []
    assert next_row['update_records'] == [] and len(next_row['queue_after']) == 1


@pytest.mark.parametrize('native', [False, True])
@pytest.mark.parametrize('ending,max_steps', [('LOST', 2000), ('WON', 2000), ('ACTIVE', 3)])
def test_horizon_one_exactly_matches_original_stream_traces_updates_and_native_weights(
        monkeypatch, native, ending, max_steps):
    scenario = Scenario(monkeypatch, limit=3 if ending != 'ACTIVE' else 9,
        ending=ending, goal=4 if native else 1000)
    reference = scenario.stream(reference=True, max_steps=max_steps, native=native)
    actual = scenario.stream(horizon=1, max_steps=max_steps, native=native)
    expected_rows = reference.advance_to(2)+reference.advance_to(5)+reference.advance_to(8)
    actual_rows = actual.advance_to(2)+actual.advance_to(5)+actual.advance_to(8)
    for left, right in zip(actual_rows, expected_rows):
        for field in ('episode', 'seed', 'start_step', 'end_step', 'start_board', 'end_board',
                      'actions', 'scores', 'spawned_cells', 'spawned_ranks', 'chosen_values',
                      'chosen_raw_values', 'updates_before', 'updates_after', 'status', 'return_score'):
            assert left[field] == right[field]
        expected_updates = [dict(target=target, raw_target=raw, error=error)
            for target, raw, error in zip(right['td_targets'], right['raw_td_targets'], right['td_errors'])
            if target is not None]
        if right['terminal_update'] is not None:
            expected_updates.append({key: right['terminal_update'][key]
                for key in ('target', 'raw_target', 'error')})
        assert [{key: record[key] for key in ('target', 'raw_target', 'error')}
            for record in left['update_records']] == expected_updates
        assert (left['queue_after'][0]['afterstate'] if left['queue_after'] else None) == right['pending_after']
        assert bool(left['censored_updates']) == right['censored_last_update']
    np.testing.assert_array_equal(actual.model.weights, reference.model.weights)
    assert actual.model.updates == reference.model.updates
    assert actual.environment_counts == reference.environment_counts
    assert actual.training_counts == reference.training_counts
    assert actual.rng.getstate() == reference.rng.getstate()
