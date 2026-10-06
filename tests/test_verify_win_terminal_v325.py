"""Concrete V325 root/member calibration, readonly native work and frozen-inference failures."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_win_terminal_v325 as audit
from acfqp.science.win_terminal_analysis_v325 import summarize
from test_win_terminal_analysis_v325 import cohort


def test_actual_fixed_grid_fresh_seed_and_frozen_reader_contract():
    indices = audit.selected_groups()
    assert len(indices) == 64 and indices[0] == 0 and indices[-1] == 16383
    assert np.all(np.diff(indices) > 0)
    assert audit.continuation_seed(15, 'B', 2, 16383, 3) == 325651265535
    from acfqp.science.win_terminal_run_v325 import configuration
    source = ROOT/'reports/win_learning_v324/summary.json'
    assert audit.expected_configuration(source) == configuration(source)


def test_independent_scalar_moments_keep_root_and_conditional_member_targets_distinct():
    groups = cohort()[0]['stages']['1']['A']['arms']['QUERY_WIN']['groups']
    actual = audit.scalar_moments(groups)
    assert actual['root_prediction']['FIRST']['brier'] == .0625
    assert actual['root_prediction']['FINAL']['brier'] == .25
    assert actual['member_teacher']['brier'] == .5625
    assert actual['root_brier_change']['FINAL_minus_FIRST'] == .1875
    for group in groups:
        group['replicas'][0].update(actual_win=1, status='WON')
    actual = audit.scalar_moments(groups)
    assert actual['terminal_win_rate'] == .25
    assert actual['root_prediction']['FIRST']['brier'] == .1875
    assert actual['root_brier_change']['FINAL_minus_FIRST'] == .0625


@pytest.fixture(scope='module')
def complete():
    rows = cohort()
    # Different histories, task/round cells and member outcomes expose weight or pairing errors.
    for row in rows:
        for number in ('1', '2'):
            for task in ('A', 'B'):
                for arm in audit.ARMS:
                    groups = row['stages'][number][task]['arms'][arm]['groups']
                    for index, group in enumerate(groups):
                        first = .125+(row['lifecycle'] % 4)*.0625
                        updated = first+(.125 if arm == 'QUERY_WIN' else -.0625)
                        group['predictions'].update(FIRST=first, before=first if number == '1' else updated,
                            after=updated, FINAL=updated)
                        for member, value in enumerate(group['replicas']):
                            won = int((index+member+row['lifecycle']+(task == 'B')+int(number)) % 4 == 0)
                            value.update(actual_win=won, status='WON' if won else 'LOST')
    return rows, summarize(rows)


def test_all_actual_brier_bias_and_frozen_secondary_vectors_agree(complete):
    rows, result = complete
    audit.check_analysis(result, rows)


@pytest.mark.parametrize('case', ['root_moment', 'member_moment', 'primary_source', 'primary_mean',
    'primary_status', 'lifecycle_value', 'parent_value', 'direction_count', 'interval_scope',
    'interval_feasible', 'seed', 'draws', 'physical_rollouts', 'grid', 'secondary'])
def test_wrong_diagnostic_weight_scope_primary_or_truth_is_rejected(complete, case):
    rows, original = complete; result = deepcopy(original)
    if case == 'root_moment': result['by_lifecycle'][0]['cells']['R1_A']['QUERY_WIN']['root_prediction']['FIRST']['brier'] += .01
    elif case == 'member_moment': result['by_lifecycle'][0]['cells']['R1_A']['QUERY_WIN']['member_teacher']['brier'] += .01
    elif case == 'primary_source': result['primary'] = deepcopy(result['overall']['root_brier_change']['FACTUAL_WIN']['FINAL_minus_FIRST'])
    elif case == 'primary_mean': result['primary']['mean'] += .01
    elif case == 'primary_status': result['primary_status'] = 'SUPPORTED_GAIN'
    elif case == 'lifecycle_value': result['overall']['terminal_win_rate']['QUERY_WIN']['lifecycle_values']['0'] += .01
    elif case == 'parent_value': result['overall']['terminal_win_rate']['QUERY_WIN']['parent_mean_values']['0'] += .01
    elif case == 'direction_count': result['overall']['terminal_win_rate']['QUERY_WIN']['positive_equal_negative'][0] -= 1
    elif case == 'interval_scope': result['overall']['terminal_win_rate']['QUERY_WIN']['interval_scope'] = 'INDEPENDENT_LEARNING_CONFIRMATION'
    elif case == 'interval_feasible': result['overall']['terminal_win_rate']['QUERY_WIN']['ci95'] = [-1., 1.]
    elif case == 'seed': result['bootstrap_seed'] += 1
    elif case == 'draws': result['bootstrap_draws'] += 1
    elif case == 'physical_rollouts': result['physical_conditional_rollouts'] -= 1
    elif case == 'grid': result['selected_group_indices'] = list(range(64))
    else: result['by_stage'].pop('R2_B')
    with pytest.raises(ValueError): audit.check_analysis(result, rows)


def test_single_cutoff_holds_all_root_and_teacher_inference_without_imputation():
    rows = cohort(); rows[3]['stages']['2']['B']['arms']['QUERY_WIN']['groups'][1]['replicas'][2].update(
        status='CUTOFF', actual_win=None)
    result = summarize(rows)
    audit.check_analysis(result, rows)
    result['overall'] = {}
    with pytest.raises(ValueError, match='suppresses every terminal statistic'):
        audit.check_analysis(result, rows)


def prediction_work():
    n = 64
    return dict(roots=n, updates_before=13, updates_after=13, readonly=True,
        prediction_rule='ACTUAL_V301_NATIVE_COMPONENT_PREDICTOR_UNCHANGED_STABLE_SIGMOID',
        counts=dict(win_predictions=n,reward_predictions=n,win_table_lookups=32*n,reward_table_lookups=32*n,
            feature_extractions=n,feature_occurrences=32*n,feature_digit_reads=192*n,
            feature_address_multiply_adds=192*n,fit_updates=0,parameter_writes=0),
        representation_counts=dict(risk_sigmoid_evaluations=n,local_risk_table_lookups=32*n,
            combined_value_additions=2*n,combined_value_multiplications=n), cpu_seconds=.01,seconds=.01)


def test_actual_native_predictor_reward_reads_are_charged_despite_win_only_statistic():
    audit.check_prediction_work(prediction_work(), {'updates':13})


@pytest.mark.parametrize('case', ['reward_reads', 'win_reads', 'fitting', 'parameter_writes',
    'updates', 'readonly', 'combined_work', 'timing'])
def test_unpaid_prediction_work_or_changed_head_is_rejected(case):
    value = prediction_work()
    if case == 'reward_reads': value['counts']['reward_table_lookups'] = 0
    elif case == 'win_reads': value['counts']['win_table_lookups'] += 1
    elif case == 'fitting': value['counts']['fit_updates'] = 1
    elif case == 'parameter_writes': value['counts']['parameter_writes'] = 1
    elif case == 'updates': value['updates_after'] += 1
    elif case == 'readonly': value['readonly'] = False
    elif case == 'combined_work': value['representation_counts']['combined_value_additions'] = 0
    else: value['cpu_seconds'] = -1.
    with pytest.raises(ValueError): audit.check_prediction_work(value, {'updates':13})


def test_all_saved_actual_root_snapshots_use_literal_occurrences_and_stable_sigmoid():
    # Only four addresses are needed for these supported zero/nonwinning roots.
    size = 4*11**6; zero = np.zeros(size); terminal = [np.zeros(size) for _ in range(3)]
    roots = np.zeros((64,16), dtype=np.int32)
    for index, weights in enumerate(terminal): weights[np.arange(4)*11**6] = index*.0625
    heads = {label:SimpleNamespace(reward=zero,terminal=weights) for label,weights in zip(audit.SNAPSHOTS,terminal)}
    expected = [audit.literal_root_predictions(roots, heads[label]) for label in audit.SNAPSHOTS]
    arrays = dict(roots=roots,prediction_probabilities=np.asarray([value['win'] for value in expected]),
        prediction_logits=np.asarray([value['logit'] for value in expected]))
    audit.check_root_predictions(arrays, heads)
    arrays['prediction_probabilities'][1,0] = .5
    with pytest.raises(ValueError,match='literal actual immutable head'):
        audit.check_root_predictions(arrays, heads)
    arrays['prediction_probabilities'][1,0] = expected[1]['win'][0]
    arrays['prediction_logits'][2,0] += 1.
    with pytest.raises(ValueError,match='literal actual immutable head'):
        audit.check_root_predictions(arrays, heads)
