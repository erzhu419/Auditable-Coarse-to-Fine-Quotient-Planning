"""Contemporaneous controls, immutable retained starts and paid repeated streams."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_controlled_predictive_new_starts_runner_v28 import _setup
from test_controlled_predictive_new_starts_v28 import ROOT, BOARD, A, B


def _fixture(monkeypatch, tmp_path, corrupt_reference=False):
    cli28, source_plan, prefixes, old_endpoints, source_output, *_ = _setup(monkeypatch, tmp_path)
    source, _ = cli28.run_new_starts(source_plan, prefixes, old_endpoints, source_output)
    source = json.loads(json.dumps(source))
    oracle = cli28.ExactOracle.from_closure(None)
    if corrupt_reference:
        with gzip.open(old_endpoints, 'rt') as reader:
            old = [json.loads(line) for line in reader]
        old[0]['arms']['CACHED']['local']['observed_batches'][0]['batch_index'] += 1
        with gzip.open(old_endpoints, 'wt') as writer:
            for row in old:
                writer.write(json.dumps(row) + '\n')
    plan = {**source['plan'], 'arms': ['CACHED', 'GAP_FRONTIER'],
        'source_plan': str(source_plan), 'source_prefixes': str(prefixes), 'source_endpoints': str(old_endpoints),
        'source_result': str(source_output), 'source_historical_physical_batches': source['accounting']['total_physical_batches'],
        'source_historical_physical_draws': source['accounting']['total_physical_draws'],
        'maximum_new_physical_batches': 8 * 32, 'maximum_new_physical_draws': 8 * 32 * 256}
    plan_path, endpoints, output = (tmp_path / n for n in ('plan31.json', 'endpoints31.jsonl.gz', 'result31.json.gz'))
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('v31_runner_test', scripts / 'run_controlled_predictive_gap_frontier_v31.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    events, providers, restorations, reads, writers = [], [], [], Counter(), {}
    old_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        handle = old_open(path, mode, *args, **kwargs)
        if mode == 'rt':
            reads[Path(path)] += 1
        if mode == 'xt':
            writers[Path(path)] = handle
        return handle
    monkeypatch.setattr(gzip, 'open', tracked_open)
    original_restore = cli.restore_state
    def restore(*args, **kwargs):
        assert not providers and not events
        state = original_restore(*args, **kwargs)
        restorations.append(state)
        return state
    monkeypatch.setattr(cli, 'restore_state', restore)
    class Provider:
        def __init__(self, seed):
            assert 'oracle' not in events and len(restorations) == 2
            self.seed, self.work_counts, self.provider_seconds = seed, Counter(), 0.
            providers.append(self)
        def sample_batch(self, key, action, index):
            assert 'oracle' not in events
            self.work_counts.update(row_requests=1, physical_draws=256)
            self.work_counts['first_batch_requests' if index == 0 else 'repeat_batch_requests'] += 1
            if key == ROOT:
                p = .25 if self.seed % 2 else .75
                return ((p, A, 0.), (1. - p, B, 0.))
            return ((1., (0, BOARD), .5 if action == 'RIGHT' else .125),)
    monkeypatch.setattr(cli, 'BatchRowSampleProvider', Provider)
    def closure(**kwargs):
        assert writers[endpoints].closed and len(providers) == 8
        assert reads[old_endpoints] == 0
        events.append('oracle')
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    return cli, plan_path, endpoints, output, source, providers, restorations, reads


def test_captured_prefixes_reset_once_and_fresh_control_exactly_reproduces(monkeypatch, tmp_path):
    cli, plan, endpoints, output, old, providers, restorations, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_gap_frontier(plan, endpoints, output)
    assert report['status'] == 'GAP_FRONTIER_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 2
    assert report['all_restorations_passed'] and len(restorations) == 2 and len(providers) == 8
    assert all(value == 1 for value in reads.values())
    account = report['accounting']
    assert account['prefix_restores'] == 2
    assert account['prefix_physical_draws'] == 0
    assert account['total_physical_batches'] == 256 and account['total_physical_draws'] == 256 * 256
    assert account['historical_physical_draws'] == old['accounting']['total_physical_draws']
    assert account['historical_plus_new_physical_draws'] == old['accounting']['total_physical_draws'] + 256 * 256
    assert account['provider_counts_by_arm']['CACHED']['physical_draws'] == 128 * 256
    assert account['frozen_policy_evaluation_calls'] == 8
    assert report['original_source_accounting'] == old['accounting']
    assert serialization['report_bytes'] > 0
    with gzip.open(endpoints, 'rt') as reader:
        pairs = [json.loads(line) for line in reader]
    assert [r['run_order'] for r in pairs] == [['CACHED', 'GAP_FRONTIER'], ['GAP_FRONTIER', 'CACHED'], ['GAP_FRONTIER', 'CACHED'], ['CACHED', 'GAP_FRONTIER']]
    for rep in report['repetitions']:
        for row in rep['contexts']:
            assert row['arms']['CACHED']['reference_validation']['passed']
            assert row['arms']['CACHED']['reference_value_validation']['passed']
            restore = report['restoration_records'][row['identity']['context_index']]['accounting']['whole_seconds']
            for arm in cli.ARMS:
                result = row['arms'][arm]
                assert result['costs']['prefix_restore_seconds'] == restore
                assert result['costs']['independent_query_seconds'] == sum(value for key, value in result['costs'].items() if key != 'independent_query_seconds')
                assert result['evaluation']['identities_pass'] and result['evaluation']['reach_probability_pass']
                assert not any(field in result['local'] for field in cli.TRACE_FIELDS)


def test_reference_mismatch_retains_all_paid_samples_and_comparison_rows(monkeypatch, tmp_path):
    cli, plan, endpoints, output, old, *_ = _fixture(monkeypatch, tmp_path, corrupt_reference=True)
    report, _ = cli.run_gap_frontier(plan, endpoints, output)
    assert report['status'] == 'GAP_FRONTIER_WITH_ISSUES'
    bad = report['repetitions'][0]['contexts'][0]
    assert not bad['source_valid'] and not bad['paired_complete']
    assert not bad['arms']['CACHED']['reference_validation']['passed']
    assert set(bad['arms']) == {'CACHED', 'GAP_FRONTIER'}
    assert all(row['local']['actual_draws'] == 32 * 256 and row['costs']['independent_query_seconds'] > 0 for row in bad['arms'].values())
    assert report['accounting']['total_physical_draws'] == 256 * 256
    assert sum(len(rep['contexts']) for rep in report['repetitions']) == 4


def test_unequal_normal_stop_retains_source_validity_and_actual_costs(monkeypatch, tmp_path):
    cli, plan, endpoints, output, _, *_ = _fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.GapFrontierPlannerState, 'select_row', lambda *args: None)
    monkeypatch.setattr(cli.GapFrontierPlannerState, 'select_resample', lambda *args, **kwargs: None)
    report, _ = cli.run_gap_frontier(plan, endpoints, output)
    assert report['source_valid_repetition_count'] == 2 and report['complete_repetition_count'] == 0
    assert report['budget_counts']['unequal_budget_pair'] == 4
    for rep in report['repetitions']:
        for row in rep['contexts']:
            arm = row['arms']['GAP_FRONTIER']
            assert row['source_valid'] and not row['budget_matched']
            assert arm['local']['actual_draws'] == 0 and arm['local']['stop_reason'] == 'NO_ELIGIBLE_CANDIDATE'
            assert arm['costs']['independent_query_seconds'] > 0
    assert report['accounting']['total_physical_draws'] == 128 * 256


def test_changed_frozen_plan_stops_before_provider_or_output(monkeypatch, tmp_path):
    cli, plan_path, endpoints, output, _, providers, *_ = _fixture(monkeypatch, tmp_path)
    plan = json.loads(plan_path.read_text())
    plan['queries']['reward']['reward_weight'] += 1.
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match='binding differs before sampling'):
        cli.run_gap_frontier(plan_path, endpoints, output)
    assert providers == [] and not endpoints.exists() and not output.exists()


def test_evaluator_failure_keeps_source_and_cost_mask_but_excludes_quality(monkeypatch, tmp_path):
    cli, plan, endpoints, output, _, *_ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def fail_cached(record, *args):
        if record['state_type'] == 'CachedGapPlannerState':
            raise ValueError('retained policy evaluation unavailable')
        return evaluate(record, *args)
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', fail_cached)
    report, _ = cli.run_gap_frontier(plan, endpoints, output)
    assert report['source_valid_repetition_count'] == 2 and report['complete_repetition_count'] == 0
    assert report['accounting']['total_physical_draws'] == 256 * 256
    for rep in report['repetitions']:
        for row in rep['contexts']:
            arm = row['arms']['CACHED']
            assert row['source_valid'] and not row['paired_complete']
            assert arm['source_valid'] and arm['reference_validation']['passed']
            assert not arm['reference_value_validation']['passed'] and not arm['evaluation_validation']['passed']
            assert arm['local']['actual_draws'] == 32 * 256 and arm['costs']['independent_query_seconds'] > 0
