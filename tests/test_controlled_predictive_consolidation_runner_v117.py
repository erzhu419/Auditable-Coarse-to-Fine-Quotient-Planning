"""Runner isolation, retained choices, current-context evaluation and fresh streams."""
import ast
from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_consolidation_v117 as runner

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = runner.ROOT / 'reports/controlled_predictive_consolidation_runner_v117.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        development_work=dict(WORK), newly_sampled_environment_transitions=0,
        new_synthetic_transitions=0, neural_model_fits=0,
        scope='mock collectors, model payloads, planning, and historical seed arithmetic'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def fixture_game(seed=0):
    return dict(seed=seed, status='LOST', steps_count=1, steps=[{}],
        return_score=0, work=dict(sampled_transitions=1, initial_spawns=2,
        environment_random_draws=6), seconds=0.)


def fixture_record(episode=0, policy='GREEDY', batch=0, module_id=0):
    return dict(episode=episode, policy=policy, batch=batch, anchor_step=0,
        horizon=30, context_module_id=module_id, board=[1]+[0]*15, target=[0.,0.,0.])


class PayloadModel:
    def __init__(self, payload):
        self.payload = deepcopy(payload)
        self.module_id = payload.get('module_id', 0)
        self.counts = Counter(payload.get('counts', {}))

    @classmethod
    def from_payload(cls, payload):
        WORK['mock_payload_reads'] += 1
        return cls(payload)

    def predict_records(self, records):
        self.counts['prediction_record_requests'] += len(records)
        WORK['mock_prediction_records'] += len(records)
        if self.payload.get('expected_context') is not None:
            assert self.module_id == self.payload['expected_context']
            assert all(row['context_module_id'] == self.module_id for row in records)
        return [[self.payload.get('value', 0.)]*3 for row in records]

    def can_route(self, module_id):
        return module_id in self.payload.get('available_modules', [module_id])

    def to_payload(self):
        return dict(deepcopy(self.payload), module_id=self.module_id, counts=dict(self.counts))


def test_lifecycle_never_fits_reserved_validation_and_preserves_selected_history(tmp_path, monkeypatch):
    template = SimpleNamespace(program='fixed', spawn_distribution=((1,.9),(2,.1)))
    class Router:
        observations_seen = 0
        module_id = 0
        def __init__(self, method):
            assert method == 'LIBRARY'
        def to_rule(self, supplied):
            assert supplied is template
            return supplied
        def to_payload(self):
            return dict(observations_seen=self.observations_seen, module_id=self.module_id)
    fit_rosters, validation_rosters, outer_versions = [], [], []
    def policy_game(seed, policy, supplied, p4, max_steps):
        WORK['mock_source_games'] += 1
        assert supplied is template
        return fixture_game(seed), {}
    def causal_records(game, policy, episode, router):
        router.observations_seen += 1
        router.module_id = (router.observations_seen-1)//18
        return [fixture_record(episode, policy, module_id=router.module_id)], dict(counts=dict(observed_transitions=1))
    def fit(records, mode, module_id):
        WORK['mock_fit_calls'] += 1
        roster = [row['episode'] for row in records]
        fit_rosters.append(roster)
        payload = dict(mode=mode, module_id=module_id, fit_roster=roster, stamp=f'{mode}:{module_id}')
        return PayloadModel(payload), dict(training_roster=deepcopy(records))
    def selection(records, models, previous, module_id):
        validation_rosters.append([row['episode'] for row in records])
        choice = ('NEW_SHARED', 'KEEP', 'NEW_SPLIT')[module_id]
        selected = deepcopy(previous if choice == 'KEEP' else models[choice.removeprefix('NEW_')])
        selected['module_id'] = module_id
        return selected, dict(selected_candidate=choice), dict(records=deepcopy(records))
    def predictive(life, phase, supplied, module_id, versions, stream):
        outer_versions.append(deepcopy(versions))
        return [], {}
    def control(*args):
        WORK['mock_control_games'] += 1
        return {}, {}
    monkeypatch.setattr(runner, 'LearnedDynamics', SimpleNamespace(from_payload=lambda _: template))
    monkeypatch.setattr(runner, 'SpawnMemory', Router)
    monkeypatch.setattr(runner, 'BankKnowledge', SimpleNamespace(fit=fit))
    monkeypatch.setattr(runner, 'policy_game', policy_game)
    monkeypatch.setattr(runner, 'causal_records', causal_records)
    monkeypatch.setattr(runner, 'validation_selection', selection)
    monkeypatch.setattr(runner, 'prediction_games', predictive)
    monkeypatch.setattr(runner, 'control_game', control)
    result = runner.lifecycle_run(0, tmp_path, {})
    for phase_index, phase in enumerate(result['phases']):
        expected_fit = [i for i in range(18*(phase_index+1)) if i%18 < 12]
        expected_validation = [i for i in range(18*(phase_index+1)) if i%18 >= 12]
        assert fit_rosters[2*phase_index:2*phase_index+2] == [expected_fit, expected_fit]
        assert validation_rosters[phase_index] == expected_validation
        assert not set(expected_fit) & set(expected_validation)
        assert [game['role'] for game in phase['source_games']] == ['FIT']*12+['VALIDATION']*6
        assert all(phase['checkpoint']['checks'].values())
    checkpoints = [phase['checkpoint'] for phase in result['phases']]
    assert [cp['selected_origin'] for cp in checkpoints] == [
        dict(batch=0,mode='SHARED'),dict(batch=0,mode='SHARED'),dict(batch=2,mode='SPLIT')]
    assert checkpoints[0]['models']['SELECTED']['stamp'] == checkpoints[1]['models']['SELECTED']['stamp'] == 'SHARED:0'
    assert outer_versions[2]['A_END'] == checkpoints[0]['models']
    assert outer_versions[2]['B_END'] == checkpoints[1]['models']
    assert all(result['checks'].values())


def test_validation_selects_or_keeps_parameters_without_changing_historical_contexts(monkeypatch):
    monkeypatch.setattr(runner, 'BankKnowledge', PayloadModel)
    records = [fixture_record(module_id=7), fixture_record(episode=1,module_id=8)]
    models = {mode: dict(mode=mode,module_id=-1,value=value,counts={'old':99})
        for mode,value in [('SHARED',2.),('SPLIT',0.)]}
    original = deepcopy(models)
    chosen, first, details = runner.validation_selection(records,models,None,42)
    assert first['selected_candidate'] == 'NEW_SHARED' and chosen['value'] == 2.
    assert chosen['module_id'] == 42 and chosen['counts'] == {}
    assert details['records'] == records and models == original
    previous = dict(mode='SHARED',module_id=3,value=0.,counts={})
    selected, kept, details = runner.validation_selection(records,models,previous,42)
    assert kept['selected_candidate'] == 'KEEP' and selected['value'] == 0.
    assert selected['module_id'] == 42 and previous['module_id'] == 3
    selected, updated, details = runner.validation_selection(records,models,chosen,42)
    assert updated['selected_candidate'] == 'NEW_SPLIT' and selected['value'] == 0.
    assert [row['context_module_id'] for row in details['records']] == [7,8]
    assert all('old' not in counts for counts in details['prediction_counts'].values())


def test_outer_archives_use_current_module_and_missing_control_branch_falls_back(monkeypatch):
    monkeypatch.setattr(runner, 'BankKnowledge', PayloadModel)
    def policy_game(seed, policy, template, p4, max_steps):
        WORK['mock_predictive_games'] += 1
        return fixture_game(seed), {}
    monkeypatch.setattr(runner,'policy_game',policy_game)
    monkeypatch.setattr(runner,'targets',lambda game,policy,episode,**kwargs: [fixture_record(episode,policy,module_id=99)])
    versions = {version: {track: dict(module_id=-1, expected_context=42,counts={'old':99})
        for track in runner.TRACKS} for version in ('CURRENT','A_END','B_END')}
    original = deepcopy(versions)
    rows, counts = runner.prediction_games(1,2,object(),42,versions,io.StringIO())
    assert len(rows) == 6 and versions == original
    assert all(row['records'][0]['context_module_id'] == 42 for row in rows)
    assert all(value['prediction_record_requests'] == 6 and 'old' not in value
        for group in counts.values() for value in group.values())
    chosen_knowledge = []
    def choose(board, query, knowledge, rule, rng, depth, work):
        chosen_knowledge.append(knowledge)
        work['model_uniform_draws'] += 4
        WORK['mock_planner_calls'] += 1
        return dict(action='LEFT',value=0.,metrics={},policy=None,branches=[],action_values={'LEFT':{}})
    def run_episode(seed, actor, p4, max_steps):
        assert actor((1,)+(0,)*15,0) == 'LEFT'
        WORK['mock_control_games'] += 1
        return fixture_game(seed)
    monkeypatch.setattr(runner.planner,'choose',choose)
    monkeypatch.setattr(runner,'run_episode',run_episode)
    row, raw = runner.control_game('SPLIT_PLAN','reward',0,1,2,object(),42,
        dict(module_id=0,available_modules=[0],counts={'old':99}))
    assert chosen_knowledge == [None]
    assert row['result']['fallback_h2'] and row['result']['routed_module_id'] == 42
    assert row['result']['environment_counts']['sampled_transitions'] == 1
    assert row['result']['planning_counts']['model_uniform_draws'] == 4
    assert row['result']['prediction_counts'] == {}
    assert raw['decisions'][0]['action_values'] == {'LEFT':{}}


def seed_expression(path, function):
    tree = ast.parse(path.read_text())
    method = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == function)
    assignment = next(node for node in ast.walk(method) if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id == 'seed' for target in node.targets))
    return compile(ast.Expression(assignment.value),str(path),'eval')


def test_environment_seed_namespaces_are_new_and_disjoint_across_lives_and_roles():
    scripts = runner.ROOT/'scripts'
    current = Path(runner.__file__)
    values = {}
    for role,function in [('source','lifecycle_run'),('prediction','prediction_games'),('control','control_game')]:
        expr = seed_expression(current,function)
        seeds = []
        for life in runner.LIFECYCLES:
            for phase_index in range(3):
                if role == 'source':
                    assignments = [dict(local_episode=i) for i in range(runner.SOURCE_GAMES)]
                elif role == 'prediction':
                    assignments = [dict(policy_index=p,replica=r) for p in range(3) for r in range(2)]
                else:
                    assignments = [dict(replica=r) for r in range(2)]
                seeds.extend(eval(expr,{'__builtins__':{}},dict(life=life,phase_index=phase_index,**extra)) for extra in assignments)
        assert len(seeds) == len(set(seeds))
        values[role] = set(seeds)
    assert min(values['source']) == 121000000
    assert not values['source'] & (values['prediction'] | values['control'])
    assert not values['prediction'] & values['control']
    historical = set()
    for version,function,role in [(115,'lifecycle_run','source'),(115,'evaluation_game','control'),
        (116,'lifecycle_run','source'),(116,'prediction_games','prediction'),(116,'control_game','control')]:
        basename = 'regime_memory' if version == 115 else 'context_consequences'
        expr = seed_expression(scripts/f'run_controlled_predictive_{basename}_v{version}.py',function)
        for life in range(4):
            for phase_index in range(3):
                if role == 'source':
                    assignments = [dict(episode=i,local_episode=i) for i in range(6 if version==115 else 18)]
                elif role == 'prediction':
                    assignments = [dict(policy_index=p,replica=r) for p in range(3) for r in range(2)]
                elif version == 115:
                    assignments = [dict(after_game=n,replica=r) for n in ((6,) if phase_index==0 else (1,3,6)) for r in range(2)]
                else:
                    assignments = [dict(replica=r) for r in range(2)]
                historical.update(eval(expr,{'__builtins__':{}},dict(life=life,phase_index=phase_index,**extra)) for extra in assignments)
    fresh = set.union(*values.values())
    assert not fresh & historical
    WORK['fresh_environment_seeds_checked'] += len(fresh)
    WORK['historical_environment_seeds_checked'] += len(historical)
