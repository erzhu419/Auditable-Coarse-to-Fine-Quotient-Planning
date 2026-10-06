"""Fresh frozen-policy validation separates execution gain from A/B retention."""
import copy

import pytest

import acfqp.science.win_confirmation_analysis_v323 as analysis
from acfqp.science.win_confirmation_analysis_v323 import ARMS, summarize


def cohort():
    values = dict(SOURCE=1., FIRST_LOCAL=2., WIN_ONLY=3.)
    rows = []
    for life in range(16):
        initial, candidates, evaluations = {}, {}, {}
        for task_index, task in enumerate(('A', 'B')):
            belief = .23 if task == 'A' else .73
            first = dict(schema='acfqp.head_version.v313', head_kind='LOCAL_RISK', lifecycle=life,
                parent=life % 4, context_id=task_index, arm='FIRST_LOCAL', version=0,
                updates=1000 + life, file=f'v317/life_{life}/{task}/FIRST_LOCAL_v0.npz', base_file=None)
            head = dict(first, arm='WIN_ONLY', version=1, base_file=first['file'],
                file=f'v322/life_{life}/{task}/WIN_ONLY_v1.npz')
            initial[task] = dict(head_version=first, planning_belief=dict(estimated_p_four=belief),
                context_id=task_index)
            candidates[task] = dict(head_version=head, assembly=dict(new_fit_updates=0, weights_frozen=True,
                complete_component_equality=True, parameter_updates_counter=first['updates'],
                reward_source='FIRST_LOCAL', win_source='NSTEP_QUERY'))
            evaluations[task] = {}
            for arm in ARMS:
                evaluations[task][arm] = dict(estimated_p_four=belief,
                    head_version=copy.deepcopy({'SOURCE': None, 'FIRST_LOCAL': first, 'WIN_ONLY': head}[arm]),
                    planner='H2', static_evaluation_valid=True,
                    game_summaries=[dict(seed=323900000000 + life * 1000000 + task_index * 100000 + episode,
                        utility=life + (100. if task == 'B' else 0.) + values[arm], status='LOST')
                        for episode in range(64)])
        rows.append(dict(lifecycle=life, parent=life % 4, initial=initial,
            frozen_candidate=candidates, evaluations=evaluations))
    return rows


def shift(rows, arm, amount, task=None):
    for row in rows:
        for name in ('A', 'B') if task is None else (task,):
            for game in row['evaluations'][name][arm]['game_summaries']:
                game['utility'] += amount


def test_prospective_primary_is_own_first_gain_on_all_new_physical_streams():
    result = summarize(cohort(), draws=40)
    expected = dict(WIN_ONLY_minus_FIRST_LOCAL=1., WIN_ONLY_minus_SOURCE=2., FIRST_LOCAL_minus_SOURCE=1.)
    assert result['primary_contrast'] == 'WIN_ONLY_minus_FIRST_LOCAL_FINAL_AB'
    assert {key: value['mean'] for key, value in result['final_ab_contrasts'].items()} == expected
    assert result['primary']['ci95'] == [1., 1.] and result['primary_status'] == 'SUPPORTED_GAIN'
    assert result['primary_execution_gain_supported'] and result['retained_execution_gain_supported']
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['final_net_gain_status'] == 'SUPPORTED_GAIN'
    assert result['physical_evaluation_games'] == 6144 and result['complete_game_endpoints']
    assert result['bootstrap_seed'] == 32300001 and result['bootstrap_draws'] == 40
    assert result['bootstrap_executed'] and result['fresh_evaluation_streams']
    assert not result['independent_learning_histories']
    assert result['primary']['positive_equal_negative'] == [16, 0, 0]
    assert result['primary']['parent_mean_values'] == {str(parent): 1. for parent in range(4)}
    assert 'not an independent learning cohort' in result['evidence_scope']
    assert 'without fitting, target acquisition' in result['evidence_scope']


@pytest.mark.parametrize('case', ['source_gain_without_first_gain', 'b_loss', 'zero_b_retention',
    'zero_primary', 'negative_primary', 'retained_gain_without_source_gain'])
def test_source_contrast_execution_gain_and_task_retention_are_separate(case):
    rows = cohort()
    if case == 'source_gain_without_first_gain':
        shift(rows, 'WIN_ONLY', -1.)
    elif case == 'b_loss':
        shift(rows, 'WIN_ONLY', 3., task='A')
        shift(rows, 'WIN_ONLY', -2., task='B')
    elif case == 'zero_b_retention':
        shift(rows, 'WIN_ONLY', -1., task='B')
    elif case == 'zero_primary':
        shift(rows, 'WIN_ONLY', -1.)
        shift(rows, 'SOURCE', -2.)
    elif case == 'negative_primary':
        shift(rows, 'WIN_ONLY', -2.)
    else:
        shift(rows, 'SOURCE', 3.)
    result = summarize(rows, draws=20)
    if case in ('source_gain_without_first_gain', 'zero_primary'):
        assert result['final_net_gain_status'] == 'SUPPORTED_GAIN'
        assert result['primary_status'] == 'UNRESOLVED'
        assert not result['primary_execution_gain_supported'] and not result['retained_execution_gain_supported']
    elif case == 'b_loss':
        assert result['primary_execution_gain_supported']
        assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_LOSS')
        assert not result['retained_execution_gain_supported']
    elif case == 'zero_b_retention':
        assert result['task_contrasts']['B']['WIN_ONLY_minus_FIRST_LOCAL']['ci95'] == [0., 0.]
        assert result['task_retention_status']['B'] == 'SUPPORTED_NONDECREASE'
        assert result['retained_execution_gain_supported']
    elif case == 'negative_primary':
        assert result['primary_status'] == 'SUPPORTED_LOSS'
        assert not result['primary_execution_gain_supported'] and not result['retained_execution_gain_supported']
    else:
        assert result['final_net_gain_status'] == 'SUPPORTED_LOSS'
        assert result['primary_execution_gain_supported'] and result['retained_execution_gain_supported']


@pytest.mark.parametrize('arm', ARMS)
def test_any_cutoff_keeps_every_game_but_holds_every_terminal_interval_without_bootstrap(arm, monkeypatch):
    rows = cohort()
    game = rows[6]['evaluations']['A'][arm]['game_summaries'][3]
    game.update(status='CUTOFF', utility=-100.)

    def no_bootstrap(*_args):
        raise AssertionError('A retained cutoff must stop all terminal resampling')

    monkeypatch.setattr(analysis, '_samples', no_bootstrap)
    result = summarize(rows, draws=20)
    assert not result['complete_game_endpoints'] and not result['bootstrap_executed']
    assert result['physical_evaluation_games'] == 6144 and len(result['by_lifecycle']) == 16
    assert result['cutoffs'] == [dict(lifecycle=6, task='A', arm=arm, seed=323906000003)]
    assert result['by_lifecycle'][6]['retained_endpoint_counts']['A'][arm]['CUTOFF'] == 1
    assert result['primary'] is None
    assert all(value is None for value in result['final_ab_contrasts'].values())
    assert all(value is None for task in result['task_contrasts'].values() for value in task.values())
    assert result['primary_status'] == result['final_net_gain_status'] == 'HOLD_CUTOFF'
    assert result['task_retention_status'] == dict(A='HOLD_CUTOFF', B='HOLD_CUTOFF')
    assert not result['primary_execution_gain_supported'] and not result['retained_execution_gain_supported']


@pytest.mark.parametrize('case', ['old_seed', 'unpaired_seed', 'belief', 'missing_game', 'extra_game',
    'missing_arm', 'extra_arm', 'missing_task', 'first_head', 'first_version', 'source_head',
    'candidate_head', 'candidate_version', 'candidate_base', 'candidate_updates', 'task_bank',
    'life_head', 'fit', 'weights', 'component', 'reward_source', 'win_source', 'assembly_updates',
    'planner', 'changed_evaluation', 'status'])
def test_changed_stream_saved_head_or_policy_contract_cannot_be_analyzed(case):
    rows = cohort()
    evaluation = rows[0]['evaluations']['B']['WIN_ONLY']
    candidate = rows[0]['frozen_candidate']['B']
    head, assembly = candidate['head_version'], candidate['assembly']
    if case == 'old_seed':
        evaluation['game_summaries'][0]['seed'] = 321900100000
    elif case == 'unpaired_seed':
        evaluation['game_summaries'][0]['seed'] += 1
    elif case == 'belief':
        evaluation['estimated_p_four'] = .5
    elif case == 'missing_game':
        evaluation['game_summaries'].pop()
    elif case == 'extra_game':
        evaluation['game_summaries'].append(copy.deepcopy(evaluation['game_summaries'][-1]))
    elif case == 'missing_arm':
        del rows[0]['evaluations']['B']['SOURCE']
    elif case == 'extra_arm':
        rows[0]['evaluations']['B']['EXTRA'] = copy.deepcopy(evaluation)
    elif case == 'missing_task':
        del rows[0]['frozen_candidate']['B']
    elif case == 'first_head':
        rows[0]['evaluations']['B']['FIRST_LOCAL']['head_version']['file'] = 'another_first.npz'
    elif case == 'first_version':
        rows[0]['initial']['B']['head_version']['version'] = 1
    elif case == 'source_head':
        rows[0]['evaluations']['B']['SOURCE']['head_version'] = copy.deepcopy(head)
    elif case == 'candidate_head':
        evaluation['head_version']['file'] = 'another_candidate.npz'
    elif case == 'candidate_version':
        head['version'] = 2
    elif case == 'candidate_base':
        head['base_file'] = 'v321/NSTEP_QUERY_v2.npz'
    elif case == 'candidate_updates':
        head['updates'] += 1
    elif case == 'task_bank':
        head['context_id'] = 0
    elif case == 'life_head':
        head['lifecycle'] = 1
    elif case == 'fit':
        assembly['new_fit_updates'] = 1
    elif case == 'weights':
        assembly['weights_frozen'] = False
    elif case == 'component':
        assembly['complete_component_equality'] = False
    elif case == 'reward_source':
        assembly['reward_source'] = 'NSTEP_QUERY'
    elif case == 'win_source':
        assembly['win_source'] = 'FIRST_LOCAL'
    elif case == 'assembly_updates':
        assembly['parameter_updates_counter'] += 1
    elif case == 'planner':
        evaluation['planner'] = 'DIRECT'
    elif case == 'changed_evaluation':
        evaluation['static_evaluation_valid'] = False
    else:
        evaluation['game_summaries'][0]['status'] = 'TRUNCATED'
    with pytest.raises(ValueError, match='V323'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'wrong_parent'])
def test_selected_or_reparented_lifecycles_cannot_replace_the_existing_cohort(case):
    rows = cohort()
    if case == 'missing':
        rows.pop()
    elif case == 'duplicate':
        rows[-1]['lifecycle'] = 0
    else:
        rows[0]['parent'] = 1
    with pytest.raises(ValueError, match='all sixteen FIRST lifecycles'):
        summarize(rows, draws=2)


def test_common_parent_conditional_draws_preserve_paired_and_task_covariance():
    rows = cohort()
    for row in rows:
        for task in ('A', 'B'):
            for game in row['evaluations'][task]['WIN_ONLY']['game_summaries']:
                game['utility'] += row['parent']
    result = summarize(list(reversed(rows)), draws=40)
    primary = result['primary']
    assert primary['mean'] == 2.5 and primary['ci95'] == [2.5, 2.5]
    assert primary['parent_mean_values'] == {str(parent): 1. + parent for parent in range(4)}
    assert list(primary['lifecycle_values']) == [str(life) for life in range(16)]
    assert primary['interval_scope'] == (
        'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_EXISTING_SIXTEEN_FROZEN_HEADS_NEW_V323_STREAMS')

    rows = cohort()
    for row in rows:
        bump = (row['lifecycle'] // 4 - 1.5) * 3.
        for arm in ('FIRST_LOCAL', 'WIN_ONLY'):
            for task, sign in (('A', 1), ('B', -1)):
                for game in row['evaluations'][task][arm]['game_summaries']:
                    game['utility'] += sign * bump
    result = summarize(rows, draws=40)
    assert result['task_contrasts']['A']['FIRST_LOCAL_minus_SOURCE']['ci95'][0] != (
        result['task_contrasts']['A']['FIRST_LOCAL_minus_SOURCE']['ci95'][1])
    assert result['final_ab_contrasts']['FIRST_LOCAL_minus_SOURCE']['ci95'] == [1., 1.]
    assert result['primary']['ci95'] == [1., 1.]
