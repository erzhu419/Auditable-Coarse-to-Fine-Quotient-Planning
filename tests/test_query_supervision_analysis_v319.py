"""Paired query-coverage evidence has separate growth and retention rules."""
import pytest

from acfqp.science.query_supervision_analysis_v319 import summarize


def evaluated(life, task, value, p, version=None):
    return dict(estimated_p_four=p, head_version=version, game_summaries=[dict(
        seed=319900000000+life*1000000+(100000 if task=='B' else 0)+episode,
        utility=life+(100. if task=='B' else 0.)+value, status='LOST', steps=episode+1)
        for episode in range(32)])


def cohort():
    rows = []
    for life in range(16):
        initial, rounds = {}, {'1':{}, '2':{}}
        for task in ('A','B'):
            p = .23 if task=='A' else .73
            teacher = dict(file=f'v317/life_{life}/{task}/FIRST_LOCAL_v0.npz',
                version=0, updates=10)
            initial[task] = dict(head_version=teacher, planning_belief=dict(estimated_p_four=p),
                evaluations=dict(SOURCE=evaluated(life,task,0.,p),
                    FIRST_LOCAL=evaluated(life,task,2.,p,teacher)))
            previous = dict(FACTUAL_LOCAL=teacher,QUERY_LOCAL=teacher)
            for number in (1,2):
                arms = {}
                for arm,value in dict(FACTUAL_LOCAL=2.5 if number==1 else 3.,
                        QUERY_LOCAL=3. if number==1 else 4.).items():
                    version = dict(file=f'v319/life_{life}/{task}/{arm}_v{number}.npz',
                        version=number, updates=10+3*number, base_file=previous[arm]['file'])
                    fit = dict(alpha=.0025, learning_counts=dict(rootgroup_updates=3))
                    arms[arm] = dict(fit=fit,head_version=version,
                        evaluations=evaluated(life,task,value,p,version))
                    previous[arm] = version
                rounds[str(number)][task] = dict(groups=3,teacher_unchanged=True,
                    teacher_version=teacher,arms=arms)
        rows.append(dict(lifecycle=life,parent=life%4,initial=initial,rounds=rounds))
    return rows


def final(row, task, arm='QUERY_LOCAL'):
    return row['rounds']['2'][task]['arms'][arm]['evaluations']


def shift(evaluation, amount):
    for game in evaluation['game_summaries']:
        game['utility'] += amount


def test_six_paired_contrasts_rounds_and_6144_games_use_the_new_actual_schema():
    rows = cohort()
    result = summarize(rows,draws=40)
    expected = dict(QUERY_LOCAL_minus_FIRST_LOCAL=2.,QUERY_LOCAL_minus_FACTUAL_LOCAL=1.,
        QUERY_LOCAL_minus_SOURCE=4.,FACTUAL_LOCAL_minus_FIRST_LOCAL=1.,
        FACTUAL_LOCAL_minus_SOURCE=3.,FIRST_LOCAL_minus_SOURCE=2.)
    assert {key:value['mean'] for key,value in result['final_ab_contrasts'].items()} == expected
    assert result['primary_contrast'] == 'QUERY_LOCAL_minus_FIRST_LOCAL_FINAL_AB'
    assert result['primary_self_improvement_supported'] and result['coverage_intervention_supported']
    assert result['retained_improvement_supported'] and result['coverage_mechanism_supported']
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE',B='SUPPORTED_NONDECREASE')
    assert result['round_ab_contrasts']['1']['QUERY_LOCAL_minus_FIRST_LOCAL']['mean'] == 1.
    assert result['round_ab_contrasts']['1']['QUERY_LOCAL_minus_FACTUAL_LOCAL']['mean'] == .5
    assert result['checkpoint_contrasts']['ROUND2_B']['FACTUAL_LOCAL']['mean'] == 1.
    assert result['task_contrasts']['ROUND2_A']['QUERY_LOCAL_minus_SOURCE']['mean'] == 4.
    assert result['complete_game_endpoints'] and result['physical_evaluation_games'] == 6144
    assert [row['lifecycle'] for row in result['by_lifecycle']] == list(range(16))
    assert result['bootstrap_seed'] == 31900001 and result['bootstrap_draws'] == 40
    scope = result['evidence_scope']
    assert 'existing sixteen-life FIRST cohort' in scope
    assert 'four frozen SOURCE parents' in scope and 'bootstrapped, not terminal truth' in scope
    assert 'actual address writes and compute can differ' in scope


@pytest.mark.parametrize('case',['coverage_without_growth','growth_without_coverage',
    'b_loss','negative_source','negative_primary'])
def test_growth_coverage_both_task_retention_and_source_are_distinct(case):
    rows = cohort()
    for row in rows:
        for task in ('A','B'):
            if case == 'coverage_without_growth':
                shift(final(row,task),-2.)
                shift(final(row,task,'FACTUAL_LOCAL'),-2.)
            elif case == 'growth_without_coverage':
                shift(final(row,task,'FACTUAL_LOCAL'),1.)
            elif case == 'b_loss':
                shift(final(row,task),3. if task=='A' else -3.)
            elif case == 'negative_source':
                shift(row['initial'][task]['evaluations']['SOURCE'],7.)
            else:
                shift(final(row,task),-3.)
    result = summarize(rows,draws=20)
    if case == 'coverage_without_growth':
        assert result['coverage_intervention_supported'] and result['final_net_gain_status'] == 'SUPPORTED_GAIN'
        assert result['primary_self_improvement_status'] == 'UNRESOLVED'
        assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE',B='SUPPORTED_NONDECREASE')
        assert not result['retained_improvement_supported'] and not result['coverage_mechanism_supported']
    elif case == 'growth_without_coverage':
        assert result['primary_self_improvement_supported'] and result['retained_improvement_supported']
        assert result['coverage_intervention_status'] == 'UNRESOLVED'
        assert not result['coverage_mechanism_supported']
    elif case == 'b_loss':
        assert result['primary_self_improvement_supported'] and result['coverage_intervention_supported']
        assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE',B='SUPPORTED_LOSS')
        assert result['checkpoint_contrasts']['ROUND2_B']['QUERY_LOCAL']['ci95'] == [-1.,-1.]
        assert not result['retained_improvement_supported'] and not result['coverage_mechanism_supported']
    elif case == 'negative_source':
        assert result['retained_improvement_supported'] and result['coverage_mechanism_supported']
        assert result['final_net_gain_status'] == 'SUPPORTED_LOSS'
    else:
        assert result['primary_self_improvement_status'] == 'SUPPORTED_LOSS'
        assert result['coverage_intervention_status'] == 'SUPPORTED_LOSS'
        assert result['final_ab_contrasts']['QUERY_LOCAL_minus_FIRST_LOCAL']['ci95'] == [-1.,-1.]
        assert not result['retained_improvement_supported']


def test_cutoff_holds_all_support_claims_without_dropping_the_lifecycle_or_game():
    rows = cohort()
    game = final(rows[6],'A')['game_summaries'][3]
    game.update(status='CUTOFF',utility=-100.)
    result = summarize(rows,draws=20)
    assert not result['complete_game_endpoints'] and result['physical_evaluation_games'] == 6144
    assert len(result['by_lifecycle']) == 16
    assert result['by_lifecycle'][6]['cells']['ROUND2_A']['QUERY_LOCAL'] != 10.
    assert result['cutoffs'] == [dict(lifecycle=6,task='A',arm='QUERY_LOCAL',
        checkpoint='ROUND2',seed=319906000003)]
    for key in ('primary_self_improvement_status','coverage_intervention_status',
            'factual_self_improvement_status','final_net_gain_status'):
        assert result[key] == 'HOLD_CUTOFF'
    assert result['task_retention_status'] == dict(A='HOLD_CUTOFF',B='HOLD_CUTOFF')
    for key in ('primary_self_improvement_supported','coverage_intervention_supported',
            'retained_improvement_supported','coverage_mechanism_supported'):
        assert not result[key]


@pytest.mark.parametrize('case',['teacher','seed','belief','base','groups'])
def test_wrong_actual_teacher_pairing_private_base_or_rootgroup_quota_raises(case):
    rows = cohort()
    stage = rows[0]['rounds']['2']['B']
    if case == 'teacher':
        stage['teacher_version'] = dict(stage['teacher_version'],file='updated_teacher_v1.npz')
        message = 'immutable actual FIRST teacher'
    elif case == 'seed':
        final(rows[0],'B')['game_summaries'][0]['seed'] = 317900100000
        message = 'paired new seeds and immutable bank belief'
    elif case == 'belief':
        final(rows[0],'B')['estimated_p_four'] = .5
        message = 'paired new seeds and immutable bank belief'
    elif case == 'base':
        stage['arms']['QUERY_LOCAL']['head_version']['base_file'] = rows[0]['rounds']['1']['B']['arms']['FACTUAL_LOCAL']['head_version']['file']
        message = 'private learner advances its own actual version'
    else:
        stage['arms']['QUERY_LOCAL']['fit']['learning_counts']['rootgroup_updates'] = 2
        message = 'root-group count'
    with pytest.raises(ValueError,match=message):
        summarize(rows,draws=2)


def test_bootstrap_conditions_on_each_fixed_parent_instead_of_resampling_source_population():
    rows = cohort()
    for row in rows:
        for task in ('A','B'):
            shift(final(row,task),row['parent'])
    result = summarize(list(reversed(rows)),draws=40)
    primary = result['final_ab_contrasts']['QUERY_LOCAL_minus_FIRST_LOCAL']
    assert primary['mean'] == 3.5 and primary['ci95'] == [3.5,3.5]
    assert primary['parent_mean_deltas'] == {str(parent):2.+parent for parent in range(4)}
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REUSED_FIRST_COHORT'


def test_missing_lifecycle_cannot_be_replaced_by_an_outcome_selected_subcohort():
    with pytest.raises(ValueError,match='all sixteen FIRST lifecycles'):
        summarize(cohort()[:-1],draws=2)
