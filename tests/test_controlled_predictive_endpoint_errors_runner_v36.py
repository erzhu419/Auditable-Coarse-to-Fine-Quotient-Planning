"""All endpoint attribution, unchanged source fees and exact signed references."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_budget_transfer_runner_v35 import _fixture as source_fixture
from test_controlled_predictive_new_starts_v28 import ROOT
from acfqp.science import controlled_predictive_sampling_v15 as sampling
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_frozen_policy_v27 import evaluate_frozen_policy
from acfqp.science.controlled_predictive_quotient_v1 import Query


def _fixture(monkeypatch, tmp_path, near_tie=False, corrupted=False):
    with monkeypatch.context() as source_patch:
        cli35, source_plan, prefixes, endpoints, source_result, *_ = source_fixture(source_patch, tmp_path)
        source, _ = cli35.run_budget_transfer(source_plan, prefixes, endpoints, source_result)
        oracle = cli35.ExactOracle.from_closure(None)
    source = json.loads(json.dumps(source))
    with gzip.open(endpoints, 'rt') as reader:
        full = [json.loads(line) for line in reader]
    if near_tie:
        rows = dict(oracle.rows)
        rows[ROOT, 'UP'] = tuple((p, successor, reward + 5e-11) for p, successor, reward in rows[ROOT, 'UP'])
        oracle = ExactOracle(oracle.statuses, rows)
        lookup = {(rep['replicate_index'], row['identity']['context_index']): row for rep in source['repetitions'] for row in rep['contexts']}
        for triple in full:
            original = lookup[triple['replicate_index'], triple['identity']['context_index']]
            for name, config in triple['configurations'].items():
                original['configurations'][name]['evaluation'] = evaluate_frozen_policy(config['state'], triple['target_key'], Query(**config['state']['query']), oracle)
        with gzip.open(source_result, 'wt') as writer:
            json.dump(source, writer)
    if corrupted:
        full[0]['configurations']['CACHED24']['state']['rows'][0]['integer_counts'][0]['count'] += 1
        with gzip.open(endpoints, 'wt') as writer:
            for row in full:
                writer.write(json.dumps(row) + '\n')
    retained_costs = {name: {'physical_draws': sum(row['configurations'][name]['local']['actual_draws'] for rep in source['repetitions'] for row in rep['contexts'])}
                      for name in ('GAP24', 'CACHED24', 'CACHED32')}
    source_analysis = tmp_path / 'analysis35.json'
    source_analysis.write_text(json.dumps({'all_analysis_checks_passed': True, 'accounting': source['accounting'],
                                          'all_actual_configuration_costs': retained_costs}))
    plan = {**source['plan'], 'source_plan': str(source_plan), 'source_endpoints': str(endpoints),
        'source_result': str(source_result), 'source_analysis': str(source_analysis),
        'compared_configurations': ['CACHED24', 'CACHED32'], 'modes': ['RAW', 'REMOVE_A', 'REMOVE_D'],
        'decomposition_tolerance': 1e-10, 'expected_pair_count': 6, 'expected_endpoint_count': 12,
        'expected_model_restores': 12, 'expected_policy_evaluations': 12, 'expected_local_evaluations': 12,
        'expected_action_decompositions': 48, 'expected_source_triples_read': 6,
        'source_historical_physical_batches': source['accounting']['historical_plus_new_physical_batches'],
        'source_historical_physical_draws': source['accounting']['historical_plus_new_physical_draws']}
    plan_path, output = tmp_path / 'plan36.json', tmp_path / 'result36.json.gz'
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('v36_runner_test', scripts / 'run_controlled_predictive_endpoint_errors_v36.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    reads = Counter()
    original_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        if mode == 'rt':
            reads[Path(path)] += 1
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(gzip, 'open', tracked_open)
    monkeypatch.setattr(cli, 'build_development_closure', lambda **kwargs: SimpleNamespace(counts={'toy': True}))
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    def forbidden(*args, **kwargs):
        pytest.fail('endpoint attribution must not construct a provider or acquire samples')
    monkeypatch.setattr(sampling.BatchRowSampleProvider, '__init__', forbidden)
    monkeypatch.setattr(sampling.BatchRowSampleProvider, 'sample_batch', forbidden)
    return cli, plan_path, output, source, retained_costs, reads


def test_all_cached_endpoints_decomposed_and_all_three_original_fees_preserved(monkeypatch, tmp_path):
    cli, plan, output, source, costs, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_endpoint_errors(plan, output)
    assert report['status'] == 'ENDPOINT_ERRORS_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 3
    assert all(value == 1 for value in reads.values())
    account = report['accounting']
    assert account['model_restore_calls'] == account['frozen_policy_evaluation_calls'] == account['local_decomposition_calls'] == 12
    assert account['action_decompositions'] == 48 and account['source_endpoint_triple_records_read'] == 6
    assert account['new_provider_calls'] == account['new_sampling_calls'] == account['new_physical_draws'] == 0
    assert account['historical_physical_draws'] == source['accounting']['historical_plus_new_physical_draws']
    assert report['original_all_actual_configuration_costs'] == costs and 'GAP24' in costs
    assert report['original_source_accounting'] == source['accounting'] and serialization['report_bytes'] > 0
    for rep, original_rep in zip(report['original_repetitions'], source['repetitions']):
        assert rep['source_valid'] == original_rep['source_valid'] and rep['complete'] == original_rep['complete']
        for row, old in zip(rep['contexts'], original_rep['contexts']):
            for name in ('GAP24', 'CACHED24', 'CACHED32'):
                assert row['configurations'][name]['costs'] == old['configurations'][name]['costs']
                assert row['configurations'][name]['evaluation'] == cli._compact_evaluation(old['configurations'][name]['evaluation'])
    for rep in report['repetitions']:
        for row in rep['contexts']:
            assert row['complete'] and set(row['configurations']) == {'CACHED24', 'CACHED32'}
            cross = row['cross_budget']
            assert cross['validation']['passed'] and cross['available']
            assert cross['actions'][0] == cross['actions'][1]
            assert all(value == 0 for value in cross['change'].values())
            for endpoint in row['configurations'].values():
                assert endpoint['restoration_validation']['passed'] and endpoint['value_reproduction_validation']['passed']
                assert set(endpoint['diagnostic']['actions']) == {'DOWN', 'LEFT', 'RIGHT', 'UP'}
                assert set(endpoint['diagnostic']['modes']) == {'RAW', 'REMOVE_A', 'REMOVE_D'}


def test_exact_reference_is_distinct_from_tolerance_optimal_lex_representative(monkeypatch, tmp_path):
    cli, plan, output, _, _, _ = _fixture(monkeypatch, tmp_path, near_tie=True)
    report, _ = cli.run_endpoint_errors(plan, output)
    assert report['status'] == 'ENDPOINT_ERRORS_COMPLETE'
    endpoint = report['repetitions'][0]['contexts'][0]['configurations']['CACHED24']
    diagnosis = endpoint['diagnostic']
    assert diagnosis['true_optimal_representative'] == 'DOWN'
    assert diagnosis['exact_reference_action'] == 'UP'
    assert diagnosis['selected_minus_reference']['actions'] == ['DOWN', 'UP']
    assert diagnosis['selected_minus_reference']['q_star_difference'] == -endpoint['local_evaluation']['local_regret'] < 0
    assert diagnosis['modes']['RAW']['wrong'] is False
    assert diagnosis['modes']['REMOVE_A']['selected_action'] == 'UP'


def test_bad_endpoint_counts_keep_failed_status_and_unchanged_original_gap_costs(monkeypatch, tmp_path):
    cli, plan, output, source, costs, _ = _fixture(monkeypatch, tmp_path, corrupted=True)
    report, _ = cli.run_endpoint_errors(plan, output)
    endpoint = report['repetitions'][0]['contexts'][0]['configurations']['CACHED24']
    assert not endpoint['source_valid'] and not endpoint['restoration_validation']['passed']
    assert sum(len(rep['contexts']) for rep in report['repetitions']) == 6
    assert report['accounting']['model_restore_calls'] == 12
    assert report['original_all_actual_configuration_costs'] == costs
    assert report['original_repetitions'][0]['contexts'][0]['configurations']['GAP24']['costs'] == source['repetitions'][0]['contexts'][0]['configurations']['GAP24']['costs']
    assert all(rep['complete'] for rep in report['original_repetitions'])


def test_unavailable_policy_value_keeps_empirical_source_and_original_masks(monkeypatch, tmp_path):
    cli, plan, output, _, costs, _ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def missing(record, *args):
        if record['spent_batches'] == 56:
            raise ValueError('full policy value unavailable')
        return evaluate(record, *args)
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', missing)
    report, _ = cli.run_endpoint_errors(plan, output)
    assert report['source_valid_repetition_count'] == 3 and report['complete_repetition_count'] == 0
    assert report['original_all_actual_configuration_costs'] == costs
    assert all(rep['complete'] for rep in report['original_repetitions'])
    for rep in report['repetitions']:
        for row in rep['contexts']:
            before = row['configurations']['CACHED24']
            assert before['source_valid'] and before['diagnostic_validation']['passed']
            assert not before['value_reproduction_validation']['passed']
