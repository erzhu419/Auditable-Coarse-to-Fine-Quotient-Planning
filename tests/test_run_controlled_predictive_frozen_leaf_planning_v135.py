"""Finite frozen-leaf runner checks; no natural games or native model calls."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_frozen_leaf_planning_v135 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD, AFTER = [1, 1]+[0]*14, [2]+[0]*15


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_frozen_leaf_planning_v135.runner_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, seconds=perf_counter()-started,
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0,
        scope='Mocked frozen leaves, planners and games; source selection, shared objects, costs and ordering'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def source_fixture():
    previous = dict(snapshots=[dict(life=life, rule={'kept': life}, models={}, counts={},
        outcomes='not an input') for life in runner.LIVES], inherited_costs={'old': 1})
    run = dict(status='complete', lifecycles=[dict(life=life, queries={query: dict(learners={
        kind: dict(checkpoints=[dict(age=age,
            model_ref=f'life_{life}/{query}_{kind}_{age}.npz', updates=age-1,
            metadata=dict(parameter_count=10 if kind == 'SINGLE' else 20))
            for age in (0, 32768, 131072, 524288)])
        for kind in ('SINGLE', 'GLOBAL', 'CAPACITY')}) for query in runner.QUERIES})
        for life in runner.LIVES])
    analysis = dict(complete=True, primary_complete=True, costs={'v134': 2}, outcomes=[999])
    return previous, run, analysis


class Model:
    def __init__(self, representation='SINGLE'):
        self.kind, self.offset, self.updates = 'PRIOR', -1., 524000
        self.weights = np.zeros(1)
        if representation != 'SINGLE': self.representation = representation
        self.source = SimpleNamespace(weights=np.zeros(1))
        self.source.weights.flags.writeable = False
        self.counts, self.setup_counts, self.setup_seconds = Counter(), {}, 0.
        self.load_counts, self.last_load_seconds = {'checkpoint_loads': 1}, 0.

    def freeze(self):
        self.weights.flags.writeable = False


def test_source_references_only_final_single_and_capacity_for_all_histories(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'SOURCE', tmp_path/'old')
    previous, run, analysis = source_fixture()
    source = runner.extract_source(previous, run, analysis)
    assert [row['life'] for row in source['snapshots']] == list(runner.LIVES)
    assert source['inherited_costs'] == dict(old=1, v134_experiment={'v134': 2})
    references = []
    for row in source['snapshots']:
        assert set(row) == {'life', 'rule', 'models', 'counts', 'leaves'}
        assert set(row['leaves']) == set(runner.QUERIES)
        for query in row['leaves'].values():
            assert set(query) == {'SINGLE', 'CAPACITY'}
            for kind, ref in query.items():
                assert ref['checkpoint'] == 524288 and ref['updates'] == 524287
                assert ref['parameter_count'] == (10 if kind == 'SINGLE' else 20)
                assert ref['model_ref'].endswith(f'{kind}_524288.npz')
                assert Path(ref['model_ref']).is_relative_to(tmp_path/'old')
                references.append(ref['model_ref'])
    assert len(references) == len(set(references)) == 16
    assert list(tmp_path.iterdir()) == []  # Source extraction records paths; it never copies models.
    source['snapshots'][0]['rule']['kept'] = 999
    assert previous['snapshots'][0]['rule']['kept'] == 0


def test_source_requires_complete_execution_and_primary_analysis():
    previous, run, analysis = source_fixture()
    for field in ('status', 'complete', 'primary_complete'):
        altered_run, altered_analysis = deepcopy(run), deepcopy(analysis)
        if field == 'status': altered_run[field] = 'evaluation'
        else: altered_analysis[field] = False
        with pytest.raises(ValueError, match='V134 must be complete'):
            runner.extract_source(previous, altered_run, altered_analysis)
    assert runner.settings()['physical_control_games'] == 4*2*2*2*16 == 512
    assert runner.settings()['new_training_transitions'] == 0
    seeds = [runner.evaluation_seed(life, replica)
             for life in runner.LIVES for replica in range(runner.REPLICAS)]
    assert len(set(seeds)) == 64 and min(seeds) == 13500000000+90000000
    assert max(seeds) == 13500000000+90000000+300000+15


def test_game_retains_root_alternatives_and_only_new_planner_costs(monkeypatch):
    class Planner:
        counts = Counter(choose_calls=10, enumerated_model_outcomes=90)
        def choose(self, board, query):
            self.counts.update(choose_calls=1, enumerated_model_outcomes=3)
            rows = dict(DOWN=dict(score=4, value=2., tail_value=2.-4/2048),
                        LEFT=dict(score=0, value=1., tail_value=1.))
            return dict(action='DOWN', value=2., action_values=rows)
    calls = []
    def game(seed, act, probability, limit):
        calls.append((seed, probability, limit))
        assert [act(BOARD, 0), act(AFTER, 1)] == ['DOWN', 'DOWN']
        return dict(seed=seed, return_score=8, status='LOST', steps_count=2, seconds=0.,
            initial_board=BOARD, initial_spawns=[], final_board=AFTER,
            steps=[dict(action='DOWN', score=4, spawned_cell=1, spawned_rank=1)]*2,
            work=dict(sampled_transitions=2))
    monkeypatch.setattr(runner, 'run_episode', game)
    model = Model(); model.freeze()
    row = runner.full_game(Planner(), model, 1, 'risk8', 'SINGLE', 'H2', 3)
    assert calls == [(runner.evaluation_seed(1, 3), .1, 2000)]
    assert row['method'] == 'SINGLE_H2' and row['chosen_values'] == [2., 2.]
    assert len(row['action_values']) == 2
    assert all(set(r) == {'DOWN', 'LEFT'} and r['LEFT']['value'] == 1. for r in row['action_values'])
    assert row['result']['policy_counts'] == dict(choose_calls=2, enumerated_model_outcomes=6)
    assert row['result']['utility'] == 8/2048-8
    assert row['result']['model_state_before'] == row['result']['model_state_after']


def test_direct_and_h2_share_each_frozen_leaf_and_all_paired_games_run(tmp_path, monkeypatch):
    loads, planners, calls = [], [], []
    class Single(Model):
        @classmethod
        def load(cls, path, parent, build):
            assert '_SINGLE_' in path
            model = cls(); loads.append(model); return model
    class Capacity(Model):
        @classmethod
        def load(cls, path, parent, build):
            assert '_CAPACITY_' in path
            model = cls('CAPACITY'); loads.append(model); return model
    class Planner:
        def __init__(self, model, depth, build_dir):
            assert not model.weights.flags.writeable
            self.model, self.depth = model, depth
            self.spawn_probabilities = (.895, .105)
            self.counts, self.setup_counts, self.setup_seconds = Counter(), {}, 0.
            planners.append(self)
    def game(planner, model, life, query, representation, mode, replica):
        assert planner.model is model and not model.weights.flags.writeable
        assert planner.depth == runner.DEPTHS[mode]
        calls.append((life, query, representation, mode, replica, runner.evaluation_seed(life, replica)))
        return dict(query=query, representation=representation, mode=mode, replica=replica)
    monkeypatch.setattr(runner, 'QueryTD', Single)
    monkeypatch.setattr(runner, 'ConditionalQueryTD', Capacity)
    monkeypatch.setattr(runner, 'FrozenLeafPlanner', Planner)
    monkeypatch.setattr(runner, 'full_game', game)
    monkeypatch.setattr(runner, 'load_parent', lambda *args: (Model(), {}))
    source = runner.extract_source(*source_fixture())['snapshots'][0]
    data = runner.evaluate_lifecycle(source, tmp_path)
    assert len(loads) == 4 and len(planners) == 8 and len(calls) == 128
    assert all(planners[i].model is planners[i+1].model for i in (0, 2, 4, 6))
    assert len({id(planner.model) for planner in planners}) == 4
    assert len(set(row[:5] for row in calls)) == 128
    for replica in range(16):
        assert len({row[-1] for row in calls if row[4] == replica}) == 1
    with gzip.open(tmp_path/data['control_trace'], 'rt') as stream:
        assert len(list(stream)) == 128
    assert all(query['parent_before'] == query['parent_after'] for query in data['queries'].values())
    assert all(plan['spawn_probabilities'] == [.895, .105]
        for query in data['queries'].values()
        for representation in query['representations'].values()
        for plan in representation['planners'].values())


def test_source_and_code_are_retained_before_first_evaluation(tmp_path, monkeypatch):
    previous, old_run, analysis = source_fixture()
    source_folder = tmp_path/'old'; source_folder.mkdir()
    for name, value in [('source_capsule.json', previous), ('run.json', old_run), ('analysis.json', analysis)]:
        (source_folder/name).write_text(json.dumps(value))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def snapshot(directory):
        assert (directory/'source_capsule.json').exists()
        assert not (directory/'run.json').exists()
        events.append('source')
    def evaluate(source, directory):
        assert events[0] == 'source'
        data = json.loads((directory/'run.json').read_text())
        assert data['status'] == 'evaluation' and data['settings']['new_training_transitions'] == 0
        assert all(ref['checkpoint'] == 524288 for query in source['leaves'].values() for ref in query.values())
        events.append(source['life'])
        return dict(life=source['life'])
    monkeypatch.setattr(runner, 'SOURCE', source_folder)
    monkeypatch.setattr(runner, 'snapshot_code', snapshot)
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    output = tmp_path/'run'; runner.run(output)
    assert events == ['source', 0, 1, 2, 3]
    final = json.loads((output/'run.json').read_text())
    assert final['status'] == 'complete' and [r['life'] for r in final['eval_lifecycles']] == [0, 1, 2, 3]
