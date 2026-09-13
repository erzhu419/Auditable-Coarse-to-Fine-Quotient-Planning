"""Three unequal budgets, all six execution orders and fresh paired streams."""

from collections import Counter
from itertools import permutations
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_transfer_runner_v32 import _fixture as metadata_fixture
from test_controlled_predictive_new_starts_v28 import ROOT, BOARD, A, B, PrefixProvider


CONFIGURATIONS = [{'name': 'GAP24', 'arm': 'GAP_FRONTIER', 'budget': 24},
                  {'name': 'CACHED24', 'arm': 'CACHED', 'budget': 24},
                  {'name': 'CACHED32', 'arm': 'CACHED', 'budget': 32}]


def _fixture(monkeypatch, tmp_path):
    cli32, initial_plan, *_ = metadata_fixture(monkeypatch, tmp_path)
    plan = json.loads(initial_plan.read_text())
    plan.pop('arms')
    plan.pop('requested_batches_per_arm')
    for context in plan['contexts']:
        context.pop('requested_batch_count')
    plan.update(configurations=CONFIGURATIONS, configuration_count=3,
        source_novelty_plans=[plan['source_plan']], seed_registry_reused_values=[],
        expected_triple_count=6, expected_run_count=18, expected_arm_count=18,
        replicate_count=3, expected_local_batches=480, expected_local_draws=122880,
        expected_physical_batches=512, expected_physical_draws=131072)
    plan['boards'][0].update(generation_seed=960001, prefix_seed=961001)
    plan['replicates'] = [{'replicate_index': i, 'base_seed': 962001 + i} for i in range(3)]
    plan['seed_bands'] = {'generation': [960001], 'prefix': [961001], 'suffix': [962001, 962002, 962003]}
    plan_path, prefixes, endpoints, output = (tmp_path / name for name in (
        'plan35.json', 'prefixes35.json.gz', 'endpoints35.jsonl.gz', 'result35.json.gz'))
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('v35_runner_test', scripts / 'run_controlled_predictive_budget_transfer_v35.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'generate_board', lambda seed: BOARD)
    providers, preparations, events, reads, writers = [], [], [], Counter(), {}
    original_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if mode == 'rt':
            reads[Path(path)] += 1
        if mode == 'xt':
            writers[Path(path)] = handle
        return handle
    monkeypatch.setattr(gzip, 'open', tracked_open)
    original_prepare = cli.prepare_query
    def prepare(*args):
        assert not providers and not events and len(PrefixProvider.calls) == 32
        state, accounting = original_prepare(*args)
        preparations.append(state)
        return state, accounting
    monkeypatch.setattr(cli, 'prepare_query', prepare)
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
    oracle = cli32.ExactOracle.from_closure(None)
    def closure(**kwargs):
        assert writers[endpoints].closed and len(providers) == 18
        events.append('oracle')
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    return cli, plan_path, prefixes, endpoints, output, providers, preparations, reads


def test_three_configurations_complete_own_budgets_and_cover_all_six_orders(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, providers, preparations, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_budget_transfer(plan, prefixes, endpoints, output)
    assert report['status'] == 'BUDGET_TRANSFER_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 3
    assert len(providers) == 18 and len(preparations) == 2 and len(PrefixProvider.calls) == 32
    assert reads == {endpoints: 1}
    account = report['accounting']
    assert account['local_configuration_run_count'] == 18 and account['local_physical_batches'] == 480
    assert account['prefix_physical_batches'] == 32 and account['total_physical_draws'] == 512 * 256
    assert account['frozen_policy_evaluation_calls'] == 18
    assert account['new_prefix_stream_count'] == 1 and account['new_suffix_stream_count'] == 3
    assert account['reused_prior_seed_count'] == 0
    assert account['historical_plus_new_physical_draws'] == account['historical_physical_draws'] + 512 * 256
    assert serialization['report_bytes'] > 0
    expected_orders = list(permutations([r['name'] for r in CONFIGURATIONS]))
    contexts = [row for rep in report['repetitions'] for row in rep['contexts']]
    assert [tuple(row['run_order']) for row in contexts] == expected_orders
    assert report['fixed_budget_complete_triple_count'] == 6
    for context in contexts:
        assert context['source_valid'] and context['fixed_budget_complete'] and context['complete']
        assert 'requested_batch_count' not in context and set(context['configurations']) == {'GAP24', 'CACHED24', 'CACHED32'}
        for config in CONFIGURATIONS:
            row = context['configurations'][config['name']]
            assert row['configuration'] == config and row['local']['arm'] == config['arm']
            assert row['local']['completed_batches'] == row['local']['requested_batch_count'] == config['budget']
            assert row['source_validation']['passed'] and row['first_action_validation']['passed']
            assert row['costs']['independent_query_seconds'] == sum(v for k, v in row['costs'].items() if k != 'independent_query_seconds')
            assert not any(key.startswith('reference_') for key in row)
    assert {name: counts['row_requests'] for name, counts in account['provider_counts_by_configuration'].items()} == {'GAP24': 144, 'CACHED24': 144, 'CACHED32': 192}


def test_normal_early_stop_retains_source_and_actual_costs_but_excludes_quality(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, *_ = _fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(cli.GapFrontierPlannerState, 'select_row', lambda *args: None)
    monkeypatch.setattr(cli.GapFrontierPlannerState, 'select_resample', lambda *args, **kwargs: None)
    report, _ = cli.run_budget_transfer(plan, prefixes, endpoints, output)
    assert report['source_valid_repetition_count'] == 3 and report['complete_repetition_count'] == 0
    assert report['accounting']['total_physical_batches'] == 32 + 6 * (24 + 32)
    for rep in report['repetitions']:
        for context in rep['contexts']:
            candidate = context['configurations']['GAP24']
            assert context['source_valid'] and not context['fixed_budget_complete']
            assert candidate['source_valid'] and candidate['local']['stop_reason'] == 'NO_ELIGIBLE_CANDIDATE'
            assert candidate['local']['actual_draws'] == 0 and not candidate['completed_requested_budget']
            assert candidate['costs']['independent_query_seconds'] > 0


def test_evaluation_failure_keeps_completed_three_configuration_cost_mask(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, *_ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def missing(record, *args):
        if record['state_type'] == 'GapFrontierPlannerState':
            raise ValueError('frozen policy unavailable')
        return evaluate(record, *args)
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', missing)
    report, _ = cli.run_budget_transfer(plan, prefixes, endpoints, output)
    assert report['source_valid_repetition_count'] == 3 and report['complete_repetition_count'] == 0
    assert report['accounting']['total_physical_draws'] == 512 * 256
    for rep in report['repetitions']:
        for context in rep['contexts']:
            assert context['source_valid'] and context['fixed_budget_complete'] and not context['complete']
            row = context['configurations']['GAP24']
            assert not row['evaluation_validation']['passed'] and row['costs']['independent_query_seconds'] > 0


@pytest.mark.parametrize('field', ['configuration', 'seed_registry'])
def test_configuration_or_frozen_seed_prerequisite_change_stops_before_sampling(monkeypatch, tmp_path, field):
    cli, plan_path, prefixes, endpoints, output, providers, *_ = _fixture(monkeypatch, tmp_path)
    plan = json.loads(plan_path.read_text())
    if field == 'configuration':
        plan['configurations'][0]['budget'] = 8
    else:
        plan['seed_registry_reused_values'] = [961001]
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match='binding differs before acquisition'):
        cli.run_budget_transfer(plan_path, prefixes, endpoints, output)
    assert providers == [] and PrefixProvider.calls == []
    assert not prefixes.exists() and not endpoints.exists() and not output.exists()
