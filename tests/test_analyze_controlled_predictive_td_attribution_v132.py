"""Finite fixtures for strict signs, cancellation and fixed diagnostic denominators."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_td_attribution_v132 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_td_attribution_v132.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic signed attribution, strict/rounded gaps, aliases and missing-slot fixtures'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def contributions(value):
    return {category: dict(net=value, exact_board=value/4., shared_rest=3*value/4.)
        for category in analysis.CATEGORIES}


def test_signed_attribution_preserves_cancellation_and_partitions():
    totals = analysis.category_totals([contributions(3.), contributions(-3.)])
    assert all(row == dict(net=0., exact_board=0., shared_rest=0.) for row in totals.values())
    totals = analysis.category_totals([contributions(3.), contributions(-2.)])
    assert all(row == dict(net=1., exact_board=.25, shared_rest=.75) for row in totals.values())


def test_canonical_strict_flip_is_separate_from_rounded_action_gap():
    item = analysis.gap_classification(-2., 1., -2., 1., [[5, 1]], 0.)
    assert item['canonical_strict_flip'] and item['rounded_strict_flip']
    assert not item['parameter_invariant_tie']
    item = analysis.gap_classification(0., 0., -1e-15, 1e-15, [], 0.)
    assert item['parameter_invariant_tie'] and item['rounded_strict_flip']
    assert not item['canonical_strict_flip']
    assert item['mid_sign_disagrees_with_rounding'] and item['final_sign_disagrees_with_rounding']
    item = analysis.gap_classification(2., 0., 2., 0., [[5, 1]], 0.)
    assert not item['canonical_strict_flip'] and item['canonical_endpoint_tie']


def group_fixture():
    slots, probes = [], {}
    for life in analysis.LIVES:
        key = f'probe_{life}'
        probe = dict(life=life, mid=dict(canonical_gap=-life-1.), final=dict(canonical_gap=life+1.),
            classification=analysis.gap_classification(-life-1., life+1., -life-1., life+1., [[4, 1]], 0.),
            closure_residual=0., attribution=contributions(life+1.))
        probes[key] = probe
        for group in analysis.GROUPS:
            for replica in range(analysis.REPLICAS):
                slots.append(dict(life=life, group=group, replica=replica, probe_id=key))
    return slots, probes


def test_aliases_preserve_all_episode_slots_and_groups_stay_separate():
    slots, probes = group_fixture()
    result = analysis.group_summary(slots, probes, 'FIRST')
    assert result['complete_roster'] and result['all_slots_available']
    assert result['slots'] == result['available_slots'] == 64
    assert result['unique_probes'] == 4
    assert result['equal_life_available_slot_means']['mid_gap'] == -2.5
    assert all(row['alias_slots'] == 15 and row['events']['canonical_strict_flip'] == 16
        and row['event_fractions_of_fixed_slots']['canonical_strict_flip'] == 1.
        for row in result['lifecycles'])


def test_missing_roots_keep_denominators_and_do_not_reweight_histories():
    slots, probes = group_fixture()
    selected = [slot for slot in slots if slot['group'] == 'FIRST' and slot['life'] == 0]
    for slot in selected[1:]: slot.update(probe_id=None, reason='no_feature_difference')
    result = analysis.group_summary(slots, probes, 'FIRST')
    assert result['complete_roster'] and not result['all_slots_available']
    assert result['slots'] == 64 and result['available_slots'] == 49
    assert result['lifecycles'][0]['event_fractions_of_fixed_slots']['canonical_strict_flip'] == 1/16
    assert result['equal_life_available_slot_means']['mid_gap'] == -2.5
    selected[0].update(probe_id=None, reason='no_feature_difference')
    result = analysis.group_summary(slots, probes, 'FIRST')
    assert result['equal_life_available_slot_means']['mid_gap'] is None
    other = analysis.group_summary(slots, probes, 'FEATURE')
    assert other['all_slots_available'] and other['equal_life_available_slot_means']['mid_gap'] == -2.5


def test_update_partition_counts_winning_boundary_and_pending_pause_once():
    rows = [dict(cumulative_transitions=2, actions=['LEFT']*2, updates_before=0,
        updates_after=1, td_targets=[None, 1.], terminal_update=None, status='ACTIVE',
        episode=0, pending_before=None, pending_after=[2], start_board=[1], end_board=[3]),
        dict(cumulative_transitions=4, actions=['LEFT']*2, updates_before=1,
        updates_after=3, td_targets=[2., 8.], terminal_update=None, status='WON',
        episode=0, pending_before=[2], pending_after=None, start_board=[3], end_board=[11]),
        dict(cumulative_transitions=6, actions=['LEFT']*2, updates_before=3,
        updates_after=5, td_targets=[None, 2.], terminal_update=dict(target=-8.), status='LOST',
        episode=1, pending_before=None, pending_after=None, start_board=[1], end_board=[2])]
    result = analysis.retained_category_totals(rows, mid=2, final=6)
    assert all(result['checks'].values())
    assert result['transitions'] == 4 and result['updates'] == 4
    assert result['categories'] == dict(LOSS=1, WIN_BOUNDARY=1, BOOTSTRAP=2)
    broken = deepcopy(rows); broken[1]['pending_before'] = None
    assert not analysis.retained_category_totals(broken, 2, 6)['checks']['retained_pending_continuity']
