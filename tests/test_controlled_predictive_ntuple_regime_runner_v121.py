"""Detect TD leakage, unequal budgets, forgotten weights and charged source counters."""
from collections import Counter
from copy import deepcopy
import gzip
import io
import json
from types import SimpleNamespace
import pytest

from scripts import run_controlled_predictive_ntuple_regime_v121 as runner


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = runner.ROOT / 'reports/controlled_predictive_ntuple_regime_runner_v121.checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed - before,
        environment_samples=0, model_samples=0, fits=0,
        scope='mocked trajectories, synthetic TD updates, lifecycle aliases and seed arithmetic'))
    path.write_text(json.dumps(value, indent=2) + '\n')


class FakeValue:
    def __init__(self, rule=None, build_dir=None, updates=0, terminal=False):
        self.rule = rule or SimpleNamespace(goal_rank=11)
        self.counts, self.updates, self.events = Counter(td_updates=updates), updates, []
        self.setup_counts, self.setup_seconds = Counter(allocated_weight_bytes=8), .1
        self.terminal = terminal

    @classmethod
    def load(cls, path, rule, build_dir):
        model = cls(rule, build_dir, updates=100)
        model.counts.update(checkpoint_loads=1, checkpoint_loaded_parameters=1)
        model.last_load_seconds = .3
        return model

    def choose(self, board, query):
        assert set(query) == {'reward_weight', 'failure_penalty', 'goal_bonus'}
        index = board[0]
        self.events.append(('choose', index, self.updates))
        self.counts['choose_calls'] += 1
        afterstate = [11 if self.terminal and index == 3 else index] + [0] * 15
        return dict(action='LEFT', afterstate=afterstate, value=index * 10 + self.updates)

    def update(self, board, target, alpha):
        self.events.append(('update', board[0], target, alpha))
        self.updates += 1; self.counts['td_updates'] += 1
        self.counts['table_update_occurrences'] += 32

    def save(self, path):
        path.write_text(str(self.updates)); self.counts['checkpoint_saves'] += 1
        return dict(updates=self.updates)


def fake_episode(status='LOST', calls=None):
    def run(seed, action, p4, max_steps):
        if calls is not None:
            calls.append((seed, p4, max_steps))
        steps = []
        for index in range(1, min(3, max_steps) + 1):
            assert action([index] + [0] * 15, index - 1) == 'LEFT'
            steps.append(dict(action='LEFT', spawned_cell=index, spawned_rank=1, score=4 * index))
        actual_status = 'CUTOFF' if max_steps < 3 else status
        return dict(initial_board=[1, 1] + [0] * 14,
            initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
            final_board=[11 if actual_status == 'WON' else 3] + [0] * 15,
            return_score=sum(step['score'] for step in steps), status=actual_status,
            steps_count=len(steps), steps=steps,
            work=dict(sampled_transitions=len(steps), initial_spawns=2), seconds=0.)
    return run


@pytest.mark.parametrize('status', ['LOST', 'WON', 'CUTOFF'])
def test_causal_td_timing_terminal_targets_and_pending_scope(monkeypatch, status):
    monkeypatch.setattr(runner, 'run_episode', fake_episode(status))
    model = FakeValue(updates=100, terminal=status == 'WON')
    row, _ = runner.td_game(model, 2, 'risk_goal', 'B', 'CONT', episode=4)
    assert model.events[:5] == [('choose', 1, 100), ('choose', 2, 100),
        ('update', 1, 120, .0025), ('choose', 3, 101), ('update', 2, 131, .0025)]
    count = 3 if status == 'LOST' else 2
    assert row['result']['learning_counts']['td_updates'] == count
    assert model.updates == 100 + count
    assert row['terminal_update'] == (status == 'LOST')
    if status == 'LOST':
        assert model.events[-1] == ('update', 3, -4., .0025)
    model.events.clear()
    runner.td_game(model, 2, 'risk_goal', 'A_RETURN', 'CONT', episode=0)
    assert [event[0] for event in model.events[:3]] == ['choose', 'choose', 'update']


def test_evaluation_isolated_and_explicit_reuse_has_no_physical_cost(monkeypatch):
    calls = []
    monkeypatch.setattr(runner, 'run_episode', fake_episode(calls=calls))
    monkeypatch.setattr(runner, 'REPLICAS', 2)
    model, stream = FakeValue(updates=100), io.StringIO()
    rows = runner.evaluate(model, 0, 'reward', 'B', 'FROZEN_A', 0, stream)
    saved = stream.getvalue()
    alias = runner.evaluate(model, 0, 'reward', 'B', 'CONT', 0, stream, rows)
    assert len(calls) == 2 and stream.getvalue() == saved and model.updates == 100
    assert [row['reused_from'] for row in alias] == [row['eval_id'] for row in rows]
    assert [row['result'] for row in alias] == [row['result'] for row in rows]
    assert all(row['result']['updates_before'] == row['result']['updates_after'] for row in rows)
    assert all(p4 == .5 for _, p4, _ in calls)


def test_exact_phase_budget_and_first_crossing_checkpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'run_episode', fake_episode())
    monkeypatch.setattr(runner, 'TRAIN_TRANSITIONS', 8)
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 4, 8))
    monkeypatch.setattr(runner, 'REPLICAS', 1)
    model = FakeValue()
    result = dict(training_blocks=[], checkpoints=[dict(model_ref='implicit_zero')])
    train, control = io.StringIO(), io.StringIO()
    runner.train_phase(model, 0, 'reward', 'B', 'RESET', result,
        tmp_path, tmp_path, train, control, lambda: None)
    rows = [json.loads(line) for line in train.getvalue().splitlines()]
    assert [row['max_steps'] for row in rows] == [8, 5, 2]
    assert [row['transitions_after'] for row in rows] == [3, 6, 8]
    assert rows[-1]['result']['status'] == 'CUTOFF'
    assert [cp['transitions'] for cp in result['checkpoints'][1:]] == [6, 8]
    assert result['final_transitions'] == 8 and result['final_updates'] == 7
    assert sum(block['environment_counts']['sampled_transitions']
        for block in result['training_blocks']) == 8


def test_lifecycle_continuity_reset_and_physical_evaluation_roster(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'NtupleValue', FakeValue)
    monkeypatch.setattr(runner, 'LearnedDynamics',
        SimpleNamespace(from_payload=lambda _: SimpleNamespace(goal_rank=11)))
    monkeypatch.setattr(runner, 'run_episode', fake_episode())
    monkeypatch.setattr(runner, 'TRAIN_TRANSITIONS', 8)
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 4, 8))
    monkeypatch.setattr(runner, 'REPLICAS', 1)
    monkeypatch.setattr(runner, 'QUERIES', {'reward': runner.QUERIES['reward']})
    source = dict(life=0, rule={}, models=dict(reward=dict(
        path='/retained_v120.npz', updates=100, nonzero_weights=1)))
    result = runner.lifecycle_run(source, tmp_path)['queries']['reward']
    b, a = [result['phases'][phase]['methods'] for phase in ('B', 'A_RETURN')]
    assert b['CONT']['final_updates'] == 107
    assert a['CONT']['checkpoints'][0]['updates'] == 107
    assert a['CONT']['final_updates'] == 114
    assert a['CONT']['checkpoints'][0]['model_ref'] == b['CONT']['checkpoints'][-1]['model_ref']
    assert all(phase['RESET']['checkpoints'][0]['updates'] == 0 for phase in (b, a))
    assert all(phase['FROZEN_A']['checkpoints'][0]['updates'] == 100 for phase in (b, a))
    with gzip.open(tmp_path / result['control_trace'], 'rt') as stream:
        physical = [json.loads(line) for line in stream]
    logical = [row for phase in (b, a) for value in phase.values()
        for cp in value['checkpoints'] for row in cp['evaluations']]
    assert len(physical) == 13 and len(logical) == 14
    assert sum(row['reused_from'] is not None for row in logical) == 1
    assert len(result['model_setup']) == 4


def test_source_load_costs_only_include_fresh_work(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'NtupleValue', FakeValue)
    _, setup = runner.make_model(SimpleNamespace(goal_rank=11), tmp_path, 'CONT', 'B',
        dict(path='/source.npz', updates=100, nonzero_weights=1))
    assert setup['load_counts'] == dict(checkpoint_loads=1, checkpoint_loaded_parameters=1)
    assert setup['load_seconds'] == pytest.approx(.2)
    assert 'td_updates' not in setup['setup_counts']
    snapshots = [dict(life=life, rule={'same': True}) for life in runner.LIVES]
    value = dict(training_blocks=[dict(games=4096)], setup_counts={'bytes': 8},
        setup_seconds=.1, checkpoints=[dict(episodes=4096, model_file='model.npz',
            updates=100, model_metadata=dict(nonzero_weights=1),
            save_counts={'checkpoint_saves': 1}, save_seconds=.2)], references='EXCLUDE')
    previous = dict(inherited_costs={'prior': 1}, lifecycles=[dict(life=life,
        queries={query: deepcopy(value) for query in runner.QUERIES}) for life in runner.LIVES])
    extracted = runner.extract_source(previous, dict(snapshots=snapshots))
    assert 'EXCLUDE' not in json.dumps(extracted)
    assert extracted['inherited_costs']['v120_training'][0]['queries']['reward']['training_blocks'] == [dict(games=4096)]


def test_seed_namespaces_allow_the_full_exact_transition_budget():
    ranges = [(runner.train_seed(life, query, phase, 0),
        runner.train_seed(life, query, phase, runner.TRAIN_TRANSITIONS - 1))
        for life in runner.LIVES for query in runner.QUERIES for phase in runner.PHASES]
    ranges.sort()
    assert all(left[1] < right[0] for left, right in zip(ranges, ranges[1:]))
    outer = {runner.evaluation_seed(life, phase, replica) for life in runner.LIVES
        for phase in runner.PHASES for replica in range(runner.REPLICAS)}
    assert len(outer) == 64 and max(end for _, end in ranges) < min(outer)
    assert min(start for start, _ in ranges) > 121 * 100_000_000
    assert max(outer) < 122 * 100_000_000
