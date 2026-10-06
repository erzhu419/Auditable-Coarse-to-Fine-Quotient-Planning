"""Mock-only integration of source prefixes, immutable models and evaluation."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import io
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import scripts.run_controlled_predictive_context_consequences_v116 as runner

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_context_consequences_runner_v116.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before,
        mock_calls=dict(WORK), environment_transitions=0, model_transitions=0,
        tree_fits=0, neural_model_fits=0, optimizer_steps=0, policy_prediction_rows=0,
        scope='Runner calls use mocked games, causal extraction, fitting and planning; namespaces are derived without sampling.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def game(policy=None):
    return dict(status='LOST', steps_count=1, return_score=2048, seconds=0.,
        work=dict(sampled_transitions=1), steps=[], actual_policy=policy)


class FakeModel:
    def __init__(self, payload):
        self.payload = deepcopy(payload)
        self.counts = Counter()
        self.context_p4 = payload['context_p4']

    def to_payload(self):
        return deepcopy(self.payload)


class FakeRouter:
    def __init__(self, method):
        assert method == 'LIBRARY'
        self.observations_seen = 0

    def to_payload(self):
        return dict(observations_seen=self.observations_seen)

    def to_rule(self, template):
        probability = Fraction(100 + self.observations_seen, 1000)
        return SimpleNamespace(program=template.program, spawn_distribution=((1, 1-probability), (2, probability)))


def test_lifecycle_fits_exact_executed_policy_prefixes_and_preserves_archives(monkeypatch, tmp_path):
    template = SimpleNamespace(program='fixed_swipe_program')
    source_calls, fit_calls, version_calls, control_rules = [], [], [], []
    monkeypatch.setattr(runner, 'SpawnMemory', FakeRouter)
    monkeypatch.setattr(runner, 'LearnedDynamics', SimpleNamespace(from_payload=lambda _: template))
    def source_game(seed, policy, supplied, p_true, max_steps):
        assert supplied is template
        source_calls.append((seed, policy, p_true))
        WORK['mock_source_games'] += 1
        return game(policy), {}
    def records(observed, policy, episode, router):
        assert observed['actual_policy'] == policy
        router.observations_seen += observed['steps_count']
        WORK['mock_causal_extractions'] += 1
        return [dict(episode=episode, policy=policy, horizon=horizon, anchor_step=0,
            board=[0] * 16, target=[1., 1., 0.], context_p4=.2) for horizon in (30, 31)], dict(counts={})
    def fit(training, mode, context):
        fit_calls.append((deepcopy(training), mode, context))
        WORK['mock_model_fits'] += 1
        payload = dict(mode=mode, context_p4=context, prefix_records=len(training),
            parameters=[len(training), mode])
        roster = [{key: row[key] for key in ('episode', 'policy', 'anchor_step', 'horizon')} for row in training]
        return FakeModel(payload), dict(training_roster=roster)
    def predictions(life, phase_index, supplied, context, versions, stream):
        version_calls.append((phase_index, context, deepcopy(versions)))
        WORK['mock_prediction_batches'] += 1
        return [], {}
    def control(method, query, replica, life, phase_index, rule, payload):
        control_rules.append((phase_index, rule, deepcopy(payload)))
        if payload is not None:
            assert payload['context_p4'] == float(dict(rule.spawn_distribution)[2])
        WORK['mock_control_games'] += 1
        return {}, {}
    monkeypatch.setattr(runner, 'policy_game', source_game)
    monkeypatch.setattr(runner, 'causal_records', records)
    monkeypatch.setattr(runner, 'ConsequenceKnowledge', SimpleNamespace(fit=fit))
    monkeypatch.setattr(runner, 'prediction_games', predictions)
    monkeypatch.setattr(runner, 'control_game', control)
    result = runner.lifecycle_run(0, tmp_path, {})
    assert len(source_calls) == 54 and len(fit_calls) == 6
    for phase_index in range(3):
        assert [policy for _, policy, _ in source_calls[phase_index * 18:(phase_index + 1) * 18]] == list(runner.POLICIES) * 6
        wanted = list(range((phase_index + 1) * 18))
        current_fits = fit_calls[phase_index * 2:phase_index * 2 + 2]
        for training, mode, context in current_fits:
            assert [row['episode'] for row in training] == [episode for episode in wanted for _ in (30, 31)]
            assert [row['policy'] for row in training] == [runner.POLICIES[e % 3] for e in wanted for _ in (30, 31)]
        assert current_fits[0][0] == current_fits[1][0]
        group = [row for row in control_rules if row[0] == phase_index]
        assert len(group) == 12 and all(row[1] is group[0][1] for row in group)
        assert all(result['phases'][phase_index]['checkpoint']['checks'].values())
    _, current_context, versions = version_calls[-1]
    assert set(versions) == {'CURRENT', 'A_END', 'B_END'}
    for mode in runner.MODES:
        assert versions['A_END'][mode] == result['phases'][0]['checkpoint']['models'][mode]
        assert versions['B_END'][mode] == result['phases'][1]['checkpoint']['models'][mode]
        assert versions['CURRENT'][mode]['prefix_records'] == 108
        assert versions['A_END'][mode]['context_p4'] != current_context
        assert versions['B_END'][mode]['context_p4'] != current_context
    assert result['final_router']['observations_seen'] == 54 and all(result['checks'].values())


def test_each_prediction_version_receives_current_context_without_payload_mutation(monkeypatch):
    calls = []
    class PredictionModel(FakeModel):
        def predict_records(self, rows, context):
            calls.append((self.payload['version'], self.payload['mode'], context,
                [(r['policy'], r['horizon']) for r in rows]))
            self.counts['mock_record_rows'] += len(rows)
            WORK['mock_record_prediction_calls'] += 1
            return np.asarray([[context, float(row['horizon']), 0.] for row in rows])
    def source_game(seed, policy, template, p_true, max_steps):
        WORK['mock_prediction_games'] += 1
        return game(policy), {}
    def labels(observed, policy, episode, stride, horizons):
        assert observed['actual_policy'] == policy and stride == 4 and horizons == (30, 31)
        return [dict(policy=policy, horizon=horizon, target=[0., 0., 0.], anchor_step=0) for horizon in horizons]
    monkeypatch.setattr(runner, 'ConsequenceKnowledge', SimpleNamespace(from_payload=PredictionModel))
    monkeypatch.setattr(runner, 'policy_game', source_game)
    monkeypatch.setattr(runner, 'targets', labels)
    versions = {version: {mode: dict(version=version, mode=mode, context_p4=context, parameters=[1, 2, 3])
        for mode in runner.MODES} for version, context in (('CURRENT', .13), ('A_END', .09), ('B_END', .29))}
    saved = deepcopy(versions)
    rows, counts = runner.prediction_games(0, 2, object(), .13, versions, io.StringIO())
    assert versions == saved and len(rows) == 6 and len(calls) == 36
    assert all(call[2] == .13 for call in calls)
    assert {row['policy'] for row in rows} == set(runner.POLICIES)
    assert {row['seed'] for row in rows} == {116800000 + 2 * 10000 + pi * 100 + replica for pi in range(3) for replica in range(2)}
    for row in rows:
        for record in row['records']:
            assert all(values == [.13, record['horizon'], 0.] for group in record['predictions'].values() for values in group.values())
    assert all(row['mock_record_rows'] == 12 for group in counts.values() for row in group.values())


def test_control_preserves_joint_policy_vectors_shared_rule_and_disjoint_namespaces(monkeypatch):
    rules, chosen_vectors = [], []
    def choose(board, query, knowledge, rule, rng, depth, work):
        assert depth == 2
        rules.append(rule)
        if knowledge is not None:
            assert knowledge.context_p4 == .17
        vector = dict(reward=2., failure=.25, success=.5)
        chosen = dict(action='LEFT', metrics=vector,
            value=query['reward_weight'] * 2. - query['failure_penalty'] * .25 + query['goal_bonus'] * .5,
            policy='SPACE', branches=[dict(policy='SPACE', metrics=deepcopy(vector))])
        chosen_vectors.append(deepcopy(chosen))
        WORK['mock_planner_calls'] += 1
        return chosen
    def episode(seed, actor, p_true, max_steps):
        assert actor((1, 1) + (0,) * 14, 0) == 'LEFT'
        WORK['mock_control_games'] += 1
        return game()
    monkeypatch.setattr(runner.planner, 'choose', choose)
    monkeypatch.setattr(runner, 'run_episode', episode)
    monkeypatch.setattr(runner, 'ConsequenceKnowledge', SimpleNamespace(from_payload=FakeModel))
    rule = object(); control_seeds = set()
    for life in runner.LIFECYCLES:
        for phase_index in range(3):
            for replica in range(2):
                for method in runner.METHODS:
                    for query in runner.QUERIES:
                        payload = None if method == 'H2_ONLY' else dict(context_p4=.17)
                        row, raw = runner.control_game(method, query, replica, life, phase_index, rule, payload)
                        assert raw['decisions'] == [chosen_vectors[-1]]
                        assert row['result']['utility'] == (1. if query == 'reward' else -3.)
                        control_seeds.add(row['seed'])
    assert len(control_seeds) == 24 and all(value is rule for value in rules)
    source_seeds = {116000000 + life * 10000 + phase * 100 + episode
        for life in runner.LIFECYCLES for phase in range(3) for episode in range(18)}
    prediction_seeds = {116800000 + life * 100000 + phase * 10000 + policy * 100 + replica
        for life in runner.LIFECYCLES for phase in range(3) for policy in range(3) for replica in range(2)}
    assert len(source_seeds) == 216 and len(prediction_seeds) == 72
    assert not source_seeds & prediction_seeds
    assert not source_seeds & control_seeds
    assert not prediction_seeds & control_seeds
