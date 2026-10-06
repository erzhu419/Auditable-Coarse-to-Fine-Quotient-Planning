"""Frozen WIN learning separates new-history gain, both-bank retention and root distribution."""
import copy

import pytest

import acfqp.science.win_learning_analysis_v324 as analysis
from acfqp.science.win_learning_analysis_v324 import GROUPS, summarize


def cohort():
    rows = []
    for life in range(16):
        initial, rounds = {}, {'1': {}, '2': {}}
        for task_index, task in enumerate(('A', 'B')):
            belief = .21 if task == 'A' else .51
            teacher = dict(schema='acfqp.head_version.v313', head_kind='LOCAL_RISK', lifecycle=life,
                parent=life % 4, context_id=task_index, arm='FIRST_LOCAL', version=0,
                updates=1000 + life, file=f'v324/life_{life}/{task}/FIRST_LOCAL_v0.npz', base_file=None)

            def evaluation(arm, version, utility):
                return dict(estimated_p_four=belief, head_version=copy.deepcopy(version), planner='H2',
                    static_evaluation_valid=True, game_summaries=[dict(
                        seed=324900000000 + life * 1000000 + task_index * 100000 + episode,
                        utility=life + (50. if task == 'B' else 0.) + utility, status='LOST') for episode in range(64)])

            initial[task] = dict(head_version=teacher, head_versions={'FIRST_LOCAL': copy.deepcopy(teacher)},
                context_id=task_index, planning_belief=dict(estimated_p_four=belief),
                acquisition=dict(warmup=dict(game_summaries=[dict(episode=0, status='LOST')])),
                dataset=dict(games=[dict(episode=1, status='LOST', split='FIT'),
                    dict(episode=2, status='LOST', split='HELDOUT')]),
                evaluations={'SOURCE': evaluation('SOURCE', None, 0.), 'FIRST_LOCAL': evaluation('FIRST_LOCAL', teacher, 1.)})
            previous = {arm: teacher for arm in analysis.UPDATING_ARMS}
            for number in ('1', '2'):
                arms = {}
                for arm in analysis.UPDATING_ARMS:
                    head = dict(teacher, arm=arm, version=int(number),
                        file=f'v324/life_{life}/{task}/{arm}_v{number}.npz', base_file=previous[arm]['file'],
                        updates=previous[arm]['updates'] + GROUPS, reward_indices_count=0)
                    arms[arm] = dict(head_version=head, updates_before=previous[arm]['updates'],
                        updates_after=head['updates'], reward_unchanged=True,
                        fit=dict(alpha=.0025, fitted_rootgroups=GROUPS, replicates=4, reward_frozen=True,
                            learning_counts=dict(rootgroup_updates=GROUPS, current_predictions=GROUPS,
                                win_predictions=GROUPS), normalization_counts=dict(win_parameter_writes=GROUPS)),
                        evaluations=evaluation(arm, head, float(number) + (1. if arm == 'QUERY_WIN' else .5)))
                    previous[arm] = head
                rounds[number][task] = dict(groups=GROUPS, replicas=4, teacher_version=copy.deepcopy(teacher),
                    teacher_unchanged=True, census=dict(selected_groups=GROUPS), arms=arms,
                    collectors={'FIXED_FIRST': dict(dataset=dict(games=[dict(episode=0, status='LOST')]))})
        rows.append(dict(lifecycle=life, parent=life % 4, initial_context_precondition_met=True,
            initial=initial, rounds=rounds))
    return rows


def shift(rows, arm, amount, task=None, number='2'):
    for row in rows:
        for name in ('A', 'B') if task is None else (task,):
            evaluation = (row['initial'][name]['evaluations'][arm] if arm in analysis.INITIAL_ARMS else
                row['rounds'][number][name]['arms'][arm]['evaluations'])
            for game in evaluation['game_summaries']:
                game['utility'] += amount


def test_new_learning_primary_own_first_and_matched_distribution_are_separate():
    result = summarize(cohort(), draws=30)
    assert result['primary_contrast'] == 'QUERY_WIN_minus_FIRST_LOCAL_FINAL_AB'
    assert result['primary']['mean'] == 2. and result['primary']['ci95'] == [2., 2.]
    assert result['primary_self_improvement_supported'] and result['retained_improvement_supported']
    assert result['query_distribution_contribution_status'] == 'SUPPORTED_GAIN'
    assert result['retained_query_mechanism_supported']
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['round_ab_contrasts']['1']['QUERY_WIN_minus_FIRST_LOCAL']['mean'] == 1.
    assert result['final_ab_contrasts']['QUERY_WIN_minus_FACTUAL_WIN']['mean'] == .5
    assert result['physical_evaluation_games'] == 12288 and result['complete_target_learning_cohort']
    assert result['new_target_learning_histories'] and not result['source_histories_repeated']
    assert not result['independent_SOURCE'] and result['bootstrap_executed']
    assert result['bootstrap_seed'] == 32400001 and result['bootstrap_draws'] == 30
    assert result['primary']['positive_equal_negative'] == [16, 0, 0]
    assert result['primary']['interval_scope'] == analysis.INTERVAL_SCOPE
    assert 'not independent SOURCE replication' in result['evidence_scope']


@pytest.mark.parametrize('case', ['source_only', 'b_loss', 'zero_b', 'zero_primary', 'query_no_contribution',
    'factual_gain_query_loss', 'no_source_gain'])
def test_gain_retention_distribution_and_source_do_not_replace_each_other(case):
    rows = cohort()
    if case == 'source_only':
        shift(rows, 'QUERY_WIN', -2.)
    elif case == 'b_loss':
        shift(rows, 'QUERY_WIN', 2., task='A')
        shift(rows, 'QUERY_WIN', -3., task='B')
    elif case == 'zero_b':
        shift(rows, 'QUERY_WIN', -2., task='B')
    elif case == 'zero_primary':
        shift(rows, 'QUERY_WIN', -2.)
        shift(rows, 'SOURCE', -3.)
    elif case == 'query_no_contribution':
        shift(rows, 'FACTUAL_WIN', .5)
    elif case == 'factual_gain_query_loss':
        shift(rows, 'QUERY_WIN', -3.)
    else:
        shift(rows, 'SOURCE', 4.)
    result = summarize(rows, draws=20)
    if case in ('source_only', 'zero_primary'):
        assert result['primary_status'] == 'UNRESOLVED'
        assert result['final_net_gain_status'] == 'SUPPORTED_GAIN'
        assert not result['retained_improvement_supported']
    elif case == 'b_loss':
        assert result['primary_self_improvement_supported']
        assert result['task_retention_status']['B'] == 'SUPPORTED_LOSS'
        assert not result['retained_improvement_supported']
    elif case == 'zero_b':
        assert result['task_retention_status']['B'] == 'SUPPORTED_NONDECREASE'
        assert result['retained_improvement_supported']
    elif case == 'query_no_contribution':
        assert result['retained_improvement_supported']
        assert result['query_distribution_contribution_status'] == 'UNRESOLVED'
        assert not result['retained_query_mechanism_supported']
    elif case == 'factual_gain_query_loss':
        assert result['primary_status'] == 'SUPPORTED_LOSS'
        assert result['factual_self_improvement_status'] == 'SUPPORTED_GAIN'
    else:
        assert result['retained_improvement_supported']
        assert result['final_net_gain_status'] == 'SUPPORTED_LOSS'


@pytest.mark.parametrize('location', ['source', 'first', 'query_round1', 'factual_round2',
    'warmup', 'first_fit', 'collector', 'recorded_training_failure'])
def test_any_observed_acquisition_or_evaluation_cutoff_holds_all_inference(location, monkeypatch):
    rows = cohort()
    row = rows[5]
    if location in ('source', 'first'):
        row['initial']['B']['evaluations']['SOURCE' if location == 'source' else 'FIRST_LOCAL']['game_summaries'][2]['status'] = 'CUTOFF'
    elif location in ('query_round1', 'factual_round2'):
        number, arm = ('1', 'QUERY_WIN') if location == 'query_round1' else ('2', 'FACTUAL_WIN')
        row['rounds'][number]['A']['arms'][arm]['evaluations']['game_summaries'][2]['status'] = 'CUTOFF'
    elif location == 'warmup':
        row['initial']['A']['acquisition']['warmup']['game_summaries'][0]['status'] = 'CUTOFF'
    elif location == 'first_fit':
        row['initial']['A']['dataset']['games'][0]['status'] = 'CUTOFF'
    elif location == 'collector':
        row['rounds']['1']['A']['collectors']['FIXED_FIRST']['dataset']['games'][0]['status'] = 'CUTOFF'
    else:
        row['failure'] = dict(kind='HOLD_TRAINING_CUTOFF', task='A', round=1, reason='Actual retained native cutoff')
        row['rounds'] = {}

    def no_bootstrap(*_args):
        raise AssertionError('No terminal inference may run after a retained cutoff')

    monkeypatch.setattr(analysis, '_samples', no_bootstrap)
    result = summarize(rows, draws=20)
    assert not result['bootstrap_executed'] and not result['complete_game_endpoints']
    assert not result['complete_target_learning_cohort'] and len(result['by_lifecycle']) == 16
    assert result['primary'] is None
    assert all(value is None for values in result['round_ab_contrasts'].values() for value in values.values())
    assert all(value is None for values in result['task_contrasts'].values() for value in values.values())
    assert result['physical_evaluation_games'] == (11776 if location == 'recorded_training_failure' else 12288)
    assert result['primary_status'] == ('HOLD_CUTOFF' if location in
        ('source', 'first', 'query_round1', 'factual_round2') else 'HOLD_TRAINING_CUTOFF')
    assert not result['retained_improvement_supported'] and not result['query_distribution_contribution_supported']
    assert bool(result['cutoffs']) == (location in ('source', 'first', 'query_round1', 'factual_round2'))


@pytest.mark.parametrize('case', ['missing_bank', 'unconfirmed_bank', 'same_bank', 'missing_census',
    'short_census', 'missing_round', 'missing_evaluation', 'partial_cohort'])
def test_unavailable_banks_or_census_retain_observed_rows_and_stop_bootstrap(case, monkeypatch):
    rows = cohort()
    if case == 'missing_bank':
        del rows[2]['initial']['B']
        rows[2]['rounds'] = {}
    elif case == 'unconfirmed_bank':
        rows[2]['initial_context_precondition_met'] = False
    elif case == 'same_bank':
        row = rows[2]
        row['initial']['B']['context_id'] = 0
        row['initial']['B']['head_version']['context_id'] = 0
        row['initial']['B']['head_versions']['FIRST_LOCAL']['context_id'] = 0
        row['initial']['B']['evaluations']['FIRST_LOCAL']['head_version']['context_id'] = 0
        for number in ('1', '2'):
            stage = row['rounds'][number]['B']
            stage['teacher_version']['context_id'] = 0
            for item in stage['arms'].values():
                item['head_version']['context_id'] = 0
                item['evaluations']['head_version']['context_id'] = 0
    elif case == 'missing_census':
        del rows[2]['rounds']['1']['A']['census']
    elif case == 'short_census':
        rows[2]['rounds']['1']['A']['census']['selected_groups'] -= 1
    elif case == 'missing_round':
        del rows[2]['rounds']['2']
    elif case == 'missing_evaluation':
        del rows[2]['rounds']['2']['B']['arms']['QUERY_WIN']['evaluations']
    else:
        rows.pop()
    monkeypatch.setattr(analysis, '_samples', lambda *_args: pytest.fail('Incomplete evidence must not be resampled'))
    result = summarize(rows, draws=20)
    assert not result['bootstrap_executed'] and not result['complete_target_learning_cohort']
    assert len(result['by_lifecycle']) == len(rows)
    assert result['primary'] is None and result['hold_reasons']
    assert result['primary_status'] == ('HOLD_INITIAL_BANK' if case in
        ('missing_bank', 'unconfirmed_bank', 'same_bank') else 'HOLD_COHORT' if case == 'partial_cohort' else 'HOLD_CENSUS')
    assert result['physical_evaluation_games'] > 0


@pytest.mark.parametrize('case', ['old_seed', 'belief', 'different_first', 'teacher', 'quota', 'replicas',
    'alpha', 'reward_write', 'reward_prediction', 'reward_changed', 'head_reward_delta', 'wrong_base',
    'updates', 'wrong_arm', 'evaluated_head', 'planner', 'evaluation_update', 'unknown_endpoint',
    'duplicate_life', 'reparented'])
def test_changed_completed_frozen_contract_cannot_enter_inference(case):
    rows = cohort()
    initial = rows[0]['initial']['B']
    stage = rows[0]['rounds']['1']['B']
    item = stage['arms']['QUERY_WIN']
    if case == 'old_seed':
        item['evaluations']['game_summaries'][0]['seed'] = 323900100000
    elif case == 'belief':
        item['evaluations']['estimated_p_four'] = .1
    elif case == 'different_first':
        initial['head_versions']['FIRST_LOCAL']['file'] = 'old/FIRST_LOCAL_v0.npz'
    elif case == 'teacher':
        stage['teacher_unchanged'] = False
    elif case == 'quota':
        stage['groups'] -= 1
    elif case == 'replicas':
        stage['replicas'] = 8
    elif case == 'alpha':
        item['fit']['alpha'] = .003
    elif case == 'reward_write':
        item['fit']['normalization_counts']['reward_parameter_writes'] = 1
    elif case == 'reward_prediction':
        item['fit']['learning_counts']['reward_predictions'] = 1
    elif case == 'reward_changed':
        item['reward_unchanged'] = False
    elif case == 'head_reward_delta':
        item['head_version']['reward_indices_count'] = 1
    elif case == 'wrong_base':
        item['head_version']['base_file'] = 'another/FIRST_LOCAL.npz'
    elif case == 'updates':
        item['updates_after'] += 1
    elif case == 'wrong_arm':
        item['head_version']['arm'] = 'NSTEP_QUERY'
    elif case == 'evaluated_head':
        item['evaluations']['head_version']['file'] = 'another/QUERY_WIN.npz'
    elif case == 'planner':
        item['evaluations']['planner'] = 'DIRECT'
    elif case == 'evaluation_update':
        item['evaluations']['static_evaluation_valid'] = False
    elif case == 'unknown_endpoint':
        item['evaluations']['game_summaries'][0]['status'] = 'TRUNCATED'
    elif case == 'duplicate_life':
        rows[-1]['lifecycle'] = 0
    else:
        rows[0]['parent'] = 1
    with pytest.raises(ValueError, match='V324'):
        summarize(rows, draws=2)


def test_common_parent_draws_preserve_task_covariance_and_are_generated_once(monkeypatch):
    rows = cohort()
    for row in rows:
        bump = (row['lifecycle'] // 4 - 1.5) * 2.
        for task, sign in (('A', 1), ('B', -1)):
            for arm in ('QUERY_WIN', 'FACTUAL_WIN'):
                for game in row['rounds']['2'][task]['arms'][arm]['evaluations']['game_summaries']:
                    game['utility'] += sign * bump
    samples, calls = analysis._samples, []

    def once(actual_rows, draws):
        calls.append(draws)
        return samples(actual_rows, draws)

    monkeypatch.setattr(analysis, '_samples', once)
    result = summarize(list(reversed(rows)), draws=50)
    assert calls == [50]
    assert result['primary']['ci95'] == [2., 2.]
    assert result['final_ab_contrasts']['QUERY_WIN_minus_FACTUAL_WIN']['ci95'] == [.5, .5]
    assert result['task_contrasts']['ROUND2_A']['QUERY_WIN_minus_FIRST_LOCAL']['ci95'][0] != (
        result['task_contrasts']['ROUND2_A']['QUERY_WIN_minus_FIRST_LOCAL']['ci95'][1])
    assert list(result['primary']['lifecycle_values']) == [str(life) for life in range(16)]

