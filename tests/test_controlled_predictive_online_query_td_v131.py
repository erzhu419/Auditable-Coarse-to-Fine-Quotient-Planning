"""Finite native-table and scripted stream checks; no natural-game sampling."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import controlled_predictive_online_query_td_v131 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import ALPHA, NtupleValue
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_online_query_td_v131_build'
BOARD = [1, 1, 0, 0]+[0]*12
OTHER = [2, 0, 1, 0]+[0]*12
LOST = [1, 2, 1, 2, 2, 1, 2, 1]*2
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
TARGET = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
SOURCES, MODELS, STREAMS, REFERENCES = [], [], [], []


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_online_query_td_v131.core_checks.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        core_work=dict(sum((model.counts for model in MODELS), Counter())),
        source_work=dict(sum((model.counts for model in SOURCES), Counter())),
        reference_work=dict(sum((model.counts for model in REFERENCES), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in SOURCES+MODELS+REFERENCES), Counter())),
        scripted_environment_work=dict(sum((stream.environment_counts for stream in STREAMS), Counter())),
        newly_sampled_environment_transitions=0,
        scope='Static synthetic boards and scripted environment only; no natural-game samples.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def parent(source_query=SOURCE, target_query=TARGET):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    source.updates = 42
    SOURCES.append(source)
    return QueryParent(source, source_query, target_query, .4)


def model(kind='PRIOR', **kwargs):
    result = core.QueryTD(parent(**kwargs), kind, BUILD)
    MODELS.append(result)
    return result


def assert_choices(actual, expected):
    assert (actual['action'], actual['value'], actual['status']) == (
        expected['action'], expected['value'], expected['status'])
    assert actual['action_values'].keys() == expected['action_values'].keys()
    for action, row in actual['action_values'].items():
        for field in ('value', 'score', 'afterstate'):
            assert row[field] == expected['action_values'][action][field]


def test_zero_prior_exactly_preserves_parent_for_ordinary_goal_loss_and_ties():
    for source_query in (SOURCE, TARGET):
        result = model(source_query=source_query)
        for board in (BOARD, OTHER, [3, 3]+[0]*14, [4]+[0]*15, LOST):
            assert_choices(result.choose(board), result.parent.choose(board))
        assert result.updates == 0
        assert result.parent.updates == 42
        assert not np.shares_memory(result.weights, result.parent.source.weights)


def test_prior_preserves_two_addition_rounding_and_resulting_lexical_tie(monkeypatch):
    result = model()
    rows = {name: dict(afterstate=BOARD, score=0, tail_value=value, value=value)
        for name, value in (('UP', .1), ('DOWN', np.nextafter(.1, -np.inf)))}
    def raw_choose(board, query):
        return dict(action='UP', **rows['UP'], action_values=rows, status='ACTIVE')
    monkeypatch.setattr(result.model, 'choose', raw_choose)
    monkeypatch.setattr(result.parent.source, 'choose', raw_choose)
    expected = result.parent.choose(BOARD)
    actual = result.choose(BOARD)
    assert_choices(actual, expected)
    assert actual['action'] == 'DOWN'
    assert (.1+result.failure_shift+result.success_shift) != .1+result.offset


def test_offset_is_subtracted_once_and_v120_multiplicity_update_is_unchanged():
    result = model()
    reference = NtupleValue(result.rule, BUILD)
    REFERENCES.append(reference)
    reference.weights[:] = result.weights
    target = 1.7
    expected = reference.update(BOARD, target-result.offset, ALPHA)
    update = result.update(BOARD, target)
    assert update['target'] == target
    assert update['raw_target'] == target-result.offset
    assert update['error'] == expected
    np.testing.assert_array_equal(result.weights, reference.weights)
    assert result.counts['inner_table_update_occurrences'] == 32
    assert result.counts['inner_table_updates'] < 32


def test_scratch_has_no_source_prior_or_offset_and_goal_tail_is_analytic():
    result = model(kind='SCRATCH')
    before = result.parent.source.counts.copy()
    assert result.offset == 0.
    assert not np.any(result.weights)
    for board in (BOARD, OTHER, [3, 3]+[0]*14):
        for row in result.choose(board)['action_values'].values():
            goal = max(row['afterstate']) >= 4
            assert row['value'] == row['score']/2048.+(TARGET['goal_bonus'] if goal else 0.)
            assert row['raw_tail_value'] == 0.
            assert row['offset'] == 0.
    result.update(BOARD, .8)
    assert result.parent.source.counts == before


def test_update_cannot_modify_source_or_a_frozen_model():
    result = model()
    source_weights, source_counts = result.parent.source.weights.copy(), result.parent.source.counts.copy()
    result.update(BOARD, 1.2)
    result.choose(BOARD)
    np.testing.assert_array_equal(result.parent.source.weights, source_weights)
    assert result.parent.source.counts == source_counts
    assert result.parent.updates == 42
    result.freeze()
    before = result.weights.copy()
    with pytest.raises(RuntimeError, match='frozen'):
        result.update(BOARD, 1.4)
    np.testing.assert_array_equal(result.weights, before)
    assert result.updates == 1


def test_sparse_checkpoint_replays_target_offset_weights_and_frozen_state(tmp_path):
    result = model()
    result.update(BOARD, .7)
    result.freeze()
    saved = result.save(tmp_path/'query.npz')
    metadata = json.loads(Path(saved['sidecar']).read_text())
    assert metadata['source_updates'] == 42
    assert metadata['updates'] == 1
    assert metadata['offset'] == result.offset
    restored = core.QueryTD.load(saved['path'], result.parent, BUILD)
    MODELS.append(restored)
    np.testing.assert_array_equal(result.weights, restored.weights)
    assert not restored.weights.flags.writeable
    assert restored.updates == result.updates
    for board in (BOARD, OTHER, [3, 3]+[0]*14, LOST):
        assert_choices(restored.choose(board), result.choose(board))


class ScriptModel:
    """A tiny changing predictor that exposes action-selection/update order."""
    def __init__(self, scenario):
        self.scenario = scenario
        self.rule = SimpleNamespace(goal_rank=100)
        self.target_query = TARGET
        self.counts, self.updates = Counter(), 0
        self.weights = np.array([.4])
        self.offset, self.events = .3, []

    def choose(self, board):
        self.events.append(('choose', board[0], float(self.weights[0])))
        self.counts['choose_calls'] += 1
        action = 'RIGHT' if self.weights[0] > .3 else 'DOWN'
        afterstate, score, _ = self.scenario.swipe(board, SimpleNamespace(value=action))
        value = float(self.weights[0]+board[0]*.2+score/2048.)
        return dict(action=action, afterstate=afterstate, value=value, raw_value=value-self.offset)

    def update(self, afterstate, target):
        self.events.append(('update', afterstate[0], float(self.weights[0]), target))
        error = target-self.offset-float(self.weights[0])
        self.weights[0] += .05*error
        self.updates += 1
        self.counts['td_updates'] += 1
        return dict(target=target, raw_target=target-self.offset, error=error, work=dict(td_updates=1))


class Scenario:
    def __init__(self, monkeypatch, limit=3, ending='LOST'):
        self.limit, self.ending = limit, ending
        monkeypatch.setattr(core, '_spawn', self.spawn)
        monkeypatch.setattr(core, '_status', self.status)
        monkeypatch.setattr(core.ground, 'swipe_board_v1', self.swipe)

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
            board[1] = 100
        return tuple(board), 4*board[0]+8*int(action.value == 'RIGHT'), True

    def status(self, board, work):
        work['ground_state_status_calls'] += 1
        return self.ending if board[0] == self.limit else 'ACTIVE'

    def stream(self, max_steps=2000):
        stream = core.TDStream(ScriptModel(self), lambda episode: 131000+episode, max_steps=max_steps)
        STREAMS.append(stream)
        return stream


def test_stream_constructor_and_zero_budget_do_not_sample(monkeypatch):
    stream = Scenario(monkeypatch).stream()
    assert stream.advance(0) == stream.advance_to(0) == []
    assert not stream.environment_counts
    assert not stream.model.counts
    assert stream.board is stream.pending is stream.rng is None
    assert stream.transitions == stream.episodes_started == 0


def test_stream_chooses_next_action_before_updating_previous_afterstate(monkeypatch):
    stream = Scenario(monkeypatch).stream()
    row, = stream.advance(2)
    assert [event[0] for event in stream.model.events] == ['choose', 'choose', 'update']
    assert stream.model.events[1][2] == stream.model.events[0][2] == .4
    assert row['td_targets'] == [None, row['chosen_values'][1]]
    assert row['raw_td_targets'][1] == row['chosen_values'][1]-stream.model.offset
    assert row['terminal_update'] is None
    assert row['pending_after'] == list(stream.pending)
    assert row['status'] == 'ACTIVE' and row['budget_status'] == 'BUDGET_END'


def test_pause_resume_matches_uninterrupted_actions_rng_and_weights(monkeypatch):
    scenario = Scenario(monkeypatch)
    full, split = scenario.stream(), scenario.stream()
    whole = full.advance_to(8)
    first = split.advance_to(2)
    pending = split.pending
    rng_state, weights = split.rng.getstate(), split.model.weights.copy()
    # Checkpoint evaluation makes predictions only; it cannot resolve pending TD.
    split.model.choose(split.board)
    assert split.pending == pending and split.rng.getstate() == rng_state
    np.testing.assert_array_equal(split.model.weights, weights)
    pieces = first+split.advance_to(4)+split.advance_to(8)
    for name in ('actions', 'scores', 'spawned_cells', 'spawned_ranks', 'chosen_values',
                 'chosen_raw_values', 'td_targets', 'raw_td_targets', 'td_errors'):
        assert [item for row in pieces for item in row[name]] == [item for row in whole for item in row[name]]
    np.testing.assert_array_equal(split.model.weights, full.model.weights)
    assert split.rng.getstate() == full.rng.getstate()
    assert split.pending == full.pending
    assert split.environment_counts == full.environment_counts
    assert split.training_counts == full.training_counts
    assert split.transitions == full.transitions == 8
    assert split.model.updates == full.model.updates == 7
    assert split.episodes_started == full.episodes_started == 3
    assert split.episodes_completed == full.episodes_completed == 2
    assert 'initial_spawns' not in pieces[1]
    assert pieces[0]['pending_after'] == pieces[1]['pending_before']
    assert pieces[0]['end_board'] == pieces[1]['start_board']


@pytest.mark.parametrize('ending,limit,max_steps,updates,status', [
    ('LOST', 3, 2000, 3, 'LOST'), ('WON', 3, 2000, 2, 'WON'),
    ('ACTIVE', 9, 3, 2, 'CUTOFF')])
def test_goal_loss_and_actual_cutoff_have_distinct_update_accounting(
        monkeypatch, ending, limit, max_steps, updates, status):
    stream = Scenario(monkeypatch, limit, ending).stream(max_steps)
    row, = stream.advance(3)
    assert row['status'] == status
    assert row['budget_status'] == 'EPISODE_END'
    assert stream.model.updates == updates
    assert stream.pending is None
    assert stream.episodes_completed == 1
    assert row['environment_counts']['sampled_transitions'] == 3
    assert row['environment_counts']['environment_random_draws'] == 2*3+4
    if ending == 'LOST':
        assert row['terminal_update']['target'] == -TARGET['failure_penalty']
        assert row['terminal_update']['raw_target'] == -TARGET['failure_penalty']-stream.model.offset
        assert row['terminal_update']['afterstate'][0] == 3
    else:
        assert row['terminal_update'] is None
    assert row['censored_last_update'] == (status == 'CUTOFF')
    next_row, = stream.advance(1)
    assert next_row['episode'] == 1 and next_row['start_step'] == 0
    assert next_row['td_targets'] == [None]
    assert next_row['pending_before'] is None
