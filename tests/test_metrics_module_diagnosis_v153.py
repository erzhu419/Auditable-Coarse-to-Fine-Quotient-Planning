"""Independent algebra and weighting checks on synthetic four-branch returns."""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
from statistics import mean, variance

import pytest

from scripts import analyze_controlled_predictive_module_diagnosis_v153 as analysis

TEMP = Path(__file__).resolve().parents[1]/'reports/v153_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'metrics_checks.json'; data = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    data['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, synthetic_work=dict(WORK), production_data_reads=0,
        environment_samples=0, model_samples=0, native_planner_calls=0, training_updates=0))
    path.write_text(json.dumps(data, indent=2)+'\n')


def root(life=0, slot=0, source='H2', query='risk1', prediction=2., accept=True):
    return dict(root_id=f'{life}:{query}:{source}:{slot}', life=life, query=query,
                source_method=source, slot=slot, prediction=dict(advantage=prediction, accept=accept))


def branches(delta_h2, delta_gate):
    result = {}
    for suffix in range(16):
        h_h2, h_gate = 100.+100*suffix, 70.+3*suffix
        utilities = dict(H_H2=h_h2, M_H2=h_h2+delta_h2[suffix],
                         H_GATE=h_gate, M_GATE=h_gate+delta_gate[suffix])
        result[suffix] = {mode: dict(valid=True, result=dict(status='WON', utility=value,
            components=[value-1., 0., 1.])) for mode, value in utilities.items()}
    WORK['synthetic_branch_results_generated'] += 64
    return result


def diagnose(item, data):
    WORK['root_diagnostics_calls'] += 1
    return analysis.root_diagnostics(item, data)


def test_paired_four_branch_identity_errors_and_mse_excess_match_direct_algebra():
    h = [s-4. for s in range(16)]; g = [.5*s-2. for s in range(16)]; p = 2.
    row = diagnose(root(prediction=p), branches(h, g))
    expected = dict(delta_h2=h, delta_gate=g, continuation_shift=[b-a for a, b in zip(h, g)],
        error_h2=[p-a for a in h], error_gate=[p-b for b in g], policy_gain_h2=h, policy_gain_gate=g,
        mse_excess_h2=[(p-a)**2-a*a for a in h], mse_excess_gate=[(p-b)**2-b*b for b in g])
    assert row['complete'] and set(row['metrics']) == set(expected)
    for name, values in expected.items():
        actual = row['metrics'][name]
        assert actual['n'] == 16 and actual['complete']
        assert actual['mean'] == pytest.approx(mean(values))
        assert actual['sample_variance'] == pytest.approx(variance(values))
        assert actual['mean_variance'] == pytest.approx(variance(values)/16)
    assert row['metrics']['delta_gate']['mean'] == pytest.approx(
        row['metrics']['delta_h2']['mean']+row['metrics']['continuation_shift']['mean'])
    assert row['metrics']['error_gate']['mean'] == pytest.approx(
        row['metrics']['error_h2']['mean']-row['metrics']['continuation_shift']['mean'])
    for condition, values in (('h2', h), ('gate', g)):
        plugin = row['plug_in_mse'][condition]
        assert plugin['prediction_mse'] == pytest.approx((p-mean(values))**2)
        assert plugin['zero_mse'] == pytest.approx(mean(values)**2)
        assert plugin['mc_mean_variance'] == pytest.approx(variance(values)/16)
        assert plugin['prediction_mse']-plugin['zero_mse'] == pytest.approx(row['metrics'][f'mse_excess_{condition}']['mean'])


def test_fixed_four_suffix_blocks_keep_their_own_means_and_four_draw_variance():
    h = list(range(16)); g = [s+1. for s in h]
    row = diagnose(root(), branches(h, g))
    assert len(row['blocks']) == 4
    for block, metrics in enumerate(row['blocks']):
        values = h[4*block:4*block+4]
        assert metrics['delta_h2']['n'] == 4
        assert metrics['delta_h2']['mean'] == mean(values)
        assert metrics['delta_h2']['mean_variance'] == pytest.approx(variance(values)/4)
        # Paired subtraction cancels this shift's seed variation exactly.
        assert metrics['continuation_shift']['mean'] == 1.
        assert metrics['continuation_shift']['sample_variance'] == 0.


def all_roots(empty_accepted_life=None):
    rows = []
    for source in analysis.SOURCES:
        for query in analysis.QUERIES:
            for life in analysis.LIVES:
                for slot in range(4):
                    accepted = slot <= life and life != empty_accepted_life
                    h = [10.*life+slot+(slot+1)*(s-7.5) for s in range(16)]
                    item = root(life, slot, source, query, 2. if accepted else -2., accepted)
                    rows.append(diagnose(item, branches(h, [v+1. for v in h])))
    return rows


def test_root_variance_weights_then_equal_history_weights_are_not_pooled_observations():
    rows = all_roots(); full = analysis.aggregate(rows); accepted = analysis.aggregate(rows, accepted_only=True)
    WORK['aggregate_calls'] += 2
    seed_variance = variance(range(16))
    for source in analysis.SOURCES:
        for query in analysis.QUERIES:
            for summary, sizes in ((full[source][query], [4]*4), (accepted[source][query], [1, 2, 3, 4])):
                assert summary['complete']
                expected_history_means = [10.*life+(size-1)/2 for life, size in enumerate(sizes)]
                history_variances = [sum((slot+1)**2*seed_variance/16 for slot in range(size))/size**2 for size in sizes]
                expected_se = math.sqrt(sum(history_variances)/4**2)
                metric = summary['metrics']['delta_h2']
                assert metric['mean'] == mean(expected_history_means)
                assert metric['conditional_suffix_se'] == pytest.approx(expected_se)
                assert metric['conditional_suffix_ci95'] == pytest.approx([
                    mean(expected_history_means)-1.96*expected_se, mean(expected_history_means)+1.96*expected_se])
                assert [h['roots'] for h in summary['lifecycles']] == sizes
                for history, expected_variance in zip(summary['lifecycles'], history_variances):
                    assert history['metrics']['delta_h2']['conditional_suffix_se'] == pytest.approx(math.sqrt(expected_variance))
                assert summary['metrics']['continuation_shift']['conditional_suffix_se'] == 0.
                assert [(b['suffix_start'], b['suffix_end']) for b in summary['blocks']] == [(0, 3), (4, 7), (8, 11), (12, 15)]
                block_variance = variance(range(4))
                block_se = math.sqrt(sum(sum((slot+1)**2*block_variance/4 for slot in range(n))/n**2 for n in sizes)/4**2)
                for block in summary['blocks']:
                    assert block['metrics']['delta_h2']['conditional_suffix_se'] == pytest.approx(block_se)
            assert accepted[source][query]['metrics']['delta_h2']['mean'] == 15.75
            pooled_mean = mean(10.*life+slot for life in range(4) for slot in range(life+1))
            assert pooled_mean == 21. and pooled_mean != accepted[source][query]['metrics']['delta_h2']['mean']


def test_empty_accepted_history_remains_incomplete_instead_of_dropping_that_history():
    rows = all_roots(empty_accepted_life=2); result = analysis.aggregate(rows, accepted_only=True)
    WORK['aggregate_calls'] += 1
    for source in analysis.SOURCES:
        for query in analysis.QUERIES:
            cell = result[source][query]
            assert not cell['complete'] and cell['lifecycles'][2]['roots'] == 0
            assert not cell['lifecycles'][2]['complete']
            for metric in cell['metrics'].values():
                assert not metric['complete'] and metric['mean'] is None
                assert metric['conditional_suffix_se'] is None and metric['conditional_suffix_ci95'] is None
            assert all(not block['complete'] for block in cell['blocks'])
            assert cell['plug_in_mse']['h2']['prediction_mse'] is None


@pytest.mark.parametrize('accepted', [True, False])
def test_cutoff_propagates_only_affected_pairs_and_declined_policy_gain_is_exact_zero(accepted):
    data = branches([1.]*16, [3.]*16)
    data[3]['H_GATE']['result'].update(status='CUTOFF', utility=None)
    row = diagnose(root(prediction=2. if accepted else -2., accept=accepted), data)
    assert not row['complete']
    assert row['metrics']['delta_h2']['complete'] and row['metrics']['delta_h2']['mean'] == 1.
    assert not row['metrics']['delta_gate']['complete'] and row['metrics']['delta_gate']['mean'] is None
    assert row['metrics']['continuation_shift']['mean'] is None and row['metrics']['mse_excess_gate']['mean'] is None
    assert not row['blocks'][0]['delta_gate']['complete']
    assert all(block['delta_gate']['complete'] for block in row['blocks'][1:])
    if accepted:
        assert row['metrics']['policy_gain_gate']['mean'] is None
    else:
        for name in ('policy_gain_h2', 'policy_gain_gate'):
            metric = row['metrics'][name]
            assert metric['complete'] and metric['mean'] == metric['sample_variance'] == metric['mean_variance'] == 0.


def test_missing_or_invalid_branch_is_not_silently_treated_as_terminal_evidence():
    data = branches([1.]*16, [3.]*16)
    del data[1]['M_H2']; data[2]['M_GATE']['valid'] = False
    row = diagnose(root(), data)
    assert not row['complete']
    for name in ('delta_h2', 'delta_gate', 'continuation_shift', 'error_h2', 'error_gate'):
        assert not row['metrics'][name]['complete'] and row['metrics'][name]['mean'] is None
    assert all(block['delta_h2']['complete'] and block['delta_gate']['complete'] for block in row['blocks'][1:])
    assert analysis.moments([]) == dict(n=0, complete=False, mean=None, sample_variance=None, mean_variance=None)
