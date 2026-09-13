"""Integrated retained V36 binding with zero new sampling or full-policy work."""

from collections import Counter
import gzip
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_controlled_predictive_endpoint_errors_runner_v36 import _fixture as source_fixture
from acfqp.science import controlled_predictive_frozen_policy_v27 as policy_core
from acfqp.science import controlled_predictive_sampling_v15 as sampling


def _fixture(monkeypatch, tmp_path):
    with monkeypatch.context() as source_patch:
        cli36, source_plan, source_result, *_ = source_fixture(source_patch, tmp_path)
        source, _ = cli36.run_endpoint_errors(source_plan, source_result)
        oracle = cli36.ExactOracle.from_closure(None)
    source = json.loads(json.dumps(source))
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    from analyze_controlled_predictive_endpoint_errors_v36 import root_statistics, group_counts
    from analyze_controlled_predictive_budget_transfer_v35 import stream_statistics, policy_metrics, cost_metrics, COST_METRICS, all_actual_costs
    source['original_all_actual_configuration_costs'] = all_actual_costs(source['original_repetitions'])
    with gzip.open(source_result, 'wt') as writer:
        json.dump(source, writer)
    root, streams = root_statistics(source['repetitions'])
    reference = {'accounting': source['accounting'], 'all_analysis_checks_passed': True,
        'root_action_streams': streams, 'root_action_counterfactual_statistics': root,
        'common_diagnostic_full_policy_groups': group_counts([row for rep in source['repetitions'] for row in rep['contexts']]),
        'original_quality_streams': stream_statistics(source['original_repetitions'], policy_metrics, ('total_regret',))[1],
        'original_cost_streams': stream_statistics(source['original_repetitions'], cost_metrics, COST_METRICS)[1],
        'all_original_actual_configuration_costs': source['original_all_actual_configuration_costs'],
        'original_source_accounting': source['original_source_accounting']}
    analysis = tmp_path / 'analysis36.json'
    analysis.write_text(json.dumps(reference))
    plan = {**source['plan'], 'source_plan': str(source_plan), 'source_result': str(source_result), 'source_analysis': str(analysis),
        'modes': ['RAW', 'REMOVE_E', 'REMOVE_C'], 'expected_policy_evaluations': 0}
    plan_path, output = tmp_path / 'plan37.json', tmp_path / 'result37.json.gz'
    plan_path.write_text(json.dumps(plan))
    spec = importlib.util.spec_from_file_location('v37_runner_test', scripts / 'run_controlled_predictive_continuation_sources_v37.py')
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
        pytest.fail('V37 must not sample or re-evaluate the frozen full policy')
    monkeypatch.setattr(sampling.BatchRowSampleProvider, '__init__', forbidden)
    monkeypatch.setattr(sampling.BatchRowSampleProvider, 'sample_batch', forbidden)
    monkeypatch.setattr(policy_core, 'evaluate_frozen_policy', forbidden)
    monkeypatch.setattr(cli36, 'evaluate_frozen_policy', forbidden)
    return cli, plan_path, output, source, reference, reads


def test_all_endpoints_restore_once_exact_v36_reproduction_and_analyzer_interface(monkeypatch, tmp_path):
    cli, plan, output, old, reference, reads = _fixture(monkeypatch, tmp_path)
    report, serialization = cli.run_continuation_sources(plan, output)
    assert report['status'] == 'CONTINUATION_SOURCES_COMPLETE'
    assert report['source_valid_repetition_count'] == report['complete_repetition_count'] == 3
    assert all(count == 1 for count in reads.values())
    account = report['accounting']
    assert account['model_restore_calls'] == account['local_decomposition_calls'] == 12
    assert account['action_decompositions'] == 48 and account['source_endpoint_triple_records_read'] == 6
    assert account['frozen_policy_evaluation_calls'] == account['new_sampling_calls'] == account['new_physical_draws'] == 0
    assert report['source_diagnostic_accounting'] == old['accounting']
    assert report['original_source_accounting'] == old['original_source_accounting']
    assert report['original_repetitions'] == old['original_repetitions']
    assert report['original_all_actual_configuration_costs'] == old['original_all_actual_configuration_costs']
    assert serialization['report_bytes'] > 0
    for rep in report['repetitions']:
        for context in rep['contexts']:
            assert context['cross_budget']['actions'][0] == context['cross_budget']['actions'][1]
            assert all(value == 0 for value in context['cross_budget']['change'].values())
            for endpoint in context['configurations'].values():
                assert endpoint['local_reproduction_validation']['passed']
                assert endpoint['legacy_diagnostic_reproduction_validation']['passed']
                assert endpoint['inherited_policy_validation']['passed']
    from analyze_controlled_predictive_continuation_sources_v37 import summarize
    analyzed = summarize(report, reference)
    assert analyzed['diagnostic_complete_stream_count'] == 3
    # This integrated fixture has one board and three streams, so only the
    # production cohort-size assertion is intentionally outside its scope.
    assert {name for name, check in analyzed['checks'].items() if not check['passed']} == {'frozen_full_H2_cohort_and_modes'}


@pytest.mark.parametrize('damage', ['integer_counts', 'v36_local'])
def test_failed_current_endpoint_keeps_all_original_masks_and_fees(monkeypatch, tmp_path, damage):
    cli, plan_path, output, old, reference, reads = _fixture(monkeypatch, tmp_path)
    plan = json.loads(plan_path.read_text())
    if damage == 'integer_counts':
        with gzip.open(plan['source_endpoints'], 'rt') as reader:
            rows = [json.loads(line) for line in reader]
        rows[0]['configurations']['CACHED24']['state']['rows'][0]['integer_counts'][0]['count'] += 1
        with gzip.open(plan['source_endpoints'], 'wt') as writer:
            for row in rows:
                writer.write(json.dumps(row) + '\n')
    else:
        old['repetitions'][0]['contexts'][0]['configurations']['CACHED24']['local_evaluation']['actions']['DOWN']['D_continuation_error'] += .01
        with gzip.open(plan['source_result'], 'wt') as writer:
            json.dump(old, writer)
    report, _ = cli.run_continuation_sources(plan_path, output)
    assert report['status'] == 'CONTINUATION_SOURCES_WITH_ISSUES'
    failed = report['repetitions'][0]['contexts'][0]['configurations']['CACHED24']
    assert failed['source_valid'] == (damage == 'v36_local')
    assert failed['status'] == 'CONTINUATION_DIAGNOSTIC_INCOMPLETE'
    assert not failed['diagnostic_available']
    assert sum(len(rep['contexts']) for rep in report['repetitions']) == 6
    assert report['accounting']['model_restore_calls'] == 12
    assert report['original_repetitions'] == old['original_repetitions']
    assert report['original_all_actual_configuration_costs'] == old['original_all_actual_configuration_costs']
    assert all(rep['complete'] for rep in report['original_v36_repetitions'])
    assert all(rep['complete'] for rep in report['original_repetitions'])
