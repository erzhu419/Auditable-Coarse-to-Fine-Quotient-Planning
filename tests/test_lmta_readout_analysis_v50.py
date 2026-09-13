"""Synthetic paired V49/V50 logs; no tensor or environment imports."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load_module('lmta_readout_analysis_v50', ROOT / 'scripts/analyze_lmta_readout_v50.py')
source_fixture = load_module('lmta_v49_fixture', ROOT / 'tests/test_lmta_supervised_analysis_v49.py')


def fixture():
    old_metrics, old_manifest, old_collections, old_training = source_fixture.fixture()
    for row in old_metrics:
        if row['checkpoint'] == 2000:
            chosen = 2. - .02 * (row['run_id'] + 1)
            gap = 2. - chosen
            row.update(chosen_score=chosen, score_regret=gap, relative_regret=gap / 2.,
                       optimal=False, predicted_node=1, mse=.1)
    metrics, training, manifest = deepcopy(old_metrics), deepcopy(old_training), deepcopy(old_manifest)
    for row in metrics:
        if row['checkpoint'] == 2000:
            row.update(predicted_node=499, chosen_score=2., score_regret=0., relative_regret=0., optimal=True,
                       mse=.001, pairwise_correct=float(row['pairwise_pairs']), predicted_q=2., teacher_q=2.)
    manifest.update(schema='acfqp.lmta_readout.v50', protocol=deepcopy(analysis.FROZEN_PROTOCOL),
        source_directory='reports/lmta_supervised_v49', dataset_path='reports/lmta_supervised_v49/dataset.npz',
        initial_anchors_complete=True, information_passed=True, source_read_seconds=.1,
        information_check_seconds=.3, new_environment_calls=0, new_RL_training_updates=0, new_MCTS_calls=0)
    del manifest['dataset_serialization_seconds']
    for row in manifest['runs']:
        row.update(base_parameters=50433, candidate_parameters=50439, model_bytes=200,
                   learned_message_weight=[.1] * 5, learned_message_bias=-.1)
        for evaluation in row['evaluations']:
            evaluation['initial_mismatch_count'] = 0
    legal = Counter()
    for row in old_metrics:
        if row['run_id'] == row['checkpoint'] == 0:
            legal[row['graph_id']] += row['legal_nodes']
    information = dict(passed=True, states=1680, legal_nodes=sum(legal.values()),
        max_abs_error_float64=1e-15, max_abs_error_float32=1e-7, wall_seconds=.3,
        by_graph=[dict(graph_id=graph, states=70, legal_nodes=count, max_abs_error_float64=1e-15,
                       max_abs_error_float32=1e-7) for graph, count in legal.items()])
    return metrics, manifest, training, information, old_metrics, old_manifest, old_collections, old_training


def test_exact_initial_and_batches_with_paired_directions_and_no_new_collection_fee():
    report = analysis.summarize(*fixture())
    assert report['integrity']['passed'] and report['valid_diagnostic']
    assert report['diagnostic_outcome'] == 'SUPERVISED_RANKING_LEARNED'
    assert report['retained_V49']['diagnostic_outcome'] == 'FIT_NOT_ESTABLISHED'
    assert report['integrity']['candidate']['initial_metric_records_exact'] == 5040
    assert report['integrity']['candidate']['recorded_batches_exact'] == 6000
    for split in ('train', 'heldout'):
        paired = report['paired_final_candidate_minus_V49'][split]
        assert paired['mean_relative_regret']['run_values'] == pytest.approx([-.01, -.02, -.03])
        assert paired['optimal_rate']['run_values'] == [1., 1., 1.]
        assert paired['pairwise_accuracy']['run_values'] == [.125, .125, .125]
        assert paired['mse']['run_values'] == pytest.approx([-.099] * 3)
        radius = .01 * analysis.v44.T95_DF2 / 3 ** .5
        assert paired['mean_relative_regret']['ci_95'] == pytest.approx([-.02 - radius, -.02 + radius])
        assert paired['mean_relative_regret']['n_independent_training_runs'] == 3
    new, old = report['accounting']['new_readout'], report['accounting']['retained_V49']
    assert new['new_environment_samples'] == new['new_environment_calls'] == new['new_RL_training_updates'] == new['new_MCTS_calls'] == 0
    assert new['gradient_update_records'] == new['manifest_gradient_updates'] == 6000
    assert new['training_state_presentations_recorded'] == 24000
    assert new['evaluation_state_records'] == 10080 and new['initial_anchor_state_evaluations'] == 5040
    assert 'collection' not in new['wall_seconds_by_stage'] and 'dataset_serialization' not in new['wall_seconds_by_stage']
    assert old['collection_episodes_recorded'] == 24 and old['gradient_update_records'] == 6000
    assert new['new_model_bytes'] == 600 and old['model_bytes'] == 300


@pytest.mark.parametrize('failure', ['initial_drift', 'batch_reorder', 'heldout_batch', 'missing_metric',
                                   'duplicate_metric', 'information', 'parameter_count'])
def test_invalid_paired_evidence_retains_costs_but_has_null_outcome_and_contrasts(failure):
    inputs = fixture()
    metrics, manifest, training, information = inputs[:4]
    if failure == 'initial_drift':
        metrics[0]['mse'] += 1e-10
    elif failure == 'batch_reorder':
        training[0]['batch_state_ids'].reverse()
    elif failure == 'heldout_batch':
        training[0]['batch_state_ids'][0] = 1120
    elif failure == 'missing_metric':
        metrics.pop(0)
    elif failure == 'duplicate_metric':
        metrics.append(deepcopy(metrics[-1]))
    elif failure == 'information':
        information['max_abs_error_float32'] = 3e-6  # A claimed passed flag is insufficient.
    else:
        manifest['runs'][0]['candidate_parameters'] = 50445
    report = analysis.summarize(*inputs)
    assert not report['integrity']['passed'] and not report['valid_diagnostic']
    assert report['diagnostic_outcome'] is None
    assert report['paired_final_candidate_minus_V49'] is None
    new = report['accounting']['new_readout']
    assert new['evaluation_state_records'] == len(metrics)
    assert new['manifest_evaluation_states'] == 10080
    assert new['gradient_update_records'] == 6000 and new['training_state_presentations_recorded'] == 24000
    assert new['wall_seconds_by_stage']['supervised_training'] == 3.
    assert report['accounting']['retained_V49']['collection_episodes_recorded'] == 24
