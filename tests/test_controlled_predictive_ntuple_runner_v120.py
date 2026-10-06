"""Check causal TD timing, censoring, source separation and paired evaluation."""
from collections import Counter
from copy import deepcopy
import json
import sys
from types import SimpleNamespace
import pytest

from scripts import run_controlled_predictive_ntuple_learning_v120 as runner


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = runner.ROOT / 'reports/controlled_predictive_ntuple_runner_v120.checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed - before,
        environment_samples=0, model_samples=0, fits=0,
        scope='synthetic TD histories, mocked actors and retained seed arithmetic'))
    path.write_text(json.dumps(value, indent=2) + '\n')


class FakeValue:
    def __init__(self, terminal=False):
        self.counts, self.updates, self.events = Counter(), 0, []
        self.rule, self.terminal = SimpleNamespace(goal_rank=11), terminal

    def choose(self, board, query):
        index = board[0]
        self.events.append(('choose', index, self.updates))
        self.counts['choice_calls'] += 1
        afterstate = [index] + [0] * 15
        if index == 3 and self.terminal:
            afterstate[0] = 11
        # The update count makes evaluating after the pending update observable.
        return dict(action='LEFT', afterstate=afterstate,
            value=float(index * 10 + self.updates + (4 if index == 3 and self.terminal else 0)))

    def update(self, board, target, alpha):
        self.events.append(('update', board[0], target, alpha))
        self.updates += 1
        self.counts['td_updates'] += 1


def fake_episode(status):
    def run(seed, action, p4, max_steps):
        assert p4 == .1 and max_steps == 2000
        steps = []
        for index in (1, 2, 3):
            assert action((index,) + (0,) * 15, index - 1) == 'LEFT'
            steps.append(dict(action='LEFT', spawned_cell=index, spawned_rank=1, score=4 * index))
        return dict(initial_board=[1, 1] + [0] * 14,
            initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
            final_board=[11 if status == 'WON' else 3] + [0] * 15,
            return_score=24, status=status, steps_count=3, steps=steps,
            work=dict(sampled_transitions=3), seconds=0.)
    return run


@pytest.mark.parametrize('status', ['LOST', 'WON', 'CUTOFF'])
def test_td_uses_next_decision_before_pending_update_and_handles_terminal(monkeypatch, status):
    monkeypatch.setattr(runner, 'run_episode', fake_episode(status))
    model = FakeValue(terminal=status == 'WON')
    row, raw = runner.td_game(model, 2, 'risk_goal', episode=7)
    assert model.events[:5] == [('choose', 1, 0), ('choose', 2, 0),
        ('update', 1, 20., .0025), ('choose', 3, 1),
        ('update', 2, 35. if status == 'WON' else 31., .0025)]
    assert model.updates == (3 if status == 'LOST' else 2)
    if status == 'LOST':
        assert model.events[-1] == ('update', 3, -4., .0025)
    assert row['terminal_update'] == (status == 'LOST')
    assert row['censored_last_update'] == (status == 'CUTOFF')
    assert row['analytic_terminal'] == (status == 'WON')
    assert row['result']['utility'] == 24 / 2048 + (4 if status == 'WON' else -4 if status == 'LOST' else 0)
    assert row['seed'] == runner.train_seed(2, 'risk_goal', 7)
    assert raw['actions'] == ['LEFT'] * 3 and raw['scores'] == [4, 8, 12]


def test_evaluation_never_updates_and_reuses_only_frozen_seeds(monkeypatch):
    monkeypatch.setattr(runner, 'run_episode', fake_episode('LOST'))
    model = FakeValue()
    rows = [runner.td_game(model, 1, query, checkpoint=checkpoint, replica=2)[0]
        for query in runner.QUERIES for checkpoint in runner.CHECKPOINTS]
    assert model.updates == 0 and all(event[0] == 'choose' for event in model.events)
    assert len({row['seed'] for row in rows}) == 1
    assert all(row['result']['updates_before'] == row['result']['updates_after'] == 0 for row in rows)


def test_source_capsule_excludes_values_selection_and_old_outer():
    keys = ('supplied_dynamics_fit_counts', 'source_environment', 'source_planning',
        'source_seconds', 'source_router')
    previous = dict(snapshots=[dict(life=life, rule=dict(program='source_only'),
        model='NO_COPY', selected_origin='NO_COPY', outer_games='NO_COPY') for life in range(4)],
        inherited_costs={key: dict(work=7) for key in keys})
    previous['inherited_costs'].update(tree_fitting='NO_COPY', utility_validation_environment='NO_COPY')
    before = deepcopy(previous)
    result = runner.extract_source(previous)
    assert before == previous and 'NO_COPY' not in json.dumps(result)
    assert all(set(row) == {'life', 'rule'} for row in result['snapshots'])
    assert set(result['inherited_costs']) == set(keys) | {'scope'}


def test_references_preserve_planner_and_rollout_contract(monkeypatch, tmp_path):
    rule, calls = object(), []
    monkeypatch.setattr(runner, 'LearnedDynamics', SimpleNamespace(from_payload=lambda _: rule))
    class Rollout:
        def __init__(self, *args):
            self.args, self.counts = args, Counter()
    monkeypatch.setitem(sys.modules, 'acfqp.science.controlled_predictive_rollout_consequences_v119',
        SimpleNamespace(RolloutKnowledge=Rollout))
    def choose(board, query, knowledge, actual_rule, rng, depth, work):
        assert actual_rule is rule and depth == 2
        calls.append(knowledge)
        return dict(action='LEFT')
    monkeypatch.setattr(runner.planner, 'choose', choose)
    monkeypatch.setattr(runner, 'run_episode', fake_episode('LOST'))
    source = dict(life=1, rule={})
    rows = [runner.reference_game(source, method, 'risk_goal', 2, tmp_path)[0]
        for method in ('H2_ONLY', 'MC4')]
    assert calls[:3] == [None] * 3
    assert calls[3].args == (rule, 4, rows[1]['seed'] + runner.ROLLOUT_OFFSET, tmp_path)
    assert len({row['seed'] for row in rows}) == 1
    assert all(row['seed'] == runner.evaluation_seed(1, 2) for row in rows)


def test_new_streams_distinct_from_training_outer_and_retained_versions():
    train = {runner.train_seed(life, query, episode) for life in runner.LIVES
        for query in runner.QUERIES for episode in range(runner.TRAIN_EPISODES)}
    outer = {runner.evaluation_seed(life, replica) for life in runner.LIVES
        for replica in range(runner.REPLICAS)}
    planning = {seed + runner.PLANNER_OFFSET for seed in outer}
    rollouts = {seed + runner.ROLLOUT_OFFSET + call * 10**12
        for seed in outer for call in range(runner.MAX_STEPS)}
    assert len(train) == 32768 and len(outer) == len(planning) == 32 and len(rollouts) == 64000
    assert len(train | outer | planning | rollouts) == sum(map(len, (train, outer, planning, rollouts)))
    old = set()
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith('seed') and isinstance(child, int):
                    old.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for name in ('regime_memory_v115', 'context_consequences_v116', 'consolidation_v117',
            'utility_consolidation_v118', 'rollout_consequences_v119'):
        walk(json.loads((runner.ROOT / ('reports/controlled_predictive_' + name) / 'run.json').read_text()))
    old |= {seed + offset for seed in tuple(old) for offset in (1_000_000, 50_000_000, 60_000_000)}
    assert not (train | outer | planning | rollouts) & old
