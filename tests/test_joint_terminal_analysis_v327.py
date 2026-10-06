"""Retained terminal labels cannot replace fresh utility or task retention evidence."""
import copy

import numpy as np
import pytest

import acfqp.science.joint_terminal_analysis_v327 as analysis


def test_prediction_metrics_keep_paired_return_and_win_errors():
    reward = np.asarray([2., 1.])
    win = np.asarray([.5, .5])
    target_reward = np.asarray([[2., 3., 4., 6.], [1., 3., 0., 0.]])
    target_win = np.asarray([[0., 1., 0., 1.], [0., 1., 0., 1.]])
    fit = analysis.prediction_metrics(reward, win, target_reward, target_win, (0, 1))
    validation = analysis.prediction_metrics(reward, win, target_reward, target_win, (2, 3))
    assert fit['members'] == [0, 1] and validation['members'] == [2, 3]
    assert fit['member_count'] == validation['member_count'] == 4
    assert fit['win_brier'] == validation['win_brier'] == .25
    expected = reward[:, None] - target_reward[:, :2] + 8. * (win[:, None] - target_win[:, :2])
    assert fit['utility_mse'] == float(np.mean(expected**2))
    assert fit['utility_mse'] != fit['reward_mse'] + 64. * fit['win_brier']


def test_prediction_members_are_fixed_and_unfinished_targets_are_not_imputed():
    reward, win = np.zeros(2), np.zeros(2)
    target_reward, target_win = np.zeros((2, 4)), np.zeros((2, 4))
    with pytest.raises(ValueError, match='frozen fit or validation'):
        analysis.prediction_metrics(reward, win, target_reward, target_win, (0, 2))
    target_reward[1, 3] = np.nan
    with pytest.raises(ValueError, match='unfinished terminal'):
        analysis.prediction_metrics(reward, win, target_reward, target_win, (0, 1))


def cohort():
    rows = []
    for life in range(16):
        initial, rounds = {}, {'1': {}, '2': {}}
        for task_index, task in enumerate(analysis.TASKS):
            belief = .21 if task == 'A' else .51
            teacher = dict(schema='acfqp.head_version.v313', head_kind='LOCAL_RISK', lifecycle=life,
                parent=life % 4, context_id=task_index, arm='FIRST_LOCAL', version=0,
                updates=1000+life, file=f'v326/life_{life}/{task}/FIRST_LOCAL_v0.npz', base_file=None)

            def evaluation(version, utility):
                return dict(estimated_p_four=belief, head_version=copy.deepcopy(version), planner='H2',
                    static_evaluation_valid=True, game_summaries=[dict(seed=analysis.EVALUATION_SEED+
                        life*1000000+task_index*100000+episode, utility=life+utility,
                        status='LOST') for episode in range(analysis.GAMES_PER_CELL)])

            def metrics(members, error=1.):
                return dict(rootgroups=analysis.GROUPS, members=list(members), member_count=analysis.GROUPS*2,
                    reward_mse=error, win_brier=.25, utility_mse=16.+error,
                    reward_bias=.1, win_bias=.01, utility_bias=.18,
                    error_unit='INDIVIDUAL_TERMINAL_SUFFIX_MEMBER', utility_rule='R_PLUS_8_TIMES_WIN_MINUS_HALF')

            def partition(error=1.):
                return dict(train=metrics((0, 1), error), validation=metrics((2, 3), error))

            initial[task] = dict(head_version=teacher, context_id=task_index,
                planning_belief=dict(estimated_p_four=belief),
                evaluations={'SOURCE': evaluation(None, 0.), 'FIRST_LOCAL': evaluation(teacher, 1.)})
            previous = {arm: teacher for arm in analysis.UPDATING_ARMS}
            for number in analysis.ROUNDS:
                arms = {}
                for arm in analysis.UPDATING_ARMS:
                    head = dict(teacher, arm=arm, version=int(number),
                        file=f'v327/life_{life}/{task}/{arm}_v{number}.npz', base_file=previous[arm]['file'],
                        updates=previous[arm]['updates']+analysis.FITTED_GROUPS,
                        reward_indices_count=0 if arm == 'WIN_ONLY' else 32)

                    def fit(groups):
                        joint = arm == 'JOINT_RETURN'
                        return dict(alpha=.0025, fitted_rootgroups=groups, replicates=2, reward_frozen=not joint,
                            learning_counts=dict(rootgroup_updates=groups, current_predictions=groups,
                                win_predictions=groups, reward_predictions=groups if joint else 0),
                            normalization_counts=dict(reward_parameter_writes=32*groups if joint else 0,
                                win_parameter_writes=32*groups))

                    receipt = fit(analysis.FITTED_GROUPS)
                    receipt.update(method='REPLAY_GROUPED_'+arm, distinct_rootgroups=analysis.GROUPS,
                        epochs=analysis.EPOCHS, epoch_receipts=[fit(analysis.GROUPS) for _ in range(analysis.EPOCHS)])
                    gain = int(number)*(1. if arm == 'JOINT_RETURN' else .5)
                    arms[arm] = dict(head_version=head, updates_before=previous[arm]['updates'],
                        updates_after=head['updates'], reward_unchanged=arm == 'WIN_ONLY', fit=receipt,
                        prediction_keys=dict(before='FIRST' if number == '1' else arm+'_BEFORE', after=arm+'_AFTER'),
                        prediction_metrics=dict(before=partition(), after=partition(.5)),
                        evaluations=evaluation(head, 1.+gain))
                    previous[arm] = head
                rounds[number][task] = dict(groups=analysis.GROUPS, replicas=4, epochs=16,
                    teacher_version=copy.deepcopy(teacher), first_unchanged=True, win_weights_identical=True,
                    fit_members=[0, 1], validation_members=[2, 3], arms=arms,
                    source_group_artifact=dict(file=f'v326/life_{life}/{task}/shared_{number}.npz'),
                    source_outcome_artifact=dict(file=f'v326/life_{life}/{task}/suffix_{number}.npz'),
                    terminal_status_counts=dict(WON=2048, LOST=2048, CUTOFF=0),
                    first_prediction_metrics=partition())
        rows.append(dict(lifecycle=life, parent=life % 4, initial=initial, rounds=rounds))
    return rows


def shift(rows, arm, amount, task=None):
    for row in rows:
        for name in analysis.TASKS if task is None else (task,):
            for game in row['rounds']['2'][name]['arms'][arm]['evaluations']['game_summaries']:
                game['utility'] += amount


def assert_hold(rows, kind, monkeypatch):
    monkeypatch.setattr(analysis, '_samples', lambda *_args: pytest.fail('Incomplete evidence cannot enter bootstrap'))
    result = analysis.summarize(rows, draws=20)
    assert result['primary_status'] == kind and result['primary'] is None
    assert not result['bootstrap_executed'] and not result['complete_retained_target_cohort']
    assert not result['retained_improvement_supported'] and not result['joint_reward_contribution_supported']
    assert result['fixed_teacher_regression_route'] == 'HOLD_INCOMPLETE_EVIDENCE'
    assert result['prediction_error_summary'] is None
    assert len(result['by_lifecycle']) == len(rows)
    return result


def test_primary_requires_own_first_gain_and_task_retention_before_confirmation():
    result = analysis.summarize(cohort(), draws=30)
    assert result['primary_contrast'] == 'JOINT_RETURN_minus_FIRST_LOCAL_FINAL_AB'
    assert result['primary']['mean'] == 2. and result['primary']['ci95'] == [2., 2.]
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['retained_improvement_supported'] and result['retained_joint_mechanism_supported']
    assert result['fixed_teacher_regression_route'] == 'ADVANCE_TO_NEW_COHORT_CONFIRMATION'
    assert result['final_ab_contrasts']['JOINT_RETURN_minus_WIN_ONLY']['mean'] == 1.
    assert result['final_ab_contrasts']['FIRST_LOCAL_minus_SOURCE']['mean'] == 1.
    assert result['physical_evaluation_games'] == 12288
    assert result['reused_terminal_supervision_members'] == 262144
    assert result['physical_new_terminal_supervision_members'] == result['new_training_raw_tiles'] == 0
    assert result['reused_target_cohort'] and not result['new_target_learning_histories']
    assert not result['independent_learning_confirmation'] and not result['independent_SOURCE']
    assert result['same_suffix_value_pairing'] and result['matched_optimization_quota']
    assert not result['equal_total_raw_efficiency_evaluated']
    cell = result['prediction_error_summary']['cells']['ROUND2_A']
    assert cell['arms']['JOINT_RETURN']['change']['validation']['reward_mse'] == -.5


def test_positive_average_cannot_override_one_task_loss():
    rows = cohort()
    shift(rows, 'JOINT_RETURN', 2., task='A')
    shift(rows, 'JOINT_RETURN', -3., task='B')
    result = analysis.summarize(rows, draws=20)
    assert result['primary_self_improvement_supported']
    assert result['task_retention_status']['B'] == 'SUPPORTED_LOSS'
    assert not result['retained_improvement_supported']
    assert result['fixed_teacher_regression_route'] == 'STOP_FIXED_FIRST_TERMINAL_REGRESSION'


def test_same_root_contribution_and_prediction_improvement_cannot_replace_net_gain():
    rows = cohort()
    shift(rows, 'JOINT_RETURN', -3.)
    shift(rows, 'WIN_ONLY', -4.)
    result = analysis.summarize(rows, draws=20)
    assert result['joint_reward_contribution_supported']
    assert result['primary_status'] == 'SUPPORTED_LOSS'
    assert result['prediction_error_summary']['cells']['ROUND2_A']['arms']['JOINT_RETURN']['change']['validation']['reward_mse'] < 0
    assert not result['retained_improvement_supported']
    assert result['fixed_teacher_regression_route'] == 'STOP_FIXED_FIRST_TERMINAL_REGRESSION'


def test_source_advantage_cannot_replace_incremental_first_improvement():
    rows = cohort()
    shift(rows, 'JOINT_RETURN', -2.)
    result = analysis.summarize(rows, draws=20)
    assert result['final_net_gain_status'] == 'SUPPORTED_GAIN'
    assert result['primary_status'] == 'UNRESOLVED'
    assert result['fixed_teacher_regression_route'] == 'STOP_FIXED_FIRST_TERMINAL_REGRESSION'


def test_unfinished_evaluation_is_retained_without_bootstrap(monkeypatch):
    rows = cohort()
    rows[3]['rounds']['2']['B']['arms']['JOINT_RETURN']['evaluations']['game_summaries'][2].update(status='CUTOFF', utility=None)
    result = assert_hold(rows, 'HOLD_CUTOFF', monkeypatch)
    assert not result['complete_game_endpoints'] and len(result['cutoffs']) == 1
    assert result['by_lifecycle'][3]['cells']['ROUND2_B']['JOINT_RETURN'] is None


def test_unfinished_retained_member_holds_all_inference(monkeypatch):
    rows = cohort()
    rows[2]['rounds']['1']['A']['terminal_status_counts'].update(WON=2048, LOST=2047, CUTOFF=1)
    result = assert_hold(rows, 'HOLD_TERMINAL_CUTOFF', monkeypatch)
    assert not result['complete_game_endpoints']
    assert result['terminal_cutoffs'] == [dict(lifecycle=2, task='A', round=1, count=1)]


def test_missing_lifecycle_or_stage_holds_without_replacement(monkeypatch):
    rows = cohort()
    assert_hold(rows[:15], 'HOLD_COHORT', monkeypatch)
    rows[2]['rounds']['1'].pop('A')
    assert_hold(rows, 'HOLD_CENSUS', monkeypatch)


@pytest.mark.parametrize('mutation', ['member_leak', 'win_mismatch', 'epoch_alpha', 'cross_arm_base', 'reward_write', 'old_eval_seed'])
def test_actual_intervention_contract_cannot_silently_change(mutation):
    rows = cohort()
    stage = rows[0]['rounds']['2']['A']
    if mutation == 'member_leak':
        stage['fit_members'] = [0, 2]
    elif mutation == 'win_mismatch':
        stage['win_weights_identical'] = False
    elif mutation == 'epoch_alpha':
        stage['arms']['JOINT_RETURN']['fit']['epoch_receipts'][5]['alpha'] = .003
    elif mutation == 'cross_arm_base':
        stage['arms']['JOINT_RETURN']['head_version']['base_file'] = rows[0]['rounds']['1']['A']['arms']['WIN_ONLY']['head_version']['file']
    elif mutation == 'reward_write':
        stage['arms']['WIN_ONLY']['head_version']['reward_indices_count'] = 1
    else:
        stage['arms']['JOINT_RETURN']['evaluations']['game_summaries'][0]['seed'] -= 10000000000
    with pytest.raises(ValueError, match='V327'):
        analysis.summarize(rows, draws=2)
