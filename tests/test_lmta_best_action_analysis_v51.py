"""Synthetic paired records only: no dataset, tensor, or environment access."""
from collections import Counter
from copy import deepcopy
import importlib.util
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load_module('lmta_best_action_analysis_v51', ROOT / 'scripts/analyze_lmta_best_action_v51.py')
source_fixture = load_module('lmta_v49_fixture', ROOT / 'tests/test_lmta_supervised_analysis_v49.py')


def fixture():
    old_metrics, old_manifest, old_collections, old_training = source_fixture.fixture()
    for row in old_metrics:
        if row['checkpoint'] == 2000:
            chosen = 2. - .02 * (row['run_id'] + 1)
            gap = 2. - chosen
            row.update(chosen_score=chosen, score_regret=gap, relative_regret=gap / 2.,
                       optimal=False, predicted_node=1)
    metrics, training, manifest = deepcopy(old_metrics), deepcopy(old_training), deepcopy(old_manifest)
    for row in metrics:
        size = 1 + row['state_id'] % 2
        probability = size / row['legal_nodes'] if row['checkpoint'] == 0 else .98
        row.update(best_set_size=size, best_set_probability=probability, best_set_nll=-math.log(probability))
        if row['checkpoint'] == 2000:
            row.update(predicted_node=499, chosen_score=2., score_regret=0., relative_regret=0.,
                       optimal=True, pairwise_correct=float(row['pairwise_pairs']), mse=100.)
    manifest.update(schema='acfqp.lmta_best_action.v51', protocol=deepcopy(analysis.FROZEN_PROTOCOL),
        source_directory='reports/lmta_supervised_v49', dataset_path='reports/lmta_supervised_v49/dataset.npz',
        initial_anchors_complete=True, source_read_seconds=.1, supervision_preparation_seconds=.3,
        new_environment_calls=0, new_RL_training_updates=0, new_MCTS_calls=0)
    del manifest['dataset_serialization_seconds']
    for row in manifest['runs']:
        row.update(base_parameters=50433, candidate_parameters=50433, model_bytes=200)
        for evaluation in row['evaluations']:
            evaluation['initial_mismatch_count'] = 0
    states = [row for row in metrics if row['run_id'] == row['checkpoint'] == 0]
    supervision = dict(states=1680, legal_nodes=sum(row['legal_nodes'] for row in states),
        teacher_best_members=sum(row['best_set_size'] for row in states),
        best_set_size_counts={str(size): count for size, count in Counter(row['best_set_size'] for row in states).items()},
        tolerance=1e-9, target_dtype='float64', all_sets_nonempty=True, all_sets_legal=True, wall_seconds=.3)
    return metrics, manifest, training, supervision, old_metrics, old_manifest, old_collections, old_training


def test_ranking_pairing_excludes_logit_mse_and_charges_new_supervision_once():
    report = analysis.summarize(*fixture())
    assert report['integrity']['passed'] and report['valid_diagnostic']
    assert report['diagnostic_outcome'] == 'SUPERVISED_RANKING_LEARNED'
    assert report['retained_V49']['diagnostic_outcome'] == 'FIT_NOT_ESTABLISHED'
    assert report['integrity']['candidate']['initial_metric_records_exact'] == 5040
    assert report['integrity']['candidate']['recorded_batches_exact'] == 6000
    for split in ('train', 'heldout'):
        paired = report['paired_final_candidate_minus_V49'][split]
        assert set(paired) == {'mean_relative_regret', 'optimal_rate', 'pairwise_accuracy'}
        assert paired['mean_relative_regret']['run_values'] == pytest.approx([-.01, -.02, -.03])
        assert paired['optimal_rate']['run_values'] == [1., 1., 1.]
        assert paired['pairwise_accuracy']['run_values'] == [.125, .125, .125]
        radius = .01 * analysis.v44.T95_DF2 / 3 ** .5
        assert paired['mean_relative_regret']['ci_95'] == pytest.approx([-.02 - radius, -.02 + radius])
        assert paired['mean_relative_regret']['n_independent_training_runs'] == 3
    for row in report['summaries']:
        assert 'mse' not in row
        assert row['pairwise_accuracy'] == (.875 if row['checkpoint'] == 0 else 1.)
        if row['checkpoint'] == 2000:
            assert row['mean_best_set_probability'] == pytest.approx(.98)
            assert row['mean_best_set_nll'] == pytest.approx(-math.log(.98))
    new, old = report['accounting']['new_best_action'], report['accounting']['retained_V49']
    assert new['new_environment_samples'] == new['new_environment_calls'] == new['new_RL_training_updates'] == new['new_MCTS_calls'] == 0
    assert new['gradient_update_records'] == new['manifest_gradient_updates'] == 6000
    assert new['training_state_presentations_recorded'] == 24000
    assert new['evaluation_state_records'] == 10080 and new['initial_anchor_state_evaluations'] == 5040
    assert new['wall_seconds_by_stage']['supervision_preparation'] == .3
    assert sum(new['wall_seconds_by_stage'].values()) == pytest.approx(5.8)
    assert 'collection' not in new['wall_seconds_by_stage'] and 'dataset_serialization' not in new['wall_seconds_by_stage']
    assert old['collection_episodes_recorded'] == 24 and old['gradient_update_records'] == 6000
    assert new['added_parameters_per_model'] == 0


@pytest.mark.parametrize('failure', ['initial_drift', 'batch_reorder', 'heldout_batch', 'missing_metric',
                                   'set_size_changed', 'probability_nll', 'nonfinite_objective'])
def test_invalid_evidence_preserves_fees_without_outcome_or_paired_contrasts(failure):
    inputs = fixture()
    metrics, manifest, training, supervision = inputs[:4]
    if failure == 'initial_drift':
        metrics[0]['mse'] += 1e-10
    elif failure == 'batch_reorder':
        training[0]['batch_state_ids'].reverse()
    elif failure == 'heldout_batch':
        training[0]['batch_state_ids'][0] = 1120
    elif failure == 'missing_metric':
        metrics.pop(0)
    elif failure == 'set_size_changed':
        metrics[0]['best_set_size'] = 2  # Another run/checkpoint of this same state still has one.
    elif failure == 'probability_nll':
        metrics[-1]['best_set_probability'] = .5  # Finite but inconsistent with its NLL.
    else:
        metrics[-1]['best_set_nll'] = float('nan')
    report = analysis.summarize(*inputs)
    assert not report['integrity']['passed'] and not report['valid_diagnostic']
    assert report['diagnostic_outcome'] is None and report['paired_final_candidate_minus_V49'] is None
    if failure == 'set_size_changed':
        assert 'objective_state_consistency' in report['integrity']['candidate']['errors']
        assert 'supervision_summary' in report['integrity']['candidate']['errors']
    new = report['accounting']['new_best_action']
    assert new['evaluation_state_records'] == len(metrics)
    assert new['manifest_evaluation_states'] == 10080
    assert new['gradient_update_records'] == 6000 and new['training_state_presentations_recorded'] == 24000
    assert new['wall_seconds_by_stage']['supervised_training'] == 3.
    assert report['accounting']['retained_V49']['collection_episodes_recorded'] == 24
