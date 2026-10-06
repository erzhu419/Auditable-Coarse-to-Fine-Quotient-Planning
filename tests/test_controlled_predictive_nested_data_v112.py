"""Inner scoring must follow its two excluded histories and actual root roster."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_nested_data_v112 as module
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    original = module.CandidateModel.score_candidates
    def counted(model, features, work=None):
        scores = original(model, features, work)
        WORK['model_root_scores'] += 1
        WORK['neural_candidate_predictions'] += len(features)
        WORK['neural_hidden_activations'] += len(features) * model.hidden
        return scores
    module.CandidateModel.score_candidates = counted
    yield
    module.CandidateModel.score_candidates = original
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_nested_data_v112.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before, fixture_work=dict(WORK),
        new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
        actual_source_files_read=0, scope='synthetic source rows and manually specified scorer payloads'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def bank():
    return {life: [dict(source_life=life, query=query, episode=episode,
        is_half=half, features=[[index]]) for index, (query, episode, half) in enumerate([
            ('reward', 0, True), ('risk_goal', 4, True), ('reward', 5, True),
            ('risk_goal', 5, False), ('reward', 6, False)])] for life in (11, 12, 13, 14)}


def test_pair_preserves_batch_membership_and_cross_history_root_identity():
    original = bank()
    records, log = module.pool_pair(original, [12, 11])
    assert log['pair_id'] == '11_12' and log['source_lives'] == [11, 12]
    assert log['validation_lives'] == [13, 14] and len(records) == 10
    assert log['half']['training_roster'] == [[11, 'reward', 0], [11, 'reward', 5],
        [12, 'reward', 0], [12, 'reward', 5]]
    assert log['full']['training_roster'][2] == [11, 'risk_goal', 5]
    assert all(log['checks'].values())
    records[0]['features'][0][0] = -999
    assert original[11][0]['features'] == [[0]]


@pytest.mark.parametrize('fault', ['source_tag', 'duplicate'])
def test_pair_rejects_source_tag_or_identity_corruption(fault):
    source = bank()
    if fault == 'source_tag':
        source[11][0]['source_life'] = 14
    else:
        source[11].append(deepcopy(source[11][0]))
    with pytest.raises(ValueError, match='source history|identities must be unique'):
        module.pool_pair(source, [11, 12])


@pytest.fixture
def scorers(tmp_path):
    models = []
    sources, validation = [11, 12], [13, 14]
    training = [[life, query, 0] for life in sources for query in ('reward', 'risk_goal')]
    episodes = {query: [[life, 0] for life in sources] for query in ('reward', 'risk_goal')}
    for width, stage in ((4, 'HALF'), (16, 'FULL')):
        weights = np.zeros((121, width))
        weights[0, 0] = 1
        checkpoint = 256000 if stage == 'HALF' else 512000
        model = module.CandidateModel([weights, np.zeros(width), np.ones(width)],
            np.zeros(121), np.ones(121), checkpoint, 'UNIFORM_SHRINK', episodes, .5)
        payload = model.to_payload()
        payload['update'] = dict(pair_id='11_12', source_lives=sources, validation_lives=validation,
            stage=stage, training_roster=training, statistics_roster=training,
            optimizer_state='reset_zero_moments', new_optimizer_steps=1000)
        path = tmp_path / f'model_{width}.json'
        path.write_text(json.dumps(payload))
        WORK['fixture_payload_files_written'] += 1
        models.append(dict(pair_id='11_12', method=f'POOLED_H{width}_{stage}', metadata=dict(
            source_lives=sources, validation_lives=validation, hidden=width, stage=stage,
            family='UNIFORM_SHRINK', checkpoint=checkpoint, budget=checkpoint,
            path=str(path), parameter_count=123 * width)))
    features = [[value] + [0.] * 120 for value in (0, .5, .5, -.2, .1)]
    roots = [dict(root_id=f'{life}_{query}', life=life, query=query, episode=0,
        features=deepcopy(features) if life in validation else 'source features must never be scored')
        for life in (11, 12, 13, 14) for query in ('reward', 'risk_goal')]
    return models, roots


def test_actual_models_score_only_both_excluded_histories_with_exact_work(scorers):
    models, roots = scorers
    decisions, log = module.score_inner_models(models, roots)
    assert len(decisions) == log['expected_model_root_scores'] == 8
    assert {row['validation_life'] for row in decisions} == {13, 14}
    assert all(row['pair_id'] == '11_12' and row['event']['option'] == OPTIONS[1] for row in decisions)
    assert all(log['checks'].values())
    assert log['counts']['model_payloads_loaded'] == 2
    assert log['counts']['neural_candidate_predictions'] == 40
    assert log['counts']['neural_hidden_activations'] == 400
    assert log['counts']['neural_model_fits'] == log['counts']['new_environment_transitions'] == 0


@pytest.mark.parametrize('fault', ['validation_contains_source', 'payload_source'])
def test_polluted_model_metadata_stops_before_scoring(scorers, fault):
    models, roots = scorers
    if fault == 'validation_contains_source':
        models[0]['metadata']['validation_lives'] = [11, 14]
    else:
        path = Path(models[0]['metadata']['path'])
        payload = json.loads(path.read_text())
        payload['update']['source_lives'] = [11, 13]
        path.write_text(json.dumps(payload))
    decisions, log = module.score_inner_models(models, roots)
    assert decisions == [] and not all(log['checks'].values())
    assert log['counts']['model_root_scores'] == log['counts']['neural_candidate_predictions'] == 0


def test_missing_root_changes_actual_scoring_roster_without_inventing_evidence(scorers):
    models, roots = scorers
    shortened = [root for root in roots if root['root_id'] != '14_risk_goal']
    decisions, log = module.score_inner_models(models, shortened)
    # The outer frozen-cohort check is responsible for rejecting missing evidence.
    assert len(decisions) == log['expected_model_root_scores'] == 6
    assert log['counts']['neural_candidate_predictions'] == 30
    assert log['counts']['neural_hidden_activations'] == 300 and all(log['checks'].values())
