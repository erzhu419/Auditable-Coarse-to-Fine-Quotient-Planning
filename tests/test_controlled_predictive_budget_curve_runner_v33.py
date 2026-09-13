"""Retained budget prefixes, exact terminal replay and zero new provider calls."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_transfer_runner_v32 import _fixture as source_fixture
from acfqp.science import controlled_predictive_sampling_v15 as sampling
from acfqp.science.controlled_predictive_quotient_v1 import Query


def _fixture(monkeypatch, tmp_path, corruption=None):
    with monkeypatch.context() as source_patch:
        cli32, source_plan, prefixes, source_endpoints, source_result, *_ = source_fixture(source_patch, tmp_path)
        source, _ = cli32.run_transfer(source_plan, prefixes, source_endpoints, source_result)
        oracle = cli32.ExactOracle.from_closure(None)
    source = json.loads(json.dumps(source))
    if corruption:
        with gzip.open(source_endpoints, 'rt') as reader:
            endpoints = [json.loads(line) for line in reader]
        if corruption == 'batch':
            endpoints[0]['arms']['CACHED']['local']['observed_batches'][3]['batch_index'] += 1
        else:
            endpoints[0]['arms']['CACHED']['state']['rows'][0]['integer_counts'][0]['count'] += 1
        with gzip.open(source_endpoints, 'wt') as writer:
            for row in endpoints:
                writer.write(json.dumps(row) + '\n')
    source_analysis = tmp_path / 'source_analysis32.json'
    source_analysis.write_text(json.dumps({'all_analysis_checks_passed': True, 'accounting': source['accounting']}))
    account = source['accounting']
    plan = {**source['plan'], 'source_plan': str(source_plan), 'source_prefixes': str(prefixes),
        'source_endpoints': str(source_endpoints), 'source_result': str(source_result), 'source_analysis': str(source_analysis),
        'checkpoints': [0, 4, 8, 16, 24, 32], 'expected_prefix_evaluations': 2, 'expected_model_restores': 2,
        'expected_evaluation_count': 42, 'expected_checkpoint_reference_count': 48,
        'expected_retained_batches_replayed': 256, 'expected_retained_draws_replayed': 65536,
        'source_historical_physical_batches': account['historical_physical_batches'] + account['total_physical_batches'],
        'source_historical_physical_draws': account['historical_physical_draws'] + account['total_physical_draws']}
    plan_path, policies, output = (tmp_path / name for name in ('plan33.json', 'policies33.jsonl.gz', 'result33.json.gz'))
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('v33_runner_test', scripts / 'run_controlled_predictive_budget_curve_v33.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    reads, restorations = Counter(), []
    original_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        if mode == 'rt':
            reads[Path(path)] += 1
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(gzip, 'open', tracked_open)
    original_restore = cli.restore_state
    def restore(*args, **kwargs):
        state = original_restore(*args, **kwargs)
        restorations.append(state)
        return state
    monkeypatch.setattr(cli, 'restore_state', restore)
    def closure(**kwargs):
        assert len(restorations) == 2
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    def forbidden(*args, **kwargs):
        pytest.fail('budget curve must not create a sample provider or acquire samples')
    monkeypatch.setattr(sampling.BatchRowSampleProvider, '__init__', forbidden)
    monkeypatch.setattr(sampling.BatchRowSampleProvider, 'sample_batch', forbidden)
    return cli, plan_path, policies, output, source, source_endpoints, reads, oracle


def test_checkpoint_replay_matches_final_state_values_and_reconstructible_policy(monkeypatch, tmp_path):
    cli, plan, policies, output, source, source_endpoints, reads, oracle = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_budget_curve(plan, policies, output)
    assert report['status'] == 'BUDGET_CURVE_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 2
    assert all(value == 1 for value in reads.values())
    account = report['accounting']
    assert account['prefix_restores'] == account['prefix_policy_evaluation_calls'] == 2
    assert account['checkpoint_policy_evaluation_calls'] == 40 and account['policy_evaluation_calls'] == 42
    assert account['retained_batches_replayed'] == 256 and account['retained_draws_replayed'] == 65536
    assert account['new_provider_calls'] == account['new_sampling_calls'] == account['new_physical_draws'] == 0
    assert account['historical_physical_draws'] == source['accounting']['historical_plus_new_physical_draws']
    assert account['source_endpoint_pair_records_read'] == account['policy_pair_records_written'] == 4
    assert report['original_source_accounting'] == source['accounting'] and serialization['report_bytes'] > 0
    for rep, original_rep in zip(report['repetitions'], source['repetitions']):
        for context, original_context in zip(rep['contexts'], original_rep['contexts']):
            for arm, row in context['arms'].items():
                assert all(row[field]['passed'] for field in ('source_validation', 'prefix_validation', 'chronology_validation', 'endpoint_validation', 'reference_value_validation'))
                assert [cp['budget'] for cp in row['checkpoints']] == [0, 4, 8, 16, 24, 32]
                assert row['original_costs'] == original_context['arms'][arm]['costs']
                assert row['checkpoints'][0]['policy_record_reference'] == {'prefix_context_index': context['identity']['context_index']}
    with gzip.open(policies, 'rt') as reader:
        policy_pair = json.loads(reader.readline())
    with gzip.open(source_endpoints, 'rt') as reader:
        endpoint = json.loads(reader.readline())
    for arm in ('CACHED', 'GAP_FRONTIER'):
        archived = policy_pair['arms'][arm][0]
        assert archived['budget'] == 4 and 'rows' not in archived and 'integer_counts' not in archived
        keys = {tuple((p['key'][0], tuple(p['key'][1]))) for p in archived['policy_and_intervals']}
        original = endpoint['arms'][arm]['state']
        reconstructed = {'query': original['query'], 'profiles': [p for p in original['profiles'] if (p['key'][0], tuple(p['key'][1])) in keys],
            'policy_and_intervals': archived['policy_and_intervals'], 'rows': [{'row_key': key} for key in archived['observed_row_keys']]}
        evaluation = cli.evaluate_frozen_policy(reconstructed, endpoint['target_key'], Query(**original['query']), oracle)
        expected = report['repetitions'][0]['contexts'][0]['arms'][arm]['checkpoints'][1]['evaluation']
        assert cli._compact_evaluation(evaluation) == expected


@pytest.mark.parametrize('corruption', ['batch', 'endpoint_counts'])
def test_bad_retained_data_keeps_all_rows_and_original_full_budget_costs(monkeypatch, tmp_path, corruption):
    cli, plan, policies, output, source, *_ = _fixture(monkeypatch, tmp_path, corruption)
    report, _ = cli.run_budget_curve(plan, policies, output)
    row = report['repetitions'][0]['contexts'][0]['arms']['CACHED']
    assert not row['source_valid'] and len(row['checkpoints']) == 6
    assert row['original_costs'] == source['repetitions'][0]['contexts'][0]['arms']['CACHED']['costs']
    assert sum(len(rep['contexts']) for rep in report['repetitions']) == 4
    assert report['accounting']['historical_physical_draws'] == source['accounting']['historical_plus_new_physical_draws']
    if corruption == 'batch':
        assert not row['chronology_validation']['passed']
        assert not row['checkpoints'][1]['evaluation_validation']['passed']
    else:
        assert row['chronology_validation']['passed'] and not row['endpoint_validation']['passed']
        assert row['reference_value_validation']['passed']


def test_unavailable_middle_checkpoint_preserves_source_cost_and_endpoint_reproduction(monkeypatch, tmp_path):
    cli, plan, policies, output, source, *_ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def missing(record, *args):
        if record['spent_batches'] == 36:
            raise ValueError('checkpoint policy unavailable')
        return evaluate(record, *args)
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', missing)
    report, _ = cli.run_budget_curve(plan, policies, output)
    assert report['source_valid_repetition_count'] == 2 and report['complete_repetition_count'] == 0
    assert report['accounting']['retained_batches_replayed'] == 256
    for rep in report['repetitions']:
        for context in rep['contexts']:
            for row in context['arms'].values():
                assert row['source_valid'] and row['reference_value_validation']['passed']
                assert not row['checkpoints'][1]['evaluation_validation']['passed']
                assert row['checkpoints'][-1]['policy_evaluable'] and row['original_costs']['independent_query_seconds'] > 0
