"""Fresh acquisition timing, frozen method binding and complete physical costs."""

from collections import Counter
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_new_starts_runner_v28 import _setup
from test_controlled_predictive_new_starts_v28 import ROOT, BOARD, A, B, PrefixProvider
from acfqp.science import controlled_predictive_restore_v22 as restoration


def _fixture(monkeypatch, tmp_path):
    cli28, original_plan, *_ = _setup(monkeypatch, tmp_path)
    original = json.loads(original_plan.read_text())
    original.update(arms=['CACHED', 'GAP_FRONTIER'], selection_rule={'frozen': 'gap-frontier-v31'}, total_path_batch_cap=128)
    original['boards'][0]['board'][0] += 1
    original_plan.write_text(json.dumps(original))
    historical = {'historical_physical_batches': 100, 'total_physical_batches': 200,
                  'historical_physical_draws': 25600, 'total_physical_draws': 51200}
    source_analysis = tmp_path / 'source_analysis.json'
    source_analysis.write_text(json.dumps({'all_analysis_checks_passed': True, 'accounting': historical}))
    plan = deepcopy(original)
    plan.update(source_plan=str(original_plan), source_analysis=str(source_analysis),
        source_historical_physical_batches=300, source_historical_physical_draws=76800,
        expected_prefix_batches=32, expected_prefix_draws=8192, maximum_local_batches=256,
        maximum_local_draws=65536, maximum_physical_batches=288, maximum_physical_draws=73728,
        expected_prefix_acquisitions=1, expected_query_preparations=2, model_restores=0,
        cohort_prerequisites={"all_new_registered_root_or_target_orbits": True})
    plan['boards'][0].update(board=list(BOARD), generation_seed=950001, prefix_seed=951001, initial_status='ACTIVE')
    for repetition in plan['replicates']:
        repetition['base_seed'] += 10000
    plan_path, prefixes, endpoints, output = (tmp_path / name for name in (
        'plan32.json', 'prefixes32.json.gz', 'endpoints32.jsonl.gz', 'result32.json.gz'))
    plan_path.write_text(json.dumps(plan))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('v32_runner_test', scripts / 'run_controlled_predictive_transfer_v32.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'generate_board', lambda seed: BOARD)
    providers, preparations, events, reads, writes = [], [], [], Counter(), {}
    original_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if mode == 'rt':
            reads[Path(path)] += 1
        if mode == 'xt':
            writes[Path(path)] = handle
        return handle
    monkeypatch.setattr(gzip, 'open', tracked_open)
    original_prepare = cli.prepare_query
    def prepare(*args):
        assert not providers and not events and len(PrefixProvider.calls) == 32
        state, accounting = original_prepare(*args)
        assert len(PrefixProvider.calls) == 32
        preparations.append(state)
        return state, accounting
    monkeypatch.setattr(cli, 'prepare_query', prepare)
    class Provider:
        def __init__(self, seed):
            assert not events and len(preparations) == 2 and writes[prefixes].closed
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
    oracle = cli28.ExactOracle.from_closure(None)
    def closure(**kwargs):
        assert writes[endpoints].closed and writes[prefixes].closed and len(providers) == 8
        assert len(PrefixProvider.calls) == 32
        events.append('oracle')
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    def forbidden(*args, **kwargs):
        pytest.fail('fresh cohort acquisition must not restore an old model')
    monkeypatch.setattr(restoration, 'restore_state', forbidden)
    return cli, plan_path, prefixes, endpoints, output, historical, providers, preparations, reads


def test_fresh_prefix_paid_once_queries_prepared_once_and_all_locals_precede_truth(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, historical, providers, preparations, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_transfer(plan, prefixes, endpoints, output)
    assert report['status'] == 'TRANSFER_COMPLETE'
    assert report['plan_binding_validation']['passed'] and report['cohort_binding_validation']['passed']
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 2
    assert len(providers) == 8 and len(preparations) == 2 and len(PrefixProvider.calls) == 32
    assert reads == {endpoints: 1}
    account = report['accounting']
    assert account['prefix_board_count'] == 1 and account['prepared_query_count'] == 2
    assert account['prefix_physical_batches'] == 32 and account['local_physical_batches'] == 256
    assert account['total_physical_draws'] == 288 * 256
    assert account['historical_physical_draws'] == 76800
    assert account['historical_plus_new_physical_draws'] == 76800 + 288 * 256
    assert account['provider_counts_by_arm']['CACHED']['physical_draws'] == account['provider_counts_by_arm']['GAP_FRONTIER']['physical_draws'] == 128 * 256
    assert account['frozen_policy_evaluation_calls'] == 8
    assert report['original_source_accounting'] == historical and serialization['report_bytes'] > 0
    with gzip.open(prefixes, 'rt') as reader:
        evidence = json.load(reader)
    with gzip.open(endpoints, 'rt') as reader:
        pairs = [json.loads(line) for line in reader]
    assert len(evidence['prefixes']) == 1 and len(evidence['query_starts']) == 2
    assert evidence['oracle_constructed'] is False and evidence['local_acquisition_started'] is False
    assert [r['run_order'] for r in pairs] == [['CACHED', 'GAP_FRONTIER'], ['GAP_FRONTIER', 'CACHED'], ['GAP_FRONTIER', 'CACHED'], ['CACHED', 'GAP_FRONTIER']]
    for rep in report['repetitions']:
        for row in rep['contexts']:
            for result in row['arms'].values():
                assert set(result['costs']) == {'prefix_sampling_seconds', 'single_query_prepare_seconds', 'local_whole_run_seconds', 'independent_query_seconds'}
                assert result['costs']['independent_query_seconds'] == sum(v for k, v in result['costs'].items() if k != 'independent_query_seconds')
                assert 'reference_validation' not in result
                assert result['evaluation']['identities_pass'] and result['evaluation']['reach_probability_pass']


def test_evaluator_failure_keeps_fresh_acquisition_and_cost_denominators(monkeypatch, tmp_path):
    cli, plan, prefixes, endpoints, output, *_ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def unavailable(record, *args):
        if record['state_type'] == 'GapFrontierPlannerState':
            raise ValueError('frozen policy evaluation unavailable')
        return evaluate(record, *args)
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', unavailable)
    report, _ = cli.run_transfer(plan, prefixes, endpoints, output)
    assert report['source_valid_repetition_count'] == 2 and report['complete_repetition_count'] == 0
    assert report['accounting']['total_physical_draws'] == 288 * 256
    for rep in report['repetitions']:
        for row in rep['contexts']:
            candidate = row['arms']['GAP_FRONTIER']
            assert row['source_valid'] and not row['paired_complete']
            assert candidate['source_valid'] and not candidate['evaluation_validation']['passed']
            assert candidate['costs']['independent_query_seconds'] > 0


@pytest.mark.parametrize('field', ['selection_rule', 'suffix_seed', 'board', 'prerequisites'])
def test_changed_method_or_reused_cohort_identity_stops_before_sampling(monkeypatch, tmp_path, field):
    cli, plan_path, prefixes, endpoints, output, _, providers, *_ = _fixture(monkeypatch, tmp_path)
    plan = json.loads(plan_path.read_text())
    if field == 'selection_rule':
        plan[field]['frozen'] = 'changed'
    elif field == 'suffix_seed':
        plan['replicates'][0]['base_seed'] -= 10000
    elif field == 'prerequisites':
        plan['cohort_prerequisites']['all_new_registered_root_or_target_orbits'] = False
    else:
        plan['boards'][0]['board'][0] += 1
    plan_path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match='binding differs before acquisition'):
        cli.run_transfer(plan_path, prefixes, endpoints, output)
    assert not providers and PrefixProvider.calls == []
    assert not prefixes.exists() and not endpoints.exists() and not output.exists()
