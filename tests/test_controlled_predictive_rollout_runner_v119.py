"""Detect inherited outer-data leakage, changed planner wiring and seed reuse."""
from collections import Counter
from copy import deepcopy
import json
from types import SimpleNamespace
import sys
import pytest

from scripts import run_controlled_predictive_rollout_consequences_v119 as runner


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = runner.ROOT / 'reports/controlled_predictive_rollout_runner_v119.checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed - before,
        environment_samples=0, model_samples=0, fits=0,
        scope='synthetic source extraction, mocked actor wiring and retained seed arithmetic'))
    path.write_text(json.dumps(value, indent=2) + '\n')


def test_capsule_excludes_outer_and_charges_source_selection(monkeypatch):
    template = SimpleNamespace(fit_counts=dict(observations=7))
    monkeypatch.setattr(runner, 'LearnedDynamics', SimpleNamespace(from_payload=lambda _: template))
    class Router:
        module_id = 2
        def to_rule(self, base):
            assert base is template
            return SimpleNamespace(to_payload=lambda: dict(inferred_p4=.13))
    monkeypatch.setattr(runner, 'SpawnMemory', SimpleNamespace(from_payload=lambda _: Router()))
    source, previous = dict(supplied_dynamics={}, lifecycles=[]), dict(status='complete', lifecycles=[])
    for life in range(4):
        old, new = [], []
        for phase in ('A', 'B', 'A_RETURN'):
            old.append(dict(name=phase, source_games=[dict(environment_counts=dict(sampled_transitions=5))],
                checkpoint=dict(router_payload={}, fit_logs={'SHARED': dict(counts=dict(tree_fits=3))})))
            new.append(dict(name=phase, checkpoint=dict(
                models={'UTILITY_SELECTED': dict(stamp=life)}, utility_selected_origin=dict(batch=1),
                selection=dict(selected_candidate='KEEP'),
                source_validation_games=[dict(result=dict(environment_counts=dict(sampled_transitions=2)))],
                control_evaluations='DO_NOT_COPY', predictive_tests='DO_NOT_COPY')))
        source['lifecycles'].append(dict(life=life, phases=old))
        previous['lifecycles'].append(dict(life=life, phases=new))
    before = deepcopy((previous, source))
    capsule = runner.extract_source(previous, source)
    assert (previous, source) == before and 'DO_NOT_COPY' not in json.dumps(capsule)
    assert capsule['inherited_costs']['source_environment']['sampled_transitions'] == 60
    assert capsule['inherited_costs']['utility_validation_environment']['sampled_transitions'] == 24
    assert capsule['inherited_costs']['tree_fitting']['tree_fits'] == 36
    assert [row['model']['stamp'] for row in capsule['snapshots']] == list(range(4))
    assert all(row['rule'] == dict(inferred_p4=.13) for row in capsule['snapshots'])


def test_four_actors_use_unchanged_planner_and_separate_environment(monkeypatch, tmp_path):
    rule, calls = object(), []
    monkeypatch.setattr(runner, 'LearnedDynamics', SimpleNamespace(from_payload=lambda _: rule))
    class Model:
        def __init__(self, *args):
            self.args, self.counts = args, Counter()
        def can_route(self, module_id):
            return module_id == 2
    monkeypatch.setattr(runner, 'bound_model', lambda payload, module_id: Model(payload, module_id))
    monkeypatch.setitem(sys.modules, 'acfqp.science.controlled_predictive_rollout_consequences_v119',
        SimpleNamespace(RolloutKnowledge=Model))
    def choose(board, query, knowledge, actual_rule, rng, depth, work):
        assert actual_rule is rule and depth == 2
        calls.append(knowledge)
        return dict(action='LEFT', value=0., metrics={}, policy=None, branches=[], action_values={})
    monkeypatch.setattr(runner.planner, 'choose', choose)
    def episode(seed, act, p4, max_steps):
        assert p4 == .1 and max_steps == 2000 and act((1,) * 16, 0) == 'LEFT'
        return dict(return_score=100, status='LOST', steps_count=1,
            work=dict(sampled_transitions=1), seconds=0., steps=[])
    monkeypatch.setattr(runner, 'run_episode', episode)
    source = dict(life=1, rule={}, model=dict(stamp='frozen'), module_id=2)
    rows = [runner.control_game(source, method, 'risk_goal', 1, tmp_path)[0] for method in runner.METHODS]
    assert calls[0] is None and calls[1].args == (source['model'], 2)
    assert calls[2].args[:3] == (rule, 4, rows[2]['seed'] + runner.ROLLOUT_OFFSET)
    assert calls[3].args[:3] == (rule, 16, rows[3]['seed'] + runner.ROLLOUT_OFFSET)
    assert len({row['seed'] for row in rows}) == 1
    assert all(row['result']['utility'] == 100 / 2048 - 4 for row in rows)
    assert all(row['result']['source_unchanged'] for row in rows)


def test_new_streams_are_distinct_from_retained_experiments():
    new_env = {runner.BASE + 3_000_000 + life * 100000 + replica for life in range(4) for replica in range(2)}
    new_planner = {seed + runner.PLANNER_OFFSET for seed in new_env}
    new_rollout = {seed + runner.ROLLOUT_OFFSET + call * 10**12
        for seed in new_env for call in range(runner.MAX_STEPS)}
    old = set()
    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get('seed'), int):
                old.add(value['seed'])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for name in ('regime_memory_v115', 'context_consequences_v116',
                 'consolidation_v117', 'utility_consolidation_v118'):
        path = runner.ROOT / ('reports/controlled_predictive_' + name) / 'run.json'
        walk(json.loads(path.read_text()))
    old_all = old | {seed + offset for seed in old for offset in (1_000_000, 50_000_000)}
    assert len(new_env) == len(new_planner) == 8 and len(new_rollout) == 16000
    assert not (new_env & new_planner or new_env & new_rollout or new_planner & new_rollout)
    assert not (new_env | new_planner | new_rollout) & old_all
