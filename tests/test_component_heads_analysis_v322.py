"""Head-component restoration stays separate from growth and task retention."""
import copy

import pytest

import acfqp.science.component_heads_analysis_v322 as analysis
from acfqp.science.component_heads_analysis_v322 import ARMS, INTERACTION, NEW_ARMS, summarize


def cohort():
    values = dict(FIRST_LOCAL=2., NSTEP_QUERY=3., REWARD_ONLY=4., WIN_ONLY=2.5)
    rows = []
    for life in range(16):
        initial, cells = {}, {}
        for task_index, task in enumerate(('A', 'B')):
            belief = .23 if task == 'A' else .73
            first = dict(schema='acfqp.head_version.v313', head_kind='LOCAL_RISK', lifecycle=life,
                parent=life % 4, context_id=task_index, arm='FIRST_LOCAL', version=0,
                updates=1000 + life, file=f'v317/life_{life}/{task}/FIRST_LOCAL_v0.npz', base_file=None)
            initial[task] = dict(head_version=first, planning_belief=dict(estimated_p_four=belief),
                context_id=task_index)
            cells[task] = {}
            for arm in ARMS:
                if arm == 'FIRST_LOCAL':
                    head = copy.deepcopy(first)
                else:
                    head = dict(first, arm=arm, version=2 if arm == 'NSTEP_QUERY' else 1,
                        updates=first['updates'] + (32768 if arm == 'NSTEP_QUERY' else 0),
                        file=f'v32{1 if arm == "NSTEP_QUERY" else 2}/life_{life}/{task}/{arm}.npz',
                        base_file=f'v321/life_{life}/{task}/NSTEP_QUERY_v1.npz'
                            if arm == 'NSTEP_QUERY' else first['file'])
                evaluation = dict(estimated_p_four=belief, head_version=copy.deepcopy(head),
                    game_summaries=[dict(seed=321900000000 + life * 1000000 + task_index * 100000 + episode,
                        utility=life + (100. if task == 'B' else 0.) + values[arm], status='LOST')
                        for episode in range(32)])
                item = dict(evaluation=evaluation, reused=arm not in NEW_ARMS)
                if arm in NEW_ARMS:
                    item.update(head_version=head, assembly=dict(new_fit_updates=0, weights_frozen=True))
                cells[task][arm] = item
        rows.append(dict(lifecycle=life, parent=life % 4, initial=initial, cells=cells))
    return rows


def shift(rows, arm, amount, task=None):
    for row in rows:
        for name in ('A', 'B') if task is None else (task,):
            for game in row['cells'][name][arm]['evaluation']['game_summaries']:
                game['utility'] += amount


def test_two_by_two_component_contrasts_reuse_exactly_two_game_cells():
    result = summarize(cohort(), draws=40)
    expected = dict(REWARD_ONLY_minus_NSTEP_QUERY=1., REWARD_ONLY_minus_FIRST_LOCAL=2.,
        WIN_ONLY_minus_FIRST_LOCAL=.5, NSTEP_QUERY_minus_WIN_ONLY=.5, NSTEP_QUERY_minus_FIRST_LOCAL=1.)
    expected[INTERACTION] = -1.5
    assert result['primary_contrast'] == 'REWARD_ONLY_minus_NSTEP_QUERY_FINAL_AB'
    assert {key: value['mean'] for key, value in result['final_ab_contrasts'].items()} == expected
    assert result['primary']['ci95'] == [1., 1.]
    assert result['primary_status'] == 'SUPPORTED_GAIN' and result['primary_restoration_supported']
    assert result['pure_component_status'] == dict(REWARD_ONLY='SUPPORTED_GAIN', WIN_ONLY='SUPPORTED_GAIN')
    assert result['reward_only_self_improvement_status'] == 'SUPPORTED_GAIN'
    assert result['interaction_status'] == 'SUPPORTED_LOSS' and result['restored_growth_supported']
    assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_NONDECREASE')
    assert result['physical_new_evaluation_games'] == 2048 and result['reused_evaluation_games'] == 2048
    assert result['total_evaluation_games'] == 4096 and result['complete_game_endpoints']
    assert result['bootstrap_seed'] == 32200001 and result['bootstrap_draws'] == 40
    assert result['bootstrap_executed'] and result['paired_stream_reuse']
    assert result['primary']['positive_equal_negative'] == [16, 0, 0]
    assert result['primary']['parent_mean_values'] == {str(parent): 1. for parent in range(4)}
    assert 'not independent confirmation' in result['evidence_scope']
    assert 'without parameter fitting or new labels' in result['evidence_scope']


@pytest.mark.parametrize('case', ['restoration_without_growth', 'growth_without_restoration',
    'b_loss', 'zero_retention', 'negative_primary', 'win_only_loss'])
def test_risk_restoration_growth_and_task_retention_have_separate_requirements(case):
    rows = cohort()
    if case == 'restoration_without_growth':
        shift(rows, 'REWARD_ONLY', -2.)
        shift(rows, 'NSTEP_QUERY', -3.)
    elif case == 'growth_without_restoration':
        shift(rows, 'NSTEP_QUERY', 1.)
    elif case == 'b_loss':
        shift(rows, 'REWARD_ONLY', 3., task='A')
        shift(rows, 'REWARD_ONLY', -3., task='B')
    elif case == 'zero_retention':
        shift(rows, 'REWARD_ONLY', -2., task='B')
        shift(rows, 'NSTEP_QUERY', -1.)
    elif case == 'negative_primary':
        shift(rows, 'NSTEP_QUERY', 2.)
    else:
        shift(rows, 'WIN_ONLY', -1.)
    result = summarize(rows, draws=20)
    if case == 'restoration_without_growth':
        assert result['primary_restoration_supported']
        assert result['reward_only_self_improvement_status'] == 'UNRESOLVED'
        assert not result['restored_growth_supported']
    elif case == 'growth_without_restoration':
        assert result['primary_status'] == 'UNRESOLVED'
        assert result['reward_only_self_improvement_status'] == 'SUPPORTED_GAIN'
        assert not result['restored_growth_supported']
    elif case == 'b_loss':
        assert result['primary_restoration_supported']
        assert result['reward_only_self_improvement_status'] == 'SUPPORTED_GAIN'
        assert result['task_retention_status'] == dict(A='SUPPORTED_NONDECREASE', B='SUPPORTED_LOSS')
        assert not result['restored_growth_supported']
    elif case == 'zero_retention':
        assert result['task_contrasts']['B']['REWARD_ONLY_minus_FIRST_LOCAL']['ci95'] == [0., 0.]
        assert result['task_retention_status']['B'] == 'SUPPORTED_NONDECREASE'
        assert result['restored_growth_supported']
    elif case == 'negative_primary':
        assert result['primary_status'] == 'SUPPORTED_LOSS'
        assert result['reward_only_self_improvement_status'] == 'SUPPORTED_GAIN'
        assert not result['restored_growth_supported']
    else:
        assert result['pure_component_status']['WIN_ONLY'] == 'SUPPORTED_LOSS'
        assert result['restored_growth_supported']


@pytest.mark.parametrize('arm', ARMS)
def test_any_new_or_reused_cutoff_holds_every_terminal_interval_without_bootstrap(arm, monkeypatch):
    rows = cohort()
    game = rows[6]['cells']['A'][arm]['evaluation']['game_summaries'][3]
    game.update(status='CUTOFF', utility=-100.)

    def no_bootstrap(*_args):
        raise AssertionError('A retained cutoff must stop all terminal resampling')

    monkeypatch.setattr(analysis, '_samples', no_bootstrap)
    result = summarize(rows, draws=20)
    assert not result['complete_game_endpoints'] and not result['bootstrap_executed']
    assert result['physical_new_evaluation_games'] == 2048 and result['reused_evaluation_games'] == 2048
    assert result['total_evaluation_games'] == 4096 and len(result['by_lifecycle']) == 16
    assert result['cutoffs'] == [dict(lifecycle=6, task='A', arm=arm, seed=321906000003,
        reused=arm not in NEW_ARMS)]
    assert result['by_lifecycle'][6]['retained_endpoint_counts']['A'][arm]['CUTOFF'] == 1
    assert result['primary'] is None
    assert all(value is None for value in result['final_ab_contrasts'].values())
    assert all(value is None for task in result['task_contrasts'].values() for value in task.values())
    assert result['primary_status'] == result['reward_only_self_improvement_status'] == 'HOLD_CUTOFF'
    assert result['interaction_status'] == 'HOLD_CUTOFF'
    assert result['pure_component_status'] == dict(REWARD_ONLY='HOLD_CUTOFF', WIN_ONLY='HOLD_CUTOFF')
    assert result['task_retention_status'] == dict(A='HOLD_CUTOFF', B='HOLD_CUTOFF')
    assert not result['primary_restoration_supported'] and not result['restored_growth_supported']


@pytest.mark.parametrize('case', ['seed', 'belief', 'missing_game', 'missing_arm', 'extra_arm',
    'missing_task', 'new_reused', 'old_not_reused', 'first_head', 'both_version', 'both_updates',
    'hybrid_head', 'hybrid_base', 'hybrid_updates', 'task_bank', 'life_head', 'status'])
def test_changed_stream_or_component_contract_cannot_be_analyzed(case):
    rows = cohort()
    item = rows[0]['cells']['B']['REWARD_ONLY']
    evaluation = item['evaluation']
    both = rows[0]['cells']['B']['NSTEP_QUERY']['evaluation']['head_version']
    if case == 'seed':
        evaluation['game_summaries'][0]['seed'] = 322900100000
    elif case == 'belief':
        evaluation['estimated_p_four'] = .5
    elif case == 'missing_game':
        evaluation['game_summaries'].pop()
    elif case == 'missing_arm':
        del rows[0]['cells']['B']['WIN_ONLY']
    elif case == 'extra_arm':
        rows[0]['cells']['B']['EXTRA'] = copy.deepcopy(item)
    elif case == 'missing_task':
        del rows[0]['cells']['B']
    elif case == 'new_reused':
        item['reused'] = True
    elif case == 'old_not_reused':
        rows[0]['cells']['B']['FIRST_LOCAL']['reused'] = False
    elif case == 'first_head':
        rows[0]['cells']['B']['FIRST_LOCAL']['evaluation']['head_version']['file'] = 'another_first.npz'
    elif case == 'both_version':
        both['version'] = 1
    elif case == 'both_updates':
        both['updates'] -= 1
    elif case == 'hybrid_head':
        evaluation['head_version'] = copy.deepcopy(both)
    elif case == 'hybrid_base':
        item['head_version']['base_file'] = both['file']
        evaluation['head_version'] = copy.deepcopy(item['head_version'])
    elif case == 'hybrid_updates':
        item['head_version']['updates'] += 1
        evaluation['head_version'] = copy.deepcopy(item['head_version'])
    elif case == 'task_bank':
        evaluation['head_version']['context_id'] = 0
    elif case == 'life_head':
        evaluation['head_version']['lifecycle'] = 1
    else:
        evaluation['game_summaries'][0]['status'] = 'TRUNCATED'
    with pytest.raises(ValueError, match='V322'):
        summarize(rows, draws=2)


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'wrong_parent'])
def test_selected_or_reparented_lifecycles_cannot_replace_the_original_cohort(case):
    rows = cohort()
    if case == 'missing':
        rows.pop()
    elif case == 'duplicate':
        rows[-1]['lifecycle'] = 0
    else:
        rows[0]['parent'] = 1
    with pytest.raises(ValueError, match='all sixteen FIRST lifecycles'):
        summarize(rows, draws=2)


def test_common_parent_conditional_draws_preserve_component_covariance():
    rows = cohort()
    for row in rows:
        for task in ('A', 'B'):
            for game in row['cells'][task]['REWARD_ONLY']['evaluation']['game_summaries']:
                game['utility'] += row['parent']
    result = summarize(list(reversed(rows)), draws=40)
    primary = result['primary']
    assert primary['mean'] == 2.5 and primary['ci95'] == [2.5, 2.5]
    assert primary['parent_mean_values'] == {str(parent): 1. + parent for parent in range(4)}
    assert list(primary['lifecycle_values']) == [str(life) for life in range(16)]
    assert primary['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_REUSED_FIRST_COHORT_AND_V321_STREAMS'

    rows = cohort()
    for row in rows:
        for task in ('A', 'B'):
            bump = (row['lifecycle'] // 4 - 1.5) * 3.
            for arm in ('NSTEP_QUERY', 'REWARD_ONLY'):
                for game in row['cells'][task][arm]['evaluation']['game_summaries']:
                    game['utility'] += bump
    result = summarize(rows, draws=40)
    assert result['final_ab_contrasts']['REWARD_ONLY_minus_FIRST_LOCAL']['ci95'][0] != (
        result['final_ab_contrasts']['REWARD_ONLY_minus_FIRST_LOCAL']['ci95'][1])
    assert result['primary']['ci95'] == [1., 1.]
    assert result['final_ab_contrasts'][INTERACTION]['ci95'] == [-1.5, -1.5]
