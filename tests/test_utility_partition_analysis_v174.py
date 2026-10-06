"""Dual proposal freezing, fixed-family inference and new six-arm source pools."""
from copy import deepcopy
from statistics import NormalDist

import pytest

from scripts import analyze_controlled_predictive_utility_partition_v174 as audit
from scripts import run_controlled_predictive_utility_partition_v174 as runner
from acfqp.science import controlled_predictive_confirmed_partition_v173 as confirmation
from test_confirmed_partition_core_v173 import proposal, roots_pair, outcomes, true_vectors
from test_confirmed_partition_analysis_v173 import validation_fixture

ROWS = []


def test_both_generator_choices_use_one_global_frozen_family_and_six_final_modes():
    nested, flat = {}, {}
    for generator in audit.GENERATORS:
        nested[generator] = {}
        for life in audit.LIVES:
            model = proposal(deeper=generator == 'UTILITY')
            model.update(life=life, mode=f'PART_{generator}_UNPRUNED')
            nested[generator][life] = model
            flat[life, generator] = model
    roots = roots_pair()
    actual, actual_work = runner.freeze_all_node_choices(nested, roots)
    choices, work = audit.freeze_node_choices(flat, roots)
    assert audit._equal(actual, choices) and actual_work == work
    assert {row['generator'] for row in choices} == set(audit.GENERATORS)
    assert len([row for row in choices if row['generator'] == 'UTILITY']) > len(
        [row for row in choices if row['generator'] == 'SSE'])
    family_size = sum(node['kind'] == 'split' for model in flat.values() for node in model['nodes'])
    assert family_size == 12
    values = outcomes(roots, true_vectors)
    models = {}
    for generator in audit.GENERATORS:
        local = [{key: value for key, value in row.items() if key != 'generator'}
                 for row in choices if row['generator'] == generator]
        original = flat[0, generator]
        actual_model, actual_record = confirmation.confirm_and_prune(original, roots, local, values, family_size)
        confirmed, record = audit.previous.confirm_and_prune(original, roots, local, values, family_size)
        assert audit._equal(actual_model, confirmed) and audit._equal(actual_record, record)
        assert record['family']['total_candidates'] == family_size
        assert record['family']['z'] == NormalDist().inv_cdf(1 - .05 / (2 * family_size))
        assert confirmed['node_fits'] == original['node_fits']
        confirmed['mode'] = f'PART_{generator}_CONFIRMED'
        models[0, confirmed['mode']] = confirmed
        models[0, original['mode']] = original
    one = deepcopy(flat[0, 'SSE'])
    one.update(mode='ONE_LATE', nodes=[], groups={'ALL': 0}, leaves=[deepcopy(one['node_fits']['0'])])
    models[0, 'ONE_LATE'] = one
    actual_final, actual_final_work = runner.frozen_choices(roots, models)
    expected_final, expected_final_work = audit.choices_for(roots, models)
    assert audit._equal(actual_final, expected_final) and actual_final_work == expected_final_work
    assert len(expected_final) == len(roots) * 6
    assert {row['mode'] for row in expected_final} == set((*audit.MODES, 'H2'))


def test_six_arm_source_pool_uses_utility_retained_structure_and_preserves_hold():
    roots, _, _ = validation_fixture()
    plans = audit.forced_roster(roots, 'VALID')
    values = [dict(plan, score=2048. * plan['replica'] * (plan['canonical_action'] == 'DOWN'),
        steps=1, status='WON', components=[float(plan['replica']) * (plan['canonical_action'] == 'DOWN'), 0., 1.],
        utility=float(plan['replica']) * (plan['canonical_action'] == 'DOWN') + 1.) for plan in plans]
    choices = []
    for root in roots:
        for mode in (*audit.MODES, 'H2'):
            action = 'DOWN' if mode == 'PART_UTILITY_CONFIRMED' else 'LEFT'
            choices.append(dict(root_id=root['root_id'], life=root['life'], source_id=root['source_id'], mode=mode,
                canonical_action=action, actual_action=action, fallback=False,
                decision=dict(support=dict(complete=False), predicted_pairs={})))
    expected = audit.summarize(values, roots, choices, 1)
    assert audit._equal(runner.summarize(values, roots, choices, 1), expected)
    assert len(expected['comparisons']) == 6
    assert [row['contrast'] for row in expected['comparisons']] == list(audit.CONTRASTS)
    for row in expected['comparisons'][:2]:
        stat = row['metrics']['utility']
        assert stat['mean'] == 3.5 and stat['mean_variance'] == pytest.approx(.1875)
        assert stat['conditional_source_ci95'][0] > 0
    assert expected['progression']['status'] == 'PASS' and expected['progression']['retained_splits'] == 1
    collapsed = audit.summarize(values, roots, choices, 0)
    assert audit._equal(runner.summarize(values, roots, choices, 0), collapsed)
    assert collapsed['progression']['status'] == 'FAIL' and not collapsed['progression']['structure_eligible']
    missing = audit.summarize(values[:-1], roots, choices, 1)
    assert audit._equal(runner.summarize(values[:-1], roots, choices, 1), missing)
    assert not missing['complete'] and missing['progression']['status'] == 'HOLD'


def test_new_phase_streams_pair_actions_without_reusing_confirmation_or_old_validation_seeds():
    roots, _, _ = validation_fixture()
    for phase in ('CONFIRM_SOURCE', 'VALID_SOURCE'):
        assert audit.source_roster(phase) == runner.source_roster(phase)
        assert len(audit.source_roster(phase)) == 32
    for phase in ('CONFIRM', 'VALID'):
        roster = audit.forced_roster(roots, phase)
        assert roster == runner.branch_roster(roots, phase)
        for root in roots:
            seeds = []
            for suffix in range(4):
                paired = {row['seed'] for row in roster if row['root_id'] == root['root_id'] and row['suffix'] == suffix}
                assert len(paired) == 1
                seeds.append(next(iter(paired)))
            assert len(set(seeds)) == 4
    assert audit.seed('CONFIRM', 0, 1, 2, 3) != audit.seed('VALID', 0, 1, 2, 3)
    assert audit.seed('VALID', 0, 1, 2, 3) != audit.previous.seed('VALID', 0, 1, 2, 3)
    assert ROWS == []
