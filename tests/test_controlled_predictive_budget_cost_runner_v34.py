"""Actual rerun work at each budget, fixed order, and retained semantic controls."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_budget_curve_runner_v33 import _fixture as curve_fixture
from test_controlled_predictive_new_starts_v28 import ROOT, BOARD, A, B, PrefixProvider
from acfqp.science import controlled_predictive_new_starts_v28 as prefix_core
from acfqp.science import controlled_predictive_restore_v22 as restoration


def _fixture(monkeypatch, tmp_path):
    with monkeypatch.context() as source_patch:
        cli33, curve_plan, curve_policies, curve_output, original, old_endpoints, _, oracle = curve_fixture(source_patch, tmp_path)
        curve, _ = cli33.run_budget_curve(curve_plan, curve_policies, curve_output)
    curve_plan_data = json.loads(curve_plan.read_text())
    plan = {**original['plan'], 'source_plan': curve_plan_data['source_plan'],
        'source_prefixes': curve_plan_data['source_prefixes'], 'source_endpoints': str(old_endpoints),
        'source_result': curve_plan_data['source_result'], 'source_curve_plan': str(curve_plan),
        'source_curve_result': str(curve_output), 'source_curve_policies': str(curve_policies),
        'budgets': [4, 8, 16, 24, 32], 'budget_count': 5, 'expected_context_stream_count': 4,
        'expected_pair_count': 20, 'expected_arm_count': 40,
        'expected_prefix_acquisitions': 1, 'expected_query_preparations': 2,
        'expected_prefix_batches': 32, 'expected_prefix_draws': 8192,
        'expected_local_batches': 672, 'expected_local_draws': 172032,
        'expected_physical_batches': 704, 'expected_physical_draws': 180224,
        'source_historical_physical_batches': curve_plan_data['source_historical_physical_batches'],
        'source_historical_physical_draws': curve_plan_data['source_historical_physical_draws']}
    source_analysis = tmp_path / 'analysis33.json'
    source_analysis.write_text(json.dumps({'all_analysis_checks_passed': True, 'accounting': curve['accounting']}))
    plan['source_analysis'] = str(source_analysis)
    plan_path, prefixes, endpoints, output = (tmp_path / name for name in (
        'plan34.json', 'prefixes34.json.gz', 'endpoints34.jsonl.gz', 'result34.json.gz'))
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('v34_runner_test', scripts / 'run_controlled_predictive_budget_cost_v34.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    providers, preparations, events, reads, writers = [], [], [], Counter(), {}
    PrefixProvider.calls = []
    monkeypatch.setattr(prefix_core, 'BatchRowSampleProvider', PrefixProvider)
    original_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if mode == 'rt':
            reads[Path(path)] += 1
        if mode == 'xt':
            writers[Path(path)] = handle
        return handle
    monkeypatch.setattr(gzip, 'open', tracked_open)
    prepare = cli.prepare_query
    def prepare_once(*args):
        assert not providers and not events and len(PrefixProvider.calls) == 32
        state, account = prepare(*args)
        preparations.append(state)
        return state, account
    monkeypatch.setattr(cli, 'prepare_query', prepare_once)
    class Provider:
        def __init__(self, seed):
            assert not events and len(preparations) == 2 and writers[prefixes].closed
            self.seed, self.work_counts, self.provider_seconds = seed, Counter(), 0.
            providers.append(self)
        def sample_batch(self, key, action, index):
            assert not events
            self.work_counts.update(row_requests=1, physical_draws=256)
            self.work_counts['first_batch_requests' if index == 0 else 'repeat_batch_requests'] += 1
            if key == ROOT:
                p = .25 if self.seed % 2 else .75
                return ((p, A, 0.), (1. - p, B, 0.))
            return ((1., (0, BOARD), .5 if action == 'RIGHT' else .125),)
    monkeypatch.setattr(cli, 'BatchRowSampleProvider', Provider)
    original_read = cli._read
    truth_paths = {Path(plan[k]) for k in ('source_result', 'source_curve_result', 'source_analysis')}
    def read(path):
        if Path(path) in truth_paths:
            assert writers[endpoints].closed and len(providers) == 40
            assert sum(row.work_counts['row_requests'] for row in providers) == 672
        return original_read(path)
    monkeypatch.setattr(cli, '_read', read)
    def closure(**kwargs):
        assert writers[endpoints].closed and len(providers) == 40
        events.append('oracle')
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    def forbidden(*args, **kwargs):
        pytest.fail('contemporary budget timing must not restore an old model')
    monkeypatch.setattr(restoration, 'restore_state', forbidden)
    return cli, plan_path, prefixes, endpoints, output, original, curve, providers, reads


def test_all_budgets_reacquire_prefix_and_local_work_with_exact_frozen_controls(monkeypatch, tmp_path):
    cli, plan_path, prefixes, endpoints, output, original, curve, providers, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_budget_cost(plan_path, prefixes, endpoints, output)
    assert report['status'] == 'BUDGET_COST_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 2
    assert all(value == 1 for value in reads.values())
    account = report['accounting']
    assert len(PrefixProvider.calls) == account['prefix_physical_batches'] == 32
    assert len(providers) == account['local_arm_run_count'] == 40
    assert account['local_physical_batches'] == 672 and account['total_physical_draws'] == 704 * 256
    assert account['independent_new_samples'] == 0
    assert account['frozen_policy_evaluation_calls'] == 40
    assert account['historical_plus_new_physical_draws'] == curve['accounting']['historical_physical_draws'] + 704 * 256
    assert report['original_source_accounting'] == original['accounting']
    assert report['source_diagnostic_accounting'] == curve['accounting']
    assert serialization['report_bytes'] > 0
    with gzip.open(endpoints, 'rt') as reader:
        full = [json.loads(line) for line in reader]
    assert len(full) == 20
    cursor = 0
    for rep in report['repetitions']:
        for context in rep['contexts']:
            canonical = [4, 8, 16, 24, 32]
            offset = (rep['replicate_index'] + context['identity']['context_index']) % 5
            order = canonical[offset:] + canonical[:offset]
            assert context['budget_run_order'] == order
            assert [r['budget'] for r in full[cursor:cursor + 5]] == order
            cursor += 5
            assert [r['budget'] for r in context['budgets']] == canonical
            for run in context['budgets']:
                arm_order = ['CACHED', 'GAP_FRONTIER']
                if (rep['replicate_index'] + context['identity']['context_index'] + canonical.index(run['budget'])) % 2:
                    arm_order.reverse()
                assert run['run_order'] == arm_order
                for row in run['arms'].values():
                    assert all(row[k]['passed'] for k in ('source_validation', 'reference_history_validation', 'reference_policy_validation', 'reference_value_validation'))
                    assert row['local']['actual_draws'] == 256 * run['budget']
                    assert row['costs']['independent_query_seconds'] == sum(v for k, v in row['costs'].items() if k != 'independent_query_seconds')
                    assert 'prefix_restore_seconds' not in row['costs']
                    if run['budget'] == 32:
                        assert row['reference_state_validation']['passed']
                    else:
                        assert 'reference_state_validation' not in row


def test_missing_value_at_one_budget_preserves_all_paid_source_costs(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, _, _, _, _ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def missing(record, *args):
        if record['spent_batches'] == 36:
            raise ValueError('policy evaluation unavailable')
        return evaluate(record, *args)
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', missing)
    report, _ = cli.run_budget_cost(plan, prefixes, endpoints, output)
    assert report['source_valid_repetition_count'] == 2 and report['complete_repetition_count'] == 0
    assert report['accounting']['total_physical_draws'] == 704 * 256
    for rep in report['repetitions']:
        for context in rep['contexts']:
            first = context['budgets'][0]
            assert first['source_valid'] and not first['paired_complete']
            assert all(not row['evaluation_validation']['passed'] and row['costs']['independent_query_seconds'] > 0 for row in first['arms'].values())
            assert all(run['paired_complete'] for run in context['budgets'][1:])


def test_reference_history_mismatch_retains_all_current_runs_and_costs(monkeypatch, tmp_path):
    cli, plan_path, prefixes, endpoints, output, *_ = _fixture(monkeypatch, tmp_path)
    source_path = json.loads(plan_path.read_text())['source_endpoints']
    with gzip.open(source_path, 'rt') as reader:
        old = [json.loads(line) for line in reader]
    old[0]['arms']['CACHED']['local']['observed_batches'][3]['batch_index'] += 1
    with gzip.open(source_path, 'wt') as writer:
        for row in old:
            writer.write(json.dumps(row) + '\n')
    report, _ = cli.run_budget_cost(plan_path, prefixes, endpoints, output)
    assert report['status'] == 'BUDGET_COST_WITH_ISSUES'
    assert report['accounting']['total_physical_draws'] == 704 * 256
    for run in report['repetitions'][0]['contexts'][0]['budgets']:
        row = run['arms']['CACHED']
        assert not row['source_valid'] and not row['reference_history_validation']['passed']
        assert row['local']['actual_draws'] == run['budget'] * 256 and row['costs']['independent_query_seconds'] > 0


def test_prefix_mismatch_keeps_paid_prefix_artifact_and_stops_before_local(monkeypatch, tmp_path):
    cli, plan_path, prefixes, endpoints, output, _, _, providers, _ = _fixture(monkeypatch, tmp_path)
    source_path = json.loads(plan_path.read_text())['source_prefixes']
    with gzip.open(source_path, 'rt') as reader:
        old = json.load(reader)
    old['prefixes'][0]['batches'][0]['batch_index'] += 1
    with gzip.open(source_path, 'wt') as writer:
        json.dump(old, writer)
    with pytest.raises(ValueError, match='physical prefix work is retained'):
        cli.run_budget_cost(plan_path, prefixes, endpoints, output)
    assert providers == [] and not endpoints.exists() and not output.exists()
    with gzip.open(prefixes, 'rt') as reader:
        evidence = json.load(reader)
    assert evidence['prefixes'][0]['accounting']['physical_draws'] == 32 * 256
    assert not evidence['prefixes'][0]['validation']['passed']
