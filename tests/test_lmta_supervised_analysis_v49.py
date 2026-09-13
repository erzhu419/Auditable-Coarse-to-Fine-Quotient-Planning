"""Fixed-size synthetic logs only; no tensor, environment or training imports."""
from copy import deepcopy
import importlib.util
import itertools
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location('lmta_supervised_analysis_v49',
    Path(__file__).resolve().parents[1] / 'scripts/analyze_lmta_supervised_v49.py')
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def fixture():
    collections = [dict(split=split, graph_id=graph, environment_seed=seed,
        state_count=70, raw_return=300., counters=dict(primitive_selections=70, day_transitions=10, propagation_draws=1000),
        label_calls=70, label_node_evaluations=35000, wall_seconds=.1)
        for split, graph, seed in analysis.GRAPH_BINDINGS]
    metrics = []
    for run, checkpoint, state in itertools.product(range(3), (0, 2000), range(1680)):
        split, graph = analysis.STATE_BINDINGS[state]
        good = checkpoint == 2000
        metrics.append(dict(run_id=run, checkpoint=checkpoint, split=split, graph_id=graph, state_id=state,
            day=(state % 70) // 7, remaining_budget=70 - state % 70, legal_nodes=500 - state % 70,
            mse=.001 if good else .1, predicted_node=499 if good else 1, teacher_node=499,
            best_score=2., chosen_score=2. if good else 1., score_regret=0. if good else 1.,
            relative_regret=0. if good else .5, optimal=good, predicted_q=1., teacher_q=1.,
            pairwise_correct=5. if state % 2 == 0 else 30., pairwise_pairs=10 if state % 2 == 0 else 30))
    training = [dict(run_id=run, step=step, batch_state_ids=[(step * 4 + offset) % 1120 for offset in range(4)], loss=.01)
                for run, step in itertools.product(range(3), range(1, 2001))]
    manifest = dict(schema='acfqp.lmta_supervised.v49', status='complete', protocol=deepcopy(analysis.FROZEN_PROTOCOL),
        runtime={'device': 'synthetic'}, graphs=[dict(split=split, graph_id=graph, nodes=500, edges=2000)
            for split, graph, _ in analysis.GRAPH_BINDINGS],
        runs=[dict(run_id=run, initialization_seed=493001 + run, batch_seed=494001 + run,
            gradient_steps=2000, training_state_presentations=8000, initialization_seconds=.1,
            training_seconds=1., evaluations=[dict(checkpoint=checkpoint, wall_seconds=.2, states=1680) for checkpoint in (0, 2000)],
            model_path=f'models/run{run}.pt', model_bytes=100, model_serialization_seconds=.1) for run in range(3)],
        graph_generation_seconds=.2, dataset_serialization_seconds=.3, tensor_preparation_seconds=.4,
        wall_seconds=10., dataset_bytes=1000, retained_history='reports/lmta_components_v48/analysis.json')
    return metrics, manifest, collections, training


def test_complete_fit_uses_each_run_and_pair_counts_and_charges_data_once():
    report = analysis.summarize(*fixture())
    assert report['integrity']['passed'] and report['valid_diagnostic']
    assert report['diagnostic_outcome'] == 'SUPERVISED_RANKING_LEARNED'
    assert len(report['summaries']) == 12
    for row in report['summaries']:
        assert row['state_records'] == (1120 if row['split'] == 'train' else 560)
        assert row['pairwise_accuracy'] == .875  # Not the .75 mean of per-state ratios.
    assert all(row['train']['passed'] and row['heldout']['passed'] for row in report['final_criteria_by_run'])
    costs = report['accounting']
    assert costs['collection_episodes_recorded'] == 24
    assert costs['teacher_states_recorded'] == costs['analytical_label_calls'] == 1680
    assert costs['analytical_label_node_evaluations'] == 840000
    assert costs['new_physical_counters']['primitive_selections'] == 1680
    assert costs['gradient_update_records'] == costs['manifest_gradient_updates'] == 6000
    assert costs['training_state_presentations_recorded'] == costs['manifest_training_state_presentations'] == 24000
    assert costs['evaluation_state_records'] == costs['manifest_evaluation_states'] == 10080
    assert costs['new_RL_training_updates'] == costs['new_MCTS_calls'] == 0
    assert costs['unitemized_runner_seconds'] == pytest.approx(1.9)


@pytest.mark.parametrize('split,outcome', [('train', 'FIT_NOT_ESTABLISHED'), ('heldout', 'GENERALIZATION_NOT_ESTABLISHED')])
def test_a_single_failed_run_prevents_the_corresponding_diagnostic_claim(split, outcome):
    inputs = fixture()
    targets = [row for row in inputs[0] if row['run_id'] == 1 and row['checkpoint'] == 2000 and row['split'] == split][:64]
    for row in targets:
        row.update(predicted_node=1, chosen_score=1., score_regret=1., relative_regret=.5, optimal=False)
    report = analysis.summarize(*inputs)
    assert report['integrity']['passed']
    assert report['diagnostic_outcome'] == outcome
    assert report['final_criteria_by_run'][1][split]['passed'] is False


@pytest.mark.parametrize('failure', ['heldout_batch', 'missing_metric', 'duplicate_metric', 'missing_step', 'nonfinite', 'wrong_graph'])
def test_invalid_logs_preserve_recorded_and_manifest_work_without_a_diagnostic(failure):
    metrics, manifest, collections, training = fixture()
    if failure == 'heldout_batch':
        training[0]['batch_state_ids'][0] = 1120
    elif failure == 'missing_metric':
        metrics.pop()
    elif failure == 'duplicate_metric':
        metrics.append(deepcopy(metrics[0]))
    elif failure == 'missing_step':
        training.pop()
    elif failure == 'nonfinite':
        metrics[0]['predicted_q'] = float('nan')
    else:
        metrics[0]['graph_id'] = 490900
    report = analysis.summarize(metrics, manifest, collections, training)
    assert not report['integrity']['passed'] and not report['valid_diagnostic']
    assert report['diagnostic_outcome'] is None and report['final_criteria_by_run'] is None
    costs = report['accounting']
    assert costs['gradient_update_records'] == len(training)
    assert costs['training_state_presentations_recorded'] == 4 * len(training)
    assert costs['evaluation_state_records'] == len(metrics)
    assert costs['manifest_gradient_updates'] == 6000
    assert costs['manifest_training_state_presentations'] == 24000
    assert costs['manifest_evaluation_states'] == 10080
    assert costs['wall_seconds_by_stage']['supervised_training'] == 3.
    assert costs['collection_episodes_recorded'] == 24
