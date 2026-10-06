"""Validation weighting, preservation, coverage, and deterministic update choice."""
from collections import Counter
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_consolidation_selection_v117 import score_candidate, select_update

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_consolidation_selection_v117.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed-before,
        development_work=dict(WORK), newly_sampled_environment_transitions=0,
        new_synthetic_transitions=0, neural_model_fits=0,
        scope='synthetic validation vectors; pure list arithmetic only'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def choose(records, predictions):
    WORK['selector_calls'] += 1
    WORK['synthetic_validation_records'] += len(records)
    WORK['provided_prediction_vectors'] += sum(
        sum(value is not None for value in rows) if rows is not None else 0
        for rows in predictions.values())
    return select_update(records, predictions)


def row(batch, episode=0, policy='GREEDY', horizon=30):
    return dict(batch=batch, episode=episode, policy=policy, horizon=horizon, target=[0.,0.,0.])


def vector(value):
    return [value, value, value]


def test_weights_anchors_horizons_games_policies_and_batches_separately():
    records = [row(0)] * 3 + [row(0, horizon=31), row(0, episode=1),
        row(0, policy='SPACE'), row(1)]
    # Reward MSE: first game ((0+0+9)/3+9)/2=6; GREEDY=(6+4)/2=5;
    # batch0=(5+1)/2=3; batch1=9; equally weighted reward=6.
    values = [[v, 0., 0.] for v in (0., 0., 3., 3., 2., 1., 3.)]
    result = choose(records, dict(KEEP=values, NEW_SHARED=values, NEW_SPLIT=values))
    score = result['scores']['KEEP']
    assert score['batches']['0']['components'] == dict(reward=3., failure=0., success=0.)
    assert score['batches']['0']['policies']['GREEDY']['games'][0]['components']['reward'] == 6.
    assert score['batches']['0']['joint_loss'] == 1.
    assert score['batches']['1']['joint_loss'] == 3.
    assert score['mean_joint_loss'] == 2.
    assert result['selected_candidate'] == 'KEEP'
    WORK['score_candidate_calls'] += 1
    assert score_candidate(records, values) == score


def test_old_batch_harm_is_rejected_even_when_pooled_loss_improves():
    records = [row(0)] + [row(1, episode=i) for i in range(8)]
    keep = [vector(0)] + [vector(2)] * 8
    shared = [vector(1)] + [vector(0)] * 8
    result = choose(records, dict(KEEP=keep, NEW_SHARED=shared, NEW_SPLIT=keep))
    assert result['scores']['NEW_SHARED']['mean_joint_loss'] < result['scores']['KEEP']['mean_joint_loss']
    assert result['acceptance']['NEW_SHARED']['harmed_batches'] == [0]
    assert result['acceptance']['NEW_SHARED']['improved_batches'] == [1]
    assert not result['acceptance']['NEW_SHARED']['eligible']
    assert result['selected_candidate'] == 'KEEP'


def test_candidate_missing_coverage_rejected_and_incumbent_missing_coverage_repaired():
    records = [row(0), row(1), row(1, horizon=31)]
    result = choose(records, dict(KEEP=[vector(1),None,vector(0)],
        NEW_SHARED=[vector(0),vector(0),None], NEW_SPLIT=[vector(1),vector(2),vector(2)]))
    batch = result['scores']['NEW_SHARED']['batches']['1']
    assert not batch['covered'] and batch['joint_loss'] is None
    assert batch['components'] == dict(reward=None, failure=None, success=None)
    assert result['acceptance']['NEW_SHARED']['uncovered_batches'] == [1]
    assert result['acceptance']['NEW_SPLIT']['newly_covered_batches'] == [1]
    assert result['acceptance']['NEW_SPLIT']['equal_batches'] == [0]
    assert result['selected_candidate'] == 'NEW_SPLIT'
    all_missing = choose(records, dict(KEEP=None, NEW_SHARED=None, NEW_SPLIT=[vector(1)]*3))
    assert all_missing['selected_candidate'] == 'NEW_SPLIT'


def test_exact_ties_prefer_shared_for_eligible_updates_and_keep_without_improvement():
    records = [row(1), row(0)]
    result = choose(records, dict(KEEP=[vector(2)]*2, NEW_SPLIT=[vector(1)]*2, NEW_SHARED=[vector(1)]*2))
    assert result['batch_order'] == [0,1]
    assert result['selected_candidate'] == 'NEW_SHARED'
    assert all(case['eligible'] for case in result['acceptance'].values())
    tied = choose(records, dict(KEEP=[vector(1)]*2, NEW_SHARED=[vector(1)]*2, NEW_SPLIT=[vector(1)]*2))
    assert tied['selected_candidate'] == 'KEEP'
    assert all(case['equal_batches'] == [0,1] and case['reasons'] == ['no_strict_improvement']
        for case in tied['acceptance'].values())
