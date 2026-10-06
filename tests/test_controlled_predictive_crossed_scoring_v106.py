"""Fixed payload cross scoring, exact diagonals, stopping costs and original ties."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_crossed_scoring_v106 as m
from acfqp.science.controlled_predictive_capacity_ranking_v103 import CandidateModel, initialize

WORK = Counter()
METHODS = [f'R4_H{width}_UNIFORM_SHRINK_DIRECT{suffix}' for suffix in ('', '_FROZEN_HALF') for width in (4, 16)]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_crossed_scoring_v106.checks.json'
    result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(failed_tests=request.session.testsfailed - before, development_work=dict(WORK),
        production_neural_candidate_predictions=0, neural_model_fits=0, optimizer_steps=0,
        environment_transitions=0, model_transitions=0,
        scope='Untrained synthetic frozen payloads and real neural scoring; no model fitting or sampling.'))
    path.write_text(json.dumps(result, indent=2) + '\n')


def cohort(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    run = dict(status='complete', settings=dict(lifecycles=[11, 12, 13, 14], budgets=[256000, 512000],
        methods=['H2_ONLY', 'PREFIX_ONLY_DIRECT'] + METHODS, evaluation_replicas=1), allocations=[], lifecycles=[])
    stored = {}; rng = np.random.default_rng(106)
    for life in (11, 12, 13, 14):
        metadata = {}; stages = {}
        for method in METHODS:
            width = int(method.split('_')[1][1:]); half = method.endswith('_FROZEN_HALF')
            checkpoint, budget, gamma = (3, 256000, .5) if half else (7, 512000, .75)
            parameters = initialize(121, width); parameters[2] *= (life - 9) * (1 if half else .8)
            episodes = {'reward': [0, 1], 'risk_goal': [0, 1]}
            model = CandidateModel(parameters, np.zeros(121), np.ones(121), checkpoint,
                'UNIFORM_SHRINK', episodes, gamma)
            stored[life, method] = model
            path = source / f'{life}_{method}.json'; path.write_text(json.dumps(model.to_payload()))
            metadata[method] = dict(replicas=4, budget=budget, episode_cutoff=checkpoint,
                family='UNIFORM_SHRINK', hidden=width, parameter_count=123 * width, path=str(path))
            stage = stages.setdefault(budget, dict(budget=budget, episode_cutoff=checkpoint, fit_logs={}))
            stage['fit_logs'][str(width)] = dict(checkpoint=checkpoint, training_episodes=deepcopy(episodes), uniform_gamma=gamma)
        allocation = dict(life=life, model_metadata=metadata, construction=list(stages.values()))
        run['allocations'].append(allocation)
        run['lifecycles'].append(dict(id=life, allocations=[deepcopy(allocation)], evaluation=dict(model_metadata=deepcopy(metadata))))
    roots = []
    fixture_counts = Counter()
    for life in (11, 12, 13, 14):
        for query in m.QUERIES:
            features = rng.normal(size=(5, 121)).tolist(); board = [1] * 10 + [0] * 6
            predictions = {}
            for method in METHODS:
                scores = stored[life, method].score_candidates(features, fixture_counts)
                best = max(range(5), key=lambda i: scores[i])
                predictions[method] = dict(board=list(board), step=58, option=m.OPTIONS[best], value=scores[best],
                    predictions={option: dict(value=scores[i]) for i, option in enumerate(m.OPTIONS)}, score_semantics='rank_score')
            roots.append(dict(root_id=f'{life}_{query}_0', life=life, query=query, episode=0, features=features,
                original_predictions=predictions, board=board, step=58))
    WORK['fixture_neural_candidate_predictions'] += fixture_counts['neural_candidate_predictions']
    WORK['fixture_neural_hidden_activations'] += fixture_counts['neural_hidden_activations']
    return source, run, roots


def score(source, run, roots):
    result = m.score_models(source, run, roots)
    for key, value in result[2]['counts'].items():
        WORK['scorer_' + key] += value
    return result


def test_full_cross_grid_keeps_exact_diagonal_and_actual_width_counts(tmp_path):
    source, run, roots = cohort(tmp_path)
    models, decisions, log = score(source, run, list(reversed(roots)))
    assert all(log['checks'].values()) and len(models) == 16 and len(decisions) == 128
    assert log['counts']['model_payloads_loaded'] == 16
    assert log['counts']['diagonal_model_root_scores'] == 32
    assert log['counts']['neural_candidate_predictions'] == 640
    assert log['counts']['neural_hidden_activations'] == 6400
    assert [row['training_life'] for row in models] == [life for life in (11, 12, 13, 14) for _ in METHODS]
    assert [row['method'] for row in models[:4]] == METHODS
    root_life = {root['root_id']: root['life'] for root in roots}
    assert all(row['training_life'] == root_life[row['root_id']] for row in decisions[:32])
    assert all(row['training_life'] != root_life[row['root_id']] for row in decisions[32:])
    assert all(row['event']['score_semantics'] == 'rank_score' for row in decisions)
    assert not any(log['counts'][key] for key in ('neural_model_fits', 'optimizer_steps', 'new_environment_transitions', 'new_synthetic_transitions'))


def test_swapped_age_payload_stops_before_any_scoring(tmp_path):
    source, run, roots = cohort(tmp_path)
    method, wrong = METHODS[0], METHODS[2]
    path = run['allocations'][0]['model_metadata'][wrong]['path']
    for metadata in (run['allocations'][0]['model_metadata'], run['lifecycles'][0]['allocations'][0]['model_metadata'],
                     run['lifecycles'][0]['evaluation']['model_metadata']):
        metadata[method]['path'] = path
    _, decisions, log = score(source, run, roots)
    assert not log['checks']['frozen_model_training_match']
    assert decisions == [] and log['counts']['model_payloads_loaded'] == 1
    assert log['counts']['neural_candidate_predictions'] == 0


@pytest.mark.parametrize('mismatch', ('score', 'choice'))
def test_diagonal_mismatch_stops_and_retains_actual_prediction_cost(tmp_path, mismatch):
    source, run, roots = cohort(tmp_path)
    original = roots[0]['original_predictions'][METHODS[0]]
    if mismatch == 'score':
        old_score = original['predictions']['SPACE_1']['value']
        original['predictions']['SPACE_1']['value'] = float(np.nextafter(old_score, np.inf))
    else:
        original['option'] = next(option for option in m.OPTIONS if option != original['option'])
    _, decisions, log = score(source, run, roots)
    assert not log['checks']['diagonal_scores_exact' if mismatch == 'score' else 'diagonal_choices_exact']
    assert not log['checks']['scoring_roster_complete']
    assert len(decisions) == log['counts']['model_root_scores'] == 1
    assert log['counts']['neural_candidate_predictions'] == 5
    assert log['counts']['neural_hidden_activations'] == 20


def test_ties_preserve_original_strictly_positive_first_option_rule():
    assert m._event([0., 1., 1., -1., 0.])['option'] == 'SPACE_1'
    assert m._event([0., 0., 0., 0., 0.])['option'] == 'H2'
    assert m._event([0., -2., -1., -3., -4.])['option'] == 'H2'
