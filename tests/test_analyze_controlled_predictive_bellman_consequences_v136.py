"""Independent target, calibration and fixed-teacher comparison fixtures."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_bellman_consequences_v136 as analysis

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_bellman_consequences_v136.analysis_checks.json'
    record = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    record['attempts'].append(dict(failures=request.session.testsfailed-before, tests_run=len(request.session.items),
        environment_samples=0, model_samples=0, model_updates=0,
        scope='synthetic joint Bellman identities, paired teacher/query cells and calibration targets'))
    path.write_text(json.dumps(record, indent=2)+'\n')


def rows():
    result = {}
    for life in analysis.LIVES:
        for representation in analysis.REPRESENTATIONS:
            for teacher in analysis.TEACHERS:
                for query in analysis.evaluation_queries(teacher):
                    for method in analysis.METHODS:
                        for replica in range(analysis.REPLICAS):
                            delta = (life+1)*(1 if teacher == 'risk1' else -1)
                            value = replica+life+int(method == 'LEARNED_H2')*delta
                            key = (life, representation, teacher, query, method, replica)
                            result[key] = dict(result=dict(status='LOST', utility=value, score=4, steps=1))
    return result


def test_old_and_new_queries_remain_separate_for_each_fixed_teacher():
    indexed = rows(); result = analysis.full_game_comparison(indexed, {key: True for key in indexed})
    assert result['complete'] and len(result['cells']) == 12
    for cell in result['cells']:
        expected = 2.5 if cell['teacher_query'] == 'risk1' else -2.5
        assert cell['comparisons']['LEARNED_minus_TEACHER']['mean'] == expected
        assert cell['comparisons']['LEARNED_minus_INITIAL_H2']['mean'] == expected
        assert cell['query_role'] == ('old' if cell['query'] == cell['teacher_query'] else 'new')


def test_cutoff_return_is_censored_without_reweighting_or_selecting_another_teacher():
    indexed = rows(); valid = {key: True for key in indexed}
    indexed[(0, 'SINGLE', 'risk1', 'risk2', 'LEARNED_H2', 0)]['result']['status'] = 'CUTOFF'
    result = analysis.full_game_comparison(indexed, valid)
    affected = next(cell for cell in result['cells'] if (cell['representation'],cell['teacher_query'],cell['query']) == ('SINGLE','risk1','risk2'))
    unaffected = next(cell for cell in result['cells'] if (cell['representation'],cell['teacher_query'],cell['query']) == ('SINGLE','risk8','risk2'))
    assert affected['comparisons']['LEARNED_minus_TEACHER']['mean'] is None
    assert unaffected['comparisons']['LEARNED_minus_TEACHER']['mean'] == -2.5
    assert not result['complete']


def test_terminal_suffix_targets_exclude_own_reward_and_analytic_goal():
    assert analysis.diagnostic_targets([1024,512,2048], 'WON') == [
        dict(reward=1.25, success=1.),dict(reward=1.,success=1.)]
    assert analysis.diagnostic_targets([1024,512,2048], 'LOST') == [
        dict(reward=1.25,success=0.),dict(reward=1.,success=0.),dict(reward=0.,success=0.)]
    assert analysis.diagnostic_targets([1024,512,2048], 'CUTOFF') is None


def test_probability_error_and_reward_error_are_both_visible_in_recomposition():
    targets = [dict(reward=2.,success=1.), dict(reward=0.,success=1.)]
    predictions = [dict(reward=1.,success=.75), dict(reward=1.,success=.25)]
    result = analysis.component_errors(predictions, targets, 'risk2')
    assert result['complete'] and result['reward_mse'] == 1.
    assert result['success_brier'] == .3125
    assert result['source_query_mse'] == 4.
    assert result['reward_bias'] == 0. and result['success_bias'] == -.5
    broken = deepcopy(predictions); broken[0]['success'] = 1.1
    assert not analysis.component_errors(broken, targets, 'risk2')['complete']


def test_calibration_weights_games_equally_instead_of_pooling_long_games():
    games = []
    metrics = ('reward_mse','success_brier','source_query_mse','reward_bias','success_bias','source_query_bias')
    for rep in analysis.REPRESENTATIONS:
        for teacher in analysis.TEACHERS:
            for life in analysis.LIVES:
                for replica in range(analysis.REPLICAS):
                    error = 100. if replica == 0 else 0.
                    initial = dict(complete=True,eligible_afterstates=1000 if replica == 0 else 1,
                        **{metric:error for metric in metrics})
                    learned = dict(initial, **{metric:error/2 for metric in metrics})
                    games.append(dict(life=life,representation=rep,teacher_query=teacher,replica=replica,
                        initial=initial,learned=learned))
    result = analysis.calibration_summary(games)
    assert result['complete']
    assert all(cell['means']['initial']['reward_mse'] == 6.25 for cell in result['cells'])
    assert all(cell['changes']['reward_mse'] == -3.125 for cell in result['cells'])


def joint_work(predictions, updates, representation='SINGLE'):
    result = dict(joint_predictions=predictions,reward_predictions=predictions,success_predictions=predictions,
        sigmoid_evaluations=predictions,table_lookups=64*predictions,feature_address_occurrences=32*predictions,
        bank_0_prediction_occurrences=32*(predictions-updates),bank_0_update_occurrences=32*updates,
        td_updates=updates,reward_td_updates=updates,success_td_updates=updates,
        reward_table_update_occurrences=32*updates,success_table_update_occurrences=32*updates,
        reward_table_updates=8*updates,success_table_updates=8*updates,update_feature_squared_norm=128*updates)
    if representation == 'CAPACITY':
        result.update(context_cell_reads=32*predictions,context_bank_selections=32*predictions,
            context_bank_offset_additions=32*predictions)
    return result


def update(reward, success):
    return dict(pre_raw_reward=2.,pre_reward=1.5,pre_logit=0.,pre_success=.5,
        target_reward=reward,target_success=success,raw_reward_target=reward+.5,
        reward_error=reward+.5-2.,success_error=success-.5,work=joint_work(1,1))


@pytest.mark.parametrize('representation', ['SINGLE','CAPACITY'])
def test_both_heads_read_before_one_joint_update_and_address_work_is_shared(representation):
    counts = joint_work(3,1,representation)
    assert analysis.component_counts_valid(counts,representation,1)
    broken = dict(counts); broken['table_lookups'] = 32*3
    assert not analysis.component_counts_valid(broken,representation,1)
    broken = dict(counts); broken['success_td_updates'] = 2
    assert not analysis.component_counts_valid(broken,representation,1)
    assert analysis.update_valid(update(3.,.75),3.,.75,-.5)
    broken = update(3.,.75); broken['raw_reward_target'] = 3.
    assert not analysis.update_valid(broken,3.,.75,-.5)


def teacher_work(root_goals=0):
    outcomes = 4-2*root_goals; leaf_legals = 3*outcomes
    return dict(choose_calls=1,root_swipe_calls=4,root_legal_actions=2,root_goal_actions=root_goals,
        generated_spawn_outcomes=outcomes,expanded_postspawn_states=outcomes,leaf_choose_calls=outcomes,
        spawn_rank1_outcomes=outcomes//2,spawn_rank2_outcomes=outcomes//2,
        expectimax_probability_products=outcomes,expectimax_probability_sums=outcomes,
        second_ply_swipe_calls=4*outcomes,learned_swipe_calls=4+4*outcomes,
        line_table_lookups=16+16*outcomes,legal_swipes=2+leaf_legals,
        learned_terminal_checks=1+outcomes+2+leaf_legals,
        terminal_goal_bypasses=root_goals,value_predictions=leaf_legals,table_lookups=32*leaf_legals)


def segment_fixture(previous=None):
    first = previous is None; n_updates = int(not first)
    source = dict(counts=dict(reward=dict(constant=.25)))
    end = [2,1]+[0]*14 if first else [1]+[0]*11+[2,1,0,0]
    cell = 1 if first else 0; after = list(end); after[cell] = 0
    row = dict(episode=0,seed=13600000001,start_step=0 if first else 1,end_step=1 if first else 2,
        start_board=[1,1]+[0]*14 if first else previous['end_board'],end_board=end,
        actions=['LEFT' if first else 'DOWN'],scores=[4 if first else 0],spawned_cells=[cell],spawned_ranks=[1],
        chosen_values=[1.1],next_components=[dict(raw_reward=2.,reward=1.5,logit=-1.,success=.25,failure=.75)],
        joint_updates=[None if first else update(1.5,.25)],terminal_update=None,
        pending_before=None if first else previous['pending_after'],pending_after=after,
        updates_before=0,updates_after=n_updates,cumulative_updates=n_updates,
        cumulative_transitions=1 if first else 2,status='ACTIVE',budget_status='BUDGET_END',
        censored_last_update=False,return_score=4,seconds=.01,
        environment_counts=dict(sampled_transitions=1,initial_spawns=2*first,environment_random_draws=2+4*first,
            ground_explicit_swipe_calls=1,ground_state_status_calls=1+first,ground_status_internal_swipe_calls=4*(1+first)),
        model_counts=dict(joint_work(1+n_updates,n_updates),value_calls=1),teacher_counts=teacher_work())
    if first: row['initial_spawns'] = [dict(cell=0,rank=1),dict(cell=1,rank=1)]
    return row, source


def test_budget_resume_carries_pending_and_uses_component_targets_not_teacher_scalar():
    first, source = segment_fixture(); second, _ = segment_fixture(first)
    assert all(analysis.segment_checks(first,None,source,'SINGLE','risk1').values())
    assert all(analysis.segment_checks(second,first,source,'SINGLE','risk1').values())
    broken = deepcopy(second); broken['joint_updates'][0] = update(1.1,.25)
    assert not analysis.segment_checks(broken,first,source,'SINGLE','risk1')['joint_targets']
    broken = deepcopy(second); broken['pending_before'] = None
    assert not analysis.segment_checks(broken,first,source,'SINGLE','risk1')['stream_continuity']


def test_loss_flushes_zero_future_reward_and_success():
    first, source = segment_fixture(); row, _ = segment_fixture(first)
    end = [1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1]; after = list(end); after[0] = 0
    row.update(status='LOST',budget_status='EPISODE_END',end_board=end,pending_after=None,
        terminal_update=dict(update(0.,0.),afterstate=after),updates_after=2,cumulative_updates=2,
        model_counts=dict(joint_work(3,2),value_calls=1))
    assert all(analysis.segment_checks(row,first,source,'SINGLE','risk1').values())
    broken = deepcopy(row); broken['terminal_update'] = dict(update(-1.,0.),afterstate=after)
    assert not analysis.segment_checks(broken,first,source,'SINGLE','risk1')['joint_targets']


def test_goal_is_analytic_and_its_reward_updates_only_preceding_afterstate():
    first, source = segment_fixture(); row, _ = segment_fixture(first)
    row.update(status='WON',budget_status='EPISODE_END',end_board=[11,1]+[0]*14,pending_after=None,
        scores=[2048],return_score=2052,spawned_cells=[1],chosen_values=[2.],
        next_components=[dict(raw_reward=0.,reward=0.,logit=None,success=1.,failure=0.)],
        joint_updates=[update(1.,1.)],model_counts=dict(joint_work(1,1),value_calls=1),teacher_counts=teacher_work(1))
    row['environment_counts']['ground_status_internal_swipe_calls'] = 0
    assert all(analysis.segment_checks(row,first,source,'SINGLE','risk1').values())
    broken = deepcopy(row); broken['joint_updates'][0] = update(0.,1.)
    assert not analysis.segment_checks(broken,first,source,'SINGLE','risk1')['joint_targets']
