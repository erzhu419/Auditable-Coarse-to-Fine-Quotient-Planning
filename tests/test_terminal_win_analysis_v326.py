"""Terminal labels do not replace own-FIRST utility, task retention or complete histories."""
import copy

import pytest

import acfqp.science.terminal_win_analysis_v326 as analysis


def cohort():
    rows = []
    for life in range(16):
        initial, rounds = {}, {'1': {}, '2': {}}
        for task_index, task in enumerate(analysis.TASKS):
            belief = .21 if task == 'A' else .51
            teacher = dict(schema='acfqp.head_version.v313', head_kind='LOCAL_RISK', lifecycle=life,
                parent=life % 4, context_id=task_index, arm='FIRST_LOCAL', version=0,
                updates=1000 + life, file=f'v326/life_{life}/{task}/FIRST_LOCAL_v0.npz', base_file=None)

            def evaluation(version, utility):
                return dict(estimated_p_four=belief, head_version=copy.deepcopy(version), planner='H2',
                    static_evaluation_valid=True, game_summaries=[dict(seed=analysis.EVALUATION_SEED +
                        life * 1000000 + task_index * 100000 + episode, utility=life + utility,
                        status='LOST') for episode in range(analysis.GAMES_PER_CELL)])

            initial[task] = dict(head_version=teacher, head_versions={'FIRST_LOCAL': copy.deepcopy(teacher)},
                context_id=task_index, planning_belief=dict(estimated_p_four=belief),
                acquisition=dict(warmup=dict(game_summaries=[dict(episode=0, status='LOST')])),
                dataset=dict(games=[dict(episode=1, status='LOST', split='FIT')]),
                evaluations={'SOURCE': evaluation(None, 0.), 'FIRST_LOCAL': evaluation(teacher, 1.)})
            previous = {arm: teacher for arm in analysis.UPDATING_ARMS}
            for number in analysis.ROUNDS:
                artifact = dict(file=f'v326/life_{life}/{task}/shared_{number}.npz')
                arms = {}
                for arm in analysis.UPDATING_ARMS:
                    head = dict(teacher, arm=arm, version=int(number),
                        file=f'v326/life_{life}/{task}/{arm}_v{number}.npz', base_file=previous[arm]['file'],
                        updates=previous[arm]['updates'] + analysis.FITTED_GROUPS, reward_indices_count=0)

                    def fit(groups):
                        return dict(alpha=.0025, fitted_rootgroups=groups, replicates=4, reward_frozen=True,
                            learning_counts=dict(rootgroup_updates=groups, current_predictions=groups,
                                win_predictions=groups), normalization_counts=dict(win_parameter_writes=groups))

                    receipt = fit(analysis.FITTED_GROUPS)
                    receipt.update(method='REPLAY_GROUPED_WIN_ONLY_LOCAL', distinct_rootgroups=analysis.GROUPS,
                        epochs=analysis.EPOCHS, epoch_receipts=[fit(analysis.GROUPS) for _ in range(analysis.EPOCHS)])
                    gain = int(number) * (1. if arm == 'TERMINAL_WIN' else .5)
                    arms[arm] = dict(head_version=head, updates_before=previous[arm]['updates'],
                        updates_after=head['updates'], reward_unchanged=True, fit=receipt,
                        supervision=dict(group_artifact=copy.deepcopy(artifact), target_field=analysis.TARGET_FIELDS[arm]),
                        evaluations=evaluation(head, 1. + gain))
                    previous[arm] = head
                rounds[number][task] = dict(groups=analysis.GROUPS, replicas=4, teacher_version=copy.deepcopy(teacher),
                    teacher_unchanged=True, census=dict(selected_groups=analysis.GROUPS), arms=arms,
                    shared_supervision=dict(group_artifact=artifact),
                    continuation=dict(outcome_artifact=dict(file=f'v326/life_{life}/{task}/suffix_{number}.npz')),
                    terminal_status_counts=dict(WON=2048, LOST=2048, CUTOFF=0),
                    collectors={'FIXED_FIRST': dict(dataset=dict(games=[dict(episode=0, status='LOST')]))})
        rows.append(dict(lifecycle=life, parent=life % 4, initial_context_precondition_met=True,
            initial=initial, rounds=rounds))
    return rows


def shift(rows, arm, amount, task=None):
    for row in rows:
        for name in analysis.TASKS if task is None else (task,):
            for game in row['rounds']['2'][name]['arms'][arm]['evaluations']['game_summaries']:
                game['utility'] += amount


def assert_hold(rows, kind, monkeypatch):
    monkeypatch.setattr(analysis, '_samples', lambda *_args: pytest.fail('Incomplete observations cannot enter bootstrap'))
    result = analysis.summarize(rows, draws=20)
    assert result['primary_status'] == kind and result['primary'] is None
    assert not result['bootstrap_executed'] and not result['complete_target_learning_cohort']
    assert not result['retained_improvement_supported'] and not result['terminal_target_contribution_supported']
    assert len(result['by_lifecycle']) == len(rows)
    assert all(value is None for values in result['task_contrasts'].values() for value in values.values())
    return result


def test_primary_terminal_first_and_same_root_target_contribution_are_separate():
    result = analysis.summarize(cohort(), draws=30)
    assert result['primary_contrast'] == 'TERMINAL_WIN_minus_FIRST_LOCAL_FINAL_AB'
    assert result['primary']['mean'] == 2. and result['primary']['ci95'] == [2., 2.]
    assert result['retained_improvement_supported'] and result['retained_terminal_mechanism_supported']
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['final_ab_contrasts']['TERMINAL_WIN_minus_BOOTSTRAP_WIN']['mean'] == 1.
    assert result['final_ab_contrasts']['FIRST_LOCAL_minus_SOURCE']['mean'] == 1.
    assert result['round_ab_contrasts']['1']['TERMINAL_WIN_minus_FIRST_LOCAL']['mean'] == 1.
    assert result['physical_evaluation_games'] == 12288 and result['physical_terminal_supervision_members'] == 262144
    assert result['new_target_learning_histories'] and not result['independent_SOURCE']
    assert result['same_root_target_ablation'] and result['matched_optimization_quota']
    assert not result['equal_total_raw_efficiency_evaluated'] and result['bootstrap_seed'] == 32600001


def test_positive_average_cannot_override_actual_task_loss():
    rows = cohort()
    shift(rows, 'TERMINAL_WIN', 2., task='A')
    shift(rows, 'TERMINAL_WIN', -3., task='B')
    result = analysis.summarize(rows, draws=20)
    assert result['primary_self_improvement_supported']
    assert result['task_retention_status']['B'] == 'SUPPORTED_LOSS'
    assert not result['retained_improvement_supported'] and not result['retained_terminal_mechanism_supported']


def test_terminal_target_gain_cannot_override_negative_net_learning():
    rows = cohort()
    shift(rows, 'TERMINAL_WIN', -3.)
    shift(rows, 'BOOTSTRAP_WIN', -4.)
    result = analysis.summarize(rows, draws=20)
    assert result['terminal_target_contribution_supported']
    assert result['primary_status'] == 'SUPPORTED_LOSS'
    assert not result['retained_improvement_supported'] and not result['retained_terminal_mechanism_supported']


def test_terminal_cutoff_preserves_provisional_stage_and_holds_every_interval(monkeypatch):
    rows = cohort()
    row = rows[5]
    stage = row['rounds']['1']['A']
    stage['terminal_status_counts'] = dict(WON=2048, LOST=2047, CUTOFF=1)
    stage['shared_supervision'] = dict(provisional=True)
    stage.pop('arms')
    row['rounds']['1'].pop('B')
    row['rounds'].pop('2')
    row['failure'] = dict(kind='HOLD_TERMINAL_CUTOFF', task='A', round=1, reason='Retained actual suffix cutoff')
    result = assert_hold(rows, 'HOLD_TERMINAL_CUTOFF', monkeypatch)
    assert result['terminal_cutoffs'] == [dict(lifecycle=5, task='A', round=1, count=1)]
    assert not result['complete_game_endpoints'] and result['physical_evaluation_games'] == 11776


def test_unfinished_evaluation_is_not_imputed_or_resampled(monkeypatch):
    rows = cohort()
    game = rows[3]['rounds']['2']['B']['arms']['TERMINAL_WIN']['evaluations']['game_summaries'][2]
    game.update(status='CUTOFF', utility=None)
    result = assert_hold(rows, 'HOLD_CUTOFF', monkeypatch)
    assert not result['complete_game_endpoints'] and len(result['cutoffs']) == 1
    assert result['by_lifecycle'][3]['cells']['ROUND2_B']['TERMINAL_WIN'] is None


def test_training_cutoff_holds_inference_even_if_all_evaluations_finish(monkeypatch):
    rows = cohort()
    rows[2]['rounds']['1']['A']['collectors']['FIXED_FIRST']['dataset']['games'][0]['status'] = 'CUTOFF'
    result = assert_hold(rows, 'HOLD_TRAINING_CUTOFF', monkeypatch)
    assert not result['complete_game_endpoints'] and result['physical_evaluation_games'] == 12288


def test_missing_census_keeps_completed_lives_without_replacement(monkeypatch):
    rows = cohort()
    rows[2]['rounds']['1']['A']['census']['selected_groups'] -= 1
    result = assert_hold(rows, 'HOLD_CENSUS', monkeypatch)
    assert result['physical_evaluation_games'] == 12288 and result['complete_game_endpoints']


def test_terminal_arm_cannot_accidentally_read_teacher_target_field():
    rows = cohort()
    rows[0]['rounds']['1']['B']['arms']['TERMINAL_WIN']['supervision']['target_field'] = 'targetwin'
    with pytest.raises(ValueError, match='declared label fields'):
        analysis.summarize(rows, draws=2)


def test_replay_cannot_silently_change_epoch_quota_or_epoch_alpha():
    for mutation in ('epoch_quota', 'epoch_alpha'):
        rows = cohort()
        fit = rows[0]['rounds']['1']['B']['arms']['TERMINAL_WIN']['fit']
        if mutation == 'epoch_quota':
            fit['epochs'] -= 1
        else:
            fit['epoch_receipts'][5]['alpha'] = .003
        with pytest.raises(ValueError, match='V326'):
            analysis.summarize(rows, draws=2)


def test_learner_head_cannot_rebase_on_other_arm_or_modify_reward():
    for mutation in ('other_arm_base', 'reward_delta'):
        rows = cohort()
        item = rows[0]['rounds']['2']['A']['arms']['TERMINAL_WIN']
        if mutation == 'other_arm_base':
            item['head_version']['base_file'] = rows[0]['rounds']['1']['A']['arms']['BOOTSTRAP_WIN']['head_version']['file']
        else:
            item['head_version']['reward_indices_count'] = 1
        with pytest.raises(ValueError, match='V326'):
            analysis.summarize(rows, draws=2)
