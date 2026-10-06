"""Reward-label efficacy does not substitute for own-FIRST growth or retention."""
import copy

import pytest

from acfqp.science.reward_targets_analysis_v321 import ARMS, INTERACTION, UPDATING_ARMS, summarize


def cohort():
    values = dict(SOURCE=0., FIRST_LOCAL=2., OLD_FACTUAL=2.5, OLD_QUERY=1.,
        NSTEP_FACTUAL=3., NSTEP_QUERY=4.)
    rows = []
    for life in range(16):
        initial, rounds, evaluations = {}, {'1': {}, '2': {}}, {}
        for task_index, task in enumerate(('A', 'B')):
            belief = .23 if task == 'A' else .73
            teacher = dict(file=f'v317/life_{life}/{task}/FIRST_LOCAL_v0.npz', version=0)
            initial[task] = dict(head_version=teacher, planning_belief=dict(estimated_p_four=belief))
            previous = {arm: teacher for arm in UPDATING_ARMS}
            for number in ('1', '2'):
                arms = {}
                for arm in UPDATING_ARMS:
                    head = dict(file=f'v321/life_{life}/{task}/{arm}_v{number}.npz',
                        version=int(number), base_file=previous[arm]['file'])
                    arms[arm] = dict(head_version=head,
                        fit=dict(alpha=.0025, learning_counts=dict(rootgroup_updates=16384)))
                    previous[arm] = head
                rounds[number][task] = dict(groups=16384, teacher_unchanged=True,
                    teacher_version=teacher, arms=arms)
            evaluations[task] = {arm: dict(estimated_p_four=belief,
                head_version=teacher if arm == 'FIRST_LOCAL' else previous.get(arm),
                game_summaries=[dict(seed=321900000000 + life * 1000000 + task_index * 100000 + episode,
                    utility=life + (100. if task == 'B' else 0.) + values[arm], status='LOST')
                    for episode in range(32)]) for arm in ARMS}
        rows.append(dict(lifecycle=life, parent=life % 4, initial=initial, rounds=rounds,
            final_evaluations=evaluations))
    return rows


def shift(rows, arm, amount, task=None):
    for row in rows:
        for name in ('A', 'B') if task is None else (task,):
            for game in row['final_evaluations'][name][arm]['game_summaries']:
                game['utility'] += amount


def test_two_by_two_label_contrasts_have_one_primary_and_all_6144_fresh_games():
    result = summarize(cohort(), draws=40)
    assert result['primary_contrast'] == 'NSTEP_QUERY_minus_OLD_QUERY_FINAL_AB'
    expected = dict(NSTEP_QUERY_minus_OLD_QUERY=3., NSTEP_QUERY_minus_FIRST_LOCAL=2.,
        NSTEP_QUERY_minus_SOURCE=4., NSTEP_QUERY_minus_NSTEP_FACTUAL=1.,
        NSTEP_FACTUAL_minus_OLD_FACTUAL=.5, OLD_FACTUAL_minus_FIRST_LOCAL=.5,
        OLD_QUERY_minus_FIRST_LOCAL=-1.)
    expected[INTERACTION] = 2.5
    assert {key: value['mean'] for key, value in result['final_ab_contrasts'].items()} == expected
    assert result['primary']['ci95'] == [3., 3.]
    assert result['primary_status'] == 'SUPPORTED_GAIN'
    assert result['primary_intervention_supported'] and result['retained_improvement_supported']
    assert result['repaired_query_supported']
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['physical_evaluation_games'] == 6144 and result['complete_game_endpoints']
    assert result['bootstrap_seed'] == 32100001 and result['bootstrap_draws'] == 40
    assert result['bootstrap_executed']
    assert result['primary']['positive_equal_negative'] == [16, 0, 0]
    assert result['primary']['parent_mean_values'] == {str(parent): 3. for parent in range(4)}
    assert 'are not terminal truth' in result['evidence_scope']
    assert 'lifecycle rather than individual games' in result['evidence_scope']


@pytest.mark.parametrize('case', ['label_gain_without_growth', 'growth_without_label_gain',
    'b_loss', 'negative_source', 'zero_retention', 'negative_primary'])
def test_label_gain_growth_task_retention_and_source_comparisons_remain_separate(case):
    rows = cohort()
    if case == 'label_gain_without_growth':
        shift(rows, 'NSTEP_QUERY', -2.)
    elif case == 'growth_without_label_gain':
        shift(rows, 'OLD_QUERY', 3.)
    elif case == 'b_loss':
        shift(rows, 'NSTEP_QUERY', 3., task='A')
        shift(rows, 'NSTEP_QUERY', -3., task='B')
    elif case == 'negative_source':
        shift(rows, 'SOURCE', 7.)
    elif case == 'zero_retention':
        shift(rows, 'NSTEP_QUERY', -2., task='B')
    else:
        shift(rows, 'NSTEP_QUERY', -4.)
    result = summarize(rows, draws=20)
    if case == 'label_gain_without_growth':
        assert result['primary_intervention_supported']
        assert result['primary_self_improvement_status'] == 'UNRESOLVED'
        assert not result['retained_improvement_supported'] and not result['repaired_query_supported']
    elif case == 'growth_without_label_gain':
        assert result['primary_status'] == 'UNRESOLVED'
        assert result['retained_improvement_supported'] and not result['repaired_query_supported']
    elif case == 'b_loss':
        assert result['primary_intervention_supported'] and result['primary_self_improvement_supported']
        assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_LOSS')
        assert not result['retained_improvement_supported'] and not result['repaired_query_supported']
    elif case == 'negative_source':
        assert result['repaired_query_supported'] and result['final_net_gain_status'] == 'SUPPORTED_LOSS'
    elif case == 'zero_retention':
        assert result['task_contrasts']['B']['NSTEP_QUERY_minus_FIRST_LOCAL']['ci95'] == [0., 0.]
        assert result['task_retention_status']['B'] == 'SUPPORTED_NONDECREASE'
        assert result['repaired_query_supported']
    else:
        assert result['primary_status'] == 'SUPPORTED_LOSS'
        assert result['primary_self_improvement_status'] == 'SUPPORTED_LOSS'
        assert not result['repaired_query_supported']


def test_interaction_cannot_be_substituted_for_the_query_label_intervention():
    rows = cohort()
    shift(rows, 'NSTEP_FACTUAL', 4.)
    result = summarize(rows, draws=20)
    assert result['primary']['mean'] == 3. and result['primary_intervention_supported']
    assert result['final_ab_contrasts'][INTERACTION]['mean'] == -1.5
    assert result['interaction_status'] == 'SUPPORTED_LOSS'
    assert result['repaired_query_supported']


def test_cutoff_keeps_all_rows_and_games_but_executes_no_terminal_bootstrap():
    rows = cohort()
    game = rows[6]['final_evaluations']['A']['OLD_FACTUAL']['game_summaries'][3]
    game.update(status='CUTOFF', utility=-100.)
    result = summarize(rows, draws=20)
    assert not result['complete_game_endpoints'] and not result['bootstrap_executed']
    assert result['physical_evaluation_games'] == 6144 and len(result['by_lifecycle']) == 16
    assert result['cutoffs'] == [dict(lifecycle=6, task='A', arm='OLD_FACTUAL', seed=321906000003)]
    assert result['by_lifecycle'][6]['retained_endpoint_counts']['A']['OLD_FACTUAL']['CUTOFF'] == 1
    assert result['primary'] is None
    assert all(value is None for value in result['final_ab_contrasts'].values())
    assert all(value is None for task in result['task_contrasts'].values() for value in task.values())
    for key in ('primary_status', 'primary_self_improvement_status', 'final_net_gain_status',
            'factual_intervention_status', 'interaction_status'):
        assert result[key] == 'HOLD_CUTOFF'
    assert result['task_retention_status'] == dict(A='HOLD_CUTOFF', B='HOLD_CUTOFF')
    for key in ('primary_intervention_supported', 'primary_self_improvement_supported',
            'retained_improvement_supported', 'repaired_query_supported'):
        assert not result[key]


@pytest.mark.parametrize('case', ['teacher', 'base', 'alpha', 'quota', 'groups', 'missing_update_arm',
    'missing_evaluation_arm', 'extra_evaluation_arm', 'seed', 'belief', 'missing_game', 'eval_head', 'status'])
def test_missing_pairing_or_changed_learner_contract_raises(case):
    rows = cohort()
    stage = rows[0]['rounds']['2']['B']
    evaluation = rows[0]['final_evaluations']['B']['NSTEP_QUERY']
    if case == 'teacher':
        stage['teacher_version'] = dict(stage['teacher_version'], file='updated_teacher.npz')
    elif case == 'base':
        stage['arms']['NSTEP_QUERY']['head_version']['base_file'] = stage['arms']['OLD_QUERY']['head_version']['file']
    elif case == 'alpha':
        stage['arms']['NSTEP_QUERY']['fit']['alpha'] = .005
    elif case == 'quota':
        stage['arms']['NSTEP_QUERY']['fit']['learning_counts']['rootgroup_updates'] = 16383
    elif case == 'groups':
        stage['groups'] = 16383
    elif case == 'missing_update_arm':
        del stage['arms']['OLD_FACTUAL']
    elif case == 'missing_evaluation_arm':
        del rows[0]['final_evaluations']['B']['OLD_FACTUAL']
    elif case == 'extra_evaluation_arm':
        rows[0]['final_evaluations']['B']['EXTRA'] = copy.deepcopy(evaluation)
    elif case == 'seed':
        evaluation['game_summaries'][0]['seed'] = 319900100000
    elif case == 'belief':
        evaluation['estimated_p_four'] = .5
    elif case == 'missing_game':
        evaluation['game_summaries'].pop()
    elif case == 'eval_head':
        evaluation['head_version'] = rows[0]['initial']['B']['head_version']
    else:
        evaluation['game_summaries'][0]['status'] = 'TRUNCATED'
    with pytest.raises(ValueError, match='V321'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'wrong_parent'])
def test_required_sixteen_lifecycles_cannot_be_replaced_by_a_selected_cohort(case):
    rows = cohort()
    if case == 'missing':
        rows.pop()
    elif case == 'duplicate':
        rows[-1]['lifecycle'] = 0
    else:
        rows[0]['parent'] = 1
    with pytest.raises(ValueError, match='all sixteen FIRST lifecycles'):
        summarize(rows, draws=2)


def test_bootstrap_conditions_on_each_fixed_parent_and_uses_common_covarying_draws():
    rows = cohort()
    for row in rows:
        for task in ('A', 'B'):
            for game in row['final_evaluations'][task]['NSTEP_QUERY']['game_summaries']:
                game['utility'] += row['parent']
    result = summarize(list(reversed(rows)), draws=40)
    primary = result['primary']
    assert primary['mean'] == 4.5 and primary['ci95'] == [4.5, 4.5]
    assert primary['parent_mean_values'] == {str(parent): 3. + parent for parent in range(4)}
    assert list(primary['lifecycle_values']) == [str(life) for life in range(16)]
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REUSED_FIRST_COHORT'

    rows = cohort()
    for row in rows:
        for task in ('A', 'B'):
            bump = (row['lifecycle'] // 4 - 1.5) * 3.
            for arm in ('NSTEP_QUERY', 'NSTEP_FACTUAL'):
                for game in row['final_evaluations'][task][arm]['game_summaries']:
                    game['utility'] += bump
    result = summarize(rows, draws=40)
    assert result['primary']['ci95'][0] != result['primary']['ci95'][1]
    assert result['final_ab_contrasts'][INTERACTION]['ci95'] == [2.5, 2.5]
