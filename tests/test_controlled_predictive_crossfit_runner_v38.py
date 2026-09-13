"""Close every candidate before truth; preserve original source fees and policies."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_budget_transfer_runner_v35 import _fixture as source_fixture
from acfqp.science import controlled_predictive_sampling_v15 as sampling


def _fixture(monkeypatch, tmp_path):
    with monkeypatch.context() as source_patch:
        cli35, source_plan, prefixes, endpoints, source_result, *_ = source_fixture(source_patch, tmp_path)
        source, _ = cli35.run_budget_transfer(source_plan, prefixes, endpoints, source_result)
        oracle = cli35.ExactOracle.from_closure(None)
    source = json.loads(json.dumps(source))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    from analyze_controlled_predictive_budget_transfer_v35 import stream_statistics, policy_metrics, cost_metrics, COST_METRICS, all_actual_costs
    reference = {'accounting': {'model_restore_calls': 12}, 'source_diagnostic_accounting': {'model_restore_calls': 12, 'frozen_policy_evaluation_calls': 12},
        'all_analysis_checks_passed': True, 'original_source_accounting': source['accounting'],
        'original_quality_streams': stream_statistics(source['repetitions'], policy_metrics, ('total_regret',))[1],
        'original_cost_streams': stream_statistics(source['repetitions'], cost_metrics, COST_METRICS)[1],
        'all_original_actual_configuration_costs': all_actual_costs(source['repetitions'])}
    analysis = tmp_path / 'analysis37.json'
    analysis.write_text(json.dumps(reference))
    plan = json.loads((scripts.parent / 'reports/controlled_predictive_crossfit_plan_v38.json').read_text())
    for key in ('boards', 'contexts', 'queries', 'source_query_order', 'replicates', 'samples_per_batch', 'prefix_batches_per_board', 'selection_rule', 'board_count', 'context_count', 'query_count', 'replicate_count'):
        plan[key] = source['plan'][key]
    plan.update(source_plan=str(source_plan), source_result=str(source_result), source_analysis=str(analysis), source_endpoints=str(endpoints),
        source_configurations=source['plan']['configurations'], expected_pair_count=6, expected_endpoint_count=6,
        expected_model_restores=6, expected_source_triples_read=6, expected_proposals=6, expected_readout_calls=12,
        expected_policy_evaluations=6, expected_candidate_policy_evaluations=6,
        source_historical_physical_batches=source['accounting']['historical_plus_new_physical_batches'],
        source_historical_physical_draws=source['accounting']['historical_plus_new_physical_draws'])
    plan_path, proposals, output = tmp_path / 'plan38.json', tmp_path / 'proposals38.jsonl.gz', tmp_path / 'result38.json.gz'
    plan_path.write_text(json.dumps(plan))
    spec = importlib.util.spec_from_file_location('v38_runner_test', scripts / 'run_controlled_predictive_crossfit_v38.py')
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    reads, writers, calls, events = Counter(), {}, [], []
    original_open = gzip.open
    def tracked_open(path, mode='rb', *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        if mode == 'rt': reads[Path(path)] += 1
        if mode == 'xt': writers[Path(path)] = handle
        return handle
    monkeypatch.setattr(gzip, 'open', tracked_open)
    for name in ('pooled_root_readout', 'crossfit_root_readout'):
        original = getattr(cli, name)
        def tracked(*args, original=original, name=name):
            assert not events
            calls.append(name)
            return original(*args)
        monkeypatch.setattr(cli, name, tracked)
    original_read = cli._read
    def read(path):
        if Path(path) in (source_result, analysis):
            assert writers[proposals].closed and len(calls) == 12
        return original_read(path)
    monkeypatch.setattr(cli, '_read', read)
    def closure(**kwargs):
        assert writers[proposals].closed and len(calls) == 12
        events.append('oracle')
        return SimpleNamespace(counts={'toy': True})
    monkeypatch.setattr(cli, 'build_development_closure', closure)
    monkeypatch.setattr(cli.ExactOracle, 'from_closure', staticmethod(lambda closure: oracle))
    def forbidden(*args, **kwargs):
        pytest.fail('V38 must not construct a provider or acquire new environment samples')
    monkeypatch.setattr(sampling.BatchRowSampleProvider, '__init__', forbidden)
    monkeypatch.setattr(sampling.BatchRowSampleProvider, 'sample_batch', forbidden)
    return cli, plan_path, proposals, output, source, reference, reads, calls


def test_single_source_read_and_all_root_only_proposals_close_before_candidate_evaluation(monkeypatch, tmp_path):
    cli, plan, proposals, output, source, reference, reads, calls = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_crossfit(plan, proposals, output)
    assert report['status'] == 'CROSSFIT_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 3
    assert all(count == 1 for count in reads.values())
    assert calls == ['pooled_root_readout', 'crossfit_root_readout', 'crossfit_root_readout', 'pooled_root_readout',
        'crossfit_root_readout', 'pooled_root_readout', 'pooled_root_readout', 'crossfit_root_readout',
        'pooled_root_readout', 'crossfit_root_readout', 'crossfit_root_readout', 'pooled_root_readout']
    account = report['accounting']
    assert account['model_restore_calls'] == account['candidate_policy_evaluation_calls'] == 6
    assert account['baseline_policy_evaluation_calls'] == account['new_sampling_calls'] == account['new_physical_draws'] == 0
    assert account['proposal_records_written'] == account['proposal_records_read'] == 6
    assert report['original_source_accounting'] == source['accounting']
    assert report['original_all_actual_configuration_costs'] == reference['all_original_actual_configuration_costs']
    assert serialization['proposal_bytes'] > 0 and serialization['report_bytes'] > 0
    for rep in report['repetitions']:
        for context in rep['contexts']:
            before, after = (context['arms'][arm] for arm in cli.ARMS)
            assert before['value_reproduction_validation']['passed']
            assert 'lower' not in after['policy_evaluation'] and 'retained_pooled_lower' in after['policy_evaluation']
            assert all(row['costs']['postprocess_seconds'] == row['readout']['accounting']['whole_readout_seconds'] for row in context['arms'].values())
    source_path = json.loads(plan.read_text())['source_endpoints']
    with gzip.open(source_path, 'rt') as reader:
        original = [json.loads(line)['configurations']['CACHED32']['state'] for line in reader]
    with gzip.open(proposals, 'rt') as reader:
        frozen = [json.loads(line) for line in reader]
    for stored, proposal in zip(original, frozen):
        assert all(new == old for new, old in zip(proposal['candidate_state']['policy_and_intervals'], stored['policy_and_intervals']) if old['key'] != proposal['target_key'])
        assert proposal['candidate_state']['profiles'] == stored['profiles']
        assert proposal['candidate_state']['rows'] == [{'row_key': row['row_key']} for row in stored['rows']]
        assert len(proposal['crossfit_details']['split_rows']) == sum(row['row_key'][0][0] == 1 for row in stored['rows'])
    from analyze_controlled_predictive_crossfit_v38 import summarize
    analyzed = summarize(report, reference)
    assert analyzed['quality_complete_stream_count'] == 3
    assert {name for name, value in analyzed['checks'].items() if not value['passed']} == {'frozen_full_cohort_and_readout_arms'}


def test_unavailable_candidate_policy_preserves_postprocess_source_and_all_old_fees(monkeypatch, tmp_path):
    cli, plan, proposals, output, source, reference, *_ = _fixture(monkeypatch, tmp_path)
    evaluate = cli.evaluate_frozen_policy
    def unavailable(record, *args):
        result = evaluate(record, *args)
        result.update(policy_evaluable=False, missing_probability=.25, terminal_probability=.75,
            unavailable_reason='POSITIVE_MISSING_POLICY_PROBABILITY', v_pi=None, total_regret=None,
            continuation_regret=None, identity_residual=None, identities_pass=None, policy_optimal=None)
        return result
    monkeypatch.setattr(cli, 'evaluate_frozen_policy', unavailable)
    report, _ = cli.run_crossfit(plan, proposals, output)
    assert report['source_valid_repetition_count'] == 3 and report['complete_repetition_count'] == 0
    for rep in report['repetitions']:
        for context in rep['contexts']:
            candidate = context['arms']['CROSSFIT']
            assert candidate['source_valid'] and candidate['costs']['postprocess_seconds'] > 0
            assert candidate['policy_evaluation']['v_pi'] is None and candidate['policy_evaluation']['missing_probability'] == .25
    assert report['original_all_actual_configuration_costs'] == reference['all_original_actual_configuration_costs']
    assert all(rep['complete'] for rep in report['original_repetitions'])
    from analyze_controlled_predictive_crossfit_v38 import summarize
    analyzed = summarize(report, reference)
    assert analyzed['source_valid_stream_count'] == 3 and analyzed['quality_complete_stream_count'] == 0
    assert analyzed['diagnostic_valid_stream_count'] == 3
