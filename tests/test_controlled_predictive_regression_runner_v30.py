"""Replay integrity, endpoint reproduction and signed changed-action errors."""

from collections import Counter
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_new_starts_runner_v28 import _setup
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_quotient_v1 import Query
from acfqp.science import controlled_predictive_sampling_v15 as sampling


def _fixture(monkeypatch, tmp_path, mutation=None):
    cli28, source_plan, prefixes, endpoints, source_result, *_ = _setup(monkeypatch, tmp_path)
    source, _ = cli28.run_new_starts(source_plan, prefixes, endpoints, source_result)
    source = json.loads(json.dumps(source))
    oracle = cli28.ExactOracle.from_closure(None)
    with gzip.open(prefixes, 'rt') as reader:
        retained = json.load(reader)
    with gzip.open(endpoints, 'rt') as reader:
        original_endpoints = [json.loads(line) for line in reader]
    context = source['plan']['contexts'][0]
    prefix = retained['query_starts'][0]
    baseline = {'context_index': 0, 'identity': prefix['identity'], 'source_valid': True,
        'evaluation': evaluate_frozen_policy(prefix['state'], context['target_key'],
                                            Query(**prefix['state']['query']), oracle)}
    prefix_result = tmp_path / 'prefix_result.json.gz'
    with gzip.open(prefix_result, 'wt') as writer:
        json.dump({'prefix_baselines': [baseline]}, writer)
    analysis = tmp_path / 'analysis29.json'
    analysis.write_text('{}')
    if mutation:
        mutation(original_endpoints)
        with gzip.open(endpoints, 'wt') as writer:
            for row in original_endpoints:
                writer.write(json.dumps(row) + '\n')
    plan = {**source['plan'], 'source_plan': str(source_plan), 'source_prefixes': str(prefixes),
        'source_endpoints': str(endpoints), 'source_result': str(source_result),
        'source_prefix_result': str(prefix_result), 'source_analysis': str(analysis),
        'context': context, 'board': source['plan']['boards'][0], 'requested_batches': 32,
        'expected_trajectories': 4, 'expected_boundaries_per_trajectory': 33,
        'tolerance': 1e-10, 'source_historical_physical_draws': source['accounting']['total_physical_draws'],
        'source_historical_physical_batches': source['accounting']['total_physical_batches']}
    plan_path, output = tmp_path / 'plan30.json', tmp_path / 'result30.json.gz'
    plan_path.write_text(json.dumps(plan))
    script = Path(__file__).resolve().parents[1] / 'scripts/run_controlled_predictive_regression_v30.py'
    spec = importlib.util.spec_from_file_location('v30_runner_test', script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    reads = Counter()
    old_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        if mode == 'rt':
            reads[Path(path)] += 1
        return old_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(gzip, 'open', tracked_open)
    def closure(**kwargs):
        assert reads[endpoints] == 1 and reads[prefixes] == 1
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    def forbidden(*args, **kwargs):
        pytest.fail('retained replay must never create or call a sample provider')
    monkeypatch.setattr(sampling.BatchRowSampleProvider, '__init__', forbidden)
    monkeypatch.setattr(sampling.BatchRowSampleProvider, 'sample_batch', forbidden)
    return cli, plan_path, output, source, original_endpoints, reads


def test_all_retained_batches_exactly_reproduce_both_arms_without_provider(monkeypatch, tmp_path):
    cli, plan, output, source, original, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_regression(plan, output)
    assert report['plan_binding_validation']['passed']
    assert report['status'] == 'REGRESSION_REPLAY_COMPLETE'
    assert report['complete_trajectory_count'] == len(report['trajectories']) == 4
    assert all(count == 1 for count in reads.values())
    assert serialization['report_bytes'] > 0
    account = report['accounting']
    assert account['retained_batches_replayed'] == 128
    assert account['retained_draws_replayed'] == 128 * 256
    assert account['new_provider_calls'] == account['new_physical_draws'] == 0
    assert account['source_endpoint_pair_records_read'] == 4
    assert account['source_endpoint_pair_records_selected'] == 2
    assert report['original_source_accounting'] == source['accounting']
    for row in report['trajectories']:
        assert all(row[k]['passed'] for k in ('source_validation', 'prefix_validation', 'chronology_validation', 'endpoint_validation'))
        assert len(row['boundaries']) == 33 and row['chronology_validation']['request_count'] == 32
        assert all(set(boundary['local_evaluation']['actions']) == {'DOWN', 'LEFT', 'RIGHT', 'UP'} for boundary in row['boundaries'])
        source_row = next(r for r in original if r['replicate_index'] == row['replicate_index'] and r['identity']['context_index'] == 0)['arms'][row['arm']]
        assert row['original_costs'] == source_row['costs']
        assert row['source_history'] == {field: source_row['local'][field] for field in cli.TRACE_FIELDS}


@pytest.mark.parametrize('corruption', ['batch_index', 'gap', 'endpoint_count'])
def test_reachable_source_mismatch_keeps_all_histories_and_original_costs(monkeypatch, tmp_path, corruption):
    def mutate(rows):
        row = rows[0]['arms']['CACHED']
        if corruption == 'batch_index':
            row['local']['observed_batches'][3]['batch_index'] += 1
        elif corruption == 'gap':
            row['local']['gap_assessments'][3]['separated'] = not row['local']['gap_assessments'][3]['separated']
        else:
            row['state']['rows'][0]['integer_counts'][0]['count'] += 1
    cli, plan, output, source, original, _ = _fixture(monkeypatch, tmp_path, mutate)
    report, _ = cli.run_regression(plan, output)
    assert len(report['trajectories']) == 4 and report['complete_trajectory_count'] == 3
    failed = report['trajectories'][0]
    assert failed['status'] == 'REPLAY_MISMATCH'
    assert failed['original_costs'] == original[0]['arms']['CACHED']['costs']
    assert failed['source_history']['observed_batches'] == original[0]['arms']['CACHED']['local']['observed_batches']
    if corruption == 'endpoint_count':
        assert len(failed['boundaries']) == 33 and not failed['endpoint_validation']['passed']
    else:
        assert len(failed['boundaries']) == 4 and not failed['chronology_validation']['passed']
    assert report['accounting']['historical_physical_draws'] == source['accounting']['total_physical_draws']


def test_changed_action_reference_is_fixed_on_both_sides_and_unknown_rows_stay_null():
    script = Path(__file__).resolve().parents[1] / 'scripts/run_controlled_predictive_regression_v30.py'
    spec = importlib.util.spec_from_file_location('v30_margin_test', script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    local = {'actions': {
        'DOWN': {'observed': True, 'q_hat': .8, 'q_star': 1., 'lower': .8, 'A_transition_error': .1, 'D_continuation_error': -.3},
        'UP': {'observed': True, 'q_hat': .7, 'q_star': .9, 'lower': .7, 'A_transition_error': -.1, 'D_continuation_error': -.1}},
        'selected_action': 'DOWN', 'local_true_optimal_actions': ['DOWN']}
    after = deepcopy(local)
    after['selected_action'] = 'UP'
    after['actions']['UP'].update(q_hat=.9, lower=.9, D_continuation_error=.1)
    trigger = cli._trigger({'boundary_index': 0}, {'boundary_index': 1}, local, after,
        {'row_key': [[2, [1]], 'UP'], 'kind': 'REPEAT_OBSERVATION'}, {}, (2, (1,)))
    assert trigger['before_margin']['q_hat_difference'] == pytest.approx(-.1)
    assert trigger['after_margin']['q_hat_difference'] == pytest.approx(.1)
    assert trigger['before_margin']['action'] == trigger['after_margin']['action'] == 'UP'
    assert abs(trigger['before_margin']['identity_residual']) < 1e-10
    local['actions']['UP']['observed'] = False
    margin = cli.signed_margin(local, 'UP', 'DOWN')
    assert margin['observed_both'] is False and margin['A_transition_error_difference'] is None
    assert margin['q_hat_difference'] is None and margin['identity_residual'] is None


def test_plan_mismatch_retains_every_status_and_charges_without_oracle(monkeypatch, tmp_path):
    cli, plan_path, output, source, original, _ = _fixture(monkeypatch, tmp_path)
    plan = json.loads(plan_path.read_text())
    plan['queries']['reward']['reward_weight'] += 1.
    plan_path.write_text(json.dumps(plan))
    def forbidden(**kwargs):
        pytest.fail('source-binding failure must not start evaluation')
    monkeypatch.setattr(cli, 'build_development_closure', forbidden)
    report, _ = cli.run_regression(plan_path, output)
    assert not report['plan_binding_validation']['passed']
    assert report['complete_trajectory_count'] == 0 and len(report['trajectories']) == 4
    for row in report['trajectories']:
        assert row['status'] == 'REPLAY_MISMATCH'
        assert all(not row[field]['passed'] for field in ('source_validation', 'prefix_validation', 'chronology_validation', 'endpoint_validation'))
        original_row = next(r for r in original if r['replicate_index'] == row['replicate_index'] and r['identity']['context_index'] == 0)['arms'][row['arm']]
        assert row['original_costs'] == original_row['costs']
        assert row['source_history']['observed_batches'] == original_row['local']['observed_batches']
    assert report['accounting']['historical_physical_draws'] == source['accounting']['total_physical_draws']
