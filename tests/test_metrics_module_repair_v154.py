"""Pure synthetic tests for paired V154 control comparisons and seed intervals."""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
from statistics import mean, variance

import pytest

from scripts import analyze_controlled_predictive_module_repair_v154 as analysis

TEMP = Path(__file__).resolve().parents[1]/'reports/v154_runtime_tmp'
WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'metrics_checks.json'; result = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    result['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, synthetic_work=dict(WORK), production_data_reads=0,
        environment_samples=0, model_samples=0, native_planner_calls=0, training_updates=0))
    path.write_text(json.dumps(result, indent=2)+'\n')


ARMS = ('H2', 'ALT', 'OLD', 'REPAIR_H2', 'REPAIR_GATE')
CONTRASTS = {'REPAIR_H2-OLD': ('REPAIR_H2', 'OLD'),
    'REPAIR_GATE-OLD': ('REPAIR_GATE', 'OLD'),
    'REPAIR_GATE-REPAIR_H2': ('REPAIR_GATE', 'REPAIR_H2'),
    'OLD-H2': ('OLD', 'H2'), 'OLD-ALT': ('OLD', 'ALT'),
    'REPAIR_H2-H2': ('REPAIR_H2', 'H2'), 'REPAIR_H2-ALT': ('REPAIR_H2', 'ALT'),
    'REPAIR_GATE-H2': ('REPAIR_GATE', 'H2'), 'REPAIR_GATE-ALT': ('REPAIR_GATE', 'ALT'),
    'ALT-H2': ('ALT', 'H2')}
QUERIES = ('risk1', 'risk8')


def synthetic_utility(life, query, arm, replica):
    common = 1000.+100.*replica+10.*life+(500. if query == 'risk8' else 0.)
    centered = replica-7.5
    offsets = dict(H2=0., ALT=-2.+.25*centered, OLD=5.+life)
    offsets['REPAIR_H2'] = offsets['OLD']+10.*life+2.+(life+1)*centered
    offsets['REPAIR_GATE'] = offsets['REPAIR_H2']-3.+life+.5*centered
    return common+offsets[arm]


def synthetic_indexed():
    indexed = {}
    # Deliberately non-canonical insertion order; pairing must follow explicit keys.
    for life in (3, 0, 2, 1):
        for query in reversed(QUERIES):
            for arm in reversed(ARMS):
                for replica in reversed(range(16)):
                    value = synthetic_utility(life, query, arm, replica)
                    bonus = 1. if query == 'risk1' else 8.
                    indexed[life, query, arm, replica] = dict(result=dict(status='WON', utility=value,
                        score=(value-bonus)*2048., steps=20+replica, components=[value-bonus, 0., 1.]))
    WORK['synthetic_logical_results_generated'] += len(indexed)
    return indexed, dict.fromkeys(indexed, True)


def aggregate(indexed, valid):
    WORK['aggregate_calls'] += 1
    return analysis.aggregate(indexed, valid)


def expected_deltas(left, right, query):
    return [[synthetic_utility(life, query, left, replica)-synthetic_utility(life, query, right, replica)
        for replica in range(16)] for life in range(4)]


def test_all_arm_means_and_contrasts_use_matched_replicas_then_equal_histories():
    indexed, valid = synthetic_indexed(); result = aggregate(indexed, valid)
    assert result['primary_complete'] and set(result['arms']) == set(ARMS)
    assert set(result['comparisons']) == set(CONTRASTS)
    assert sum(cell['games'] for arm in result['arms'].values() for cell in arm.values()) == 640
    for arm in ARMS:
        for query in QUERIES:
            cell = result['arms'][arm][query]
            assert cell['complete'] and cell['wins'] == cell['games'] == 64
            assert cell['means']['utility'] == mean(mean(synthetic_utility(life, query, arm, replica)
                for replica in range(16)) for life in range(4))
            assert cell['means']['steps'] == 27.5
            assert [c['life'] for c in cell['lifecycles']] == list(range(4))
    for contrast, (left, right) in CONTRASTS.items():
        for query in QUERIES:
            cell = result['comparisons'][contrast][query]; deltas = expected_deltas(left, right, query)
            history_means = [mean(values) for values in deltas]
            expected_mean = mean(history_means)
            expected_se = math.sqrt(sum(variance(values)/16 for values in deltas)/16)
            assert cell['complete'] and cell['mean'] == pytest.approx(expected_mean)
            assert cell['conditional_seed_se'] == pytest.approx(expected_se)
            assert cell['conditional_seed_ci95'] == pytest.approx([expected_mean-1.96*expected_se, expected_mean+1.96*expected_se])
            assert [c['replica_deltas'] for c in cell['lifecycles']] == deltas
            assert cell['positive'] == sum(v > 0 for v in history_means)
            assert cell['negative'] == sum(v < 0 for v in history_means)
            assert cell['zero'] == sum(v == 0 for v in history_means)
    repair = result['comparisons']['REPAIR_H2-OLD']['risk1']
    assert repair['mean'] == 17.
    # Pairing cancels the common 100*replica term; summing arm variances is wrong.
    naive_independent = math.sqrt(sum((variance([synthetic_utility(l, 'risk1', a, r) for r in range(16)])
        +variance([synthetic_utility(l, 'risk1', 'OLD', r) for r in range(16)]))/16 for l in range(4)
        for a in ('REPAIR_H2',))/16)
    assert naive_independent > repair['conditional_seed_se']*20


def test_four_prespecified_seed_blocks_are_kept_in_order_with_equal_history_means():
    indexed, valid = synthetic_indexed(); result = aggregate(indexed, valid)
    for name, (left, right) in CONTRASTS.items():
        for query in QUERIES:
            cell = result['comparisons'][name][query]; deltas = expected_deltas(left, right, query)
            assert [(b['replica_start'], b['replica_end']) for b in cell['blocks']] == [(0, 3), (4, 7), (8, 11), (12, 15)]
            for b, block in enumerate(cell['blocks']):
                history_means = [mean(values[4*b:4*b+4]) for values in deltas]
                assert block['complete'] and block['mean'] == pytest.approx(mean(history_means))
                assert block['positive_histories'] == sum(v > 0 for v in history_means)
                assert [history['blocks'][b]['mean'] for history in cell['lifecycles']] == history_means


def test_conditional_seed_interval_does_not_treat_fixed_history_differences_as_seed_noise():
    indexed, valid = synthetic_indexed()
    for life in range(4):
        for query in QUERIES:
            for replica in range(16):
                old = indexed[life, query, 'OLD', replica]['result']['utility']
                indexed[life, query, 'REPAIR_H2', replica]['result']['utility'] = old+100.*life
    result = aggregate(indexed, valid)
    for query in QUERIES:
        cell = result['comparisons']['REPAIR_H2-OLD'][query]
        assert cell['mean'] == 150. and cell['conditional_seed_se'] == 0.
        assert cell['conditional_seed_ci95'] == [150., 150.]
        assert cell['positive'] == 3 and cell['negative'] == 0 and cell['zero'] == 1


def test_cutoff_only_invalidates_its_arm_query_and_related_paired_comparisons():
    indexed, valid = synthetic_indexed()
    cutoff = indexed[2, 'risk1', 'REPAIR_GATE', 7]['result']
    cutoff.update(status='CUTOFF', utility=None)
    result = aggregate(indexed, valid)
    assert not result['primary_complete']
    for arm in ARMS:
        for query in QUERIES:
            cell = result['arms'][arm][query]
            affected = arm == 'REPAIR_GATE' and query == 'risk1'
            assert cell['complete'] == (not affected)
            assert cell['games'] == 64 and cell['wins'] == (63 if affected else 64)
            assert (cell['means']['utility'] is None) == affected
    for name, pair in CONTRASTS.items():
        for query in QUERIES:
            cell = result['comparisons'][name][query]
            affected = 'REPAIR_GATE' in pair and query == 'risk1'
            assert cell['complete'] == (not affected)
            if affected:
                assert cell['mean'] is None and cell['conditional_seed_se'] is None and cell['conditional_seed_ci95'] is None
                assert cell['lifecycles'][2]['replica_deltas'][7] is None
                assert [b['complete'] for b in cell['blocks']] == [True, False, True, True]
                assert all(c['complete'] for c in cell['lifecycles'] if c['life'] != 2)
            else:
                assert cell['mean'] == pytest.approx(mean(mean(d) for d in expected_deltas(*pair, query)))


def test_alt_aliases_recompose_target_utility_without_mutating_physical_results():
    indexed, valid = {}, {}
    physical = {}
    for life in range(4):
        for query in QUERIES:
            for arm in ('H2', 'OLD', 'REPAIR_H2', 'REPAIR_GATE'):
                for replica in range(16):
                    if query == 'risk1':
                        result = dict(status='WON', components=[4., 0., 1.], utility=5., score=8192, steps=20)
                    else:
                        result = dict(status='LOST', components=[10., 1., 0.], utility=2., score=20480, steps=30)
                    physical[life, query, arm, replica] = result
    before = deepcopy(physical)
    for life in range(4):
        for query in QUERIES:
            for arm in ARMS:
                for replica in range(16):
                    source_query = ('risk8' if query == 'risk1' else 'risk1') if arm == 'ALT' else query
                    source_arm = 'H2' if arm == 'ALT' else arm
                    result = analysis.logical_result(physical[life, source_query, source_arm, replica], query)
                    WORK['logical_result_calls'] += 1
                    indexed[life, query, arm, replica] = dict(result=result)
                    valid[life, query, arm, replica] = True
    WORK['synthetic_physical_results_generated'] += len(physical)
    WORK['synthetic_logical_results_generated'] += len(indexed)
    assert len(physical) == 512 and len(indexed) == 640 and physical == before
    result = aggregate(indexed, valid)
    assert result['arms']['ALT']['risk1']['means']['utility'] == 9.
    assert result['arms']['ALT']['risk8']['means']['utility'] == 12.
    assert result['comparisons']['ALT-H2']['risk1']['mean'] == 4.
    assert result['comparisons']['ALT-H2']['risk8']['mean'] == 10.
    assert result['arms']['ALT']['risk1']['wins'] == 0 and result['arms']['ALT']['risk8']['wins'] == 64
    # The same physical cutoff remains censored under either target query.
    censored = dict(physical[0, 'risk8', 'H2', 0], status='CUTOFF', utility=999.)
    assert analysis.logical_result(censored, 'risk1')['utility'] is None
    assert analysis.logical_result(censored, 'risk8')['utility'] is None
    WORK['logical_result_calls'] += 2
