"""Finite checks detect attribution, terminal or read-only diagnostic mistakes."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS,NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics,RewriteProgram
from acfqp.science.native_b_mechanism_v299 import predict,features,decompose_h2

BUILD=Path(__file__).resolve().parents[1]/'reports/b_mechanism_v299/runtime/tests'
SOURCE_QUERY=dict(reward_weight=1.,failure_penalty=1.,goal_bonus=2.)
TARGET_QUERY=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.)


def leaf(seed=1,p=.6,same_query=False):
    mass=Fraction(str(p))
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,1-mass),(2,mass)),'uniform',4)
    source=NtupleValue(rule,BUILD)
    source.weights[:]=np.random.default_rng(seed).normal(0.,.25,size=source.weights.shape)
    target=SOURCE_QUERY if same_query else TARGET_QUERY
    result=QueryTD(QueryParent(source,SOURCE_QUERY,target,.4),'PRIOR',BUILD)
    result.freeze()
    return result


def boards():
    rows=np.random.default_rng(29900001).integers(0,4,size=(8,16),dtype=np.int32)
    rows[0]=[1,2,1,2,2,1,2,1,1,2,1,2,2,1,2,1]  # Analytic loss.
    rows[1]=[3,3]+[0]*14  # Immediate goal from either horizontal direction.
    rows[2]=[0]*16  # No legal action, despite free cells.
    rows[3]=[4]+[0]*15  # Existing goal bypasses out-of-table ranks.
    return rows


def test_predict_has_exact_raw_sum_offset_goal_and_never_updates_weights_or_counts():
    model=leaf();rows=boards();before=model.weights.copy()
    old_counts=dict(model.counts),dict(model.model.counts)
    result=predict(model,rows,BUILD)
    expected=[]
    for row in rows:
        if max(row)>=model.radix:expected.append(model.target_query['goal_bonus'])
        else:
            raw=float(model.model.library.ntuple_value_v120(row,model.model.patterns,
                model.radix,model.weights))
            expected.append(raw+model.failure_shift+model.success_shift)
    np.testing.assert_array_equal(result['predictions'],expected)
    np.testing.assert_array_equal(model.weights,before)
    assert (dict(model.counts),dict(model.model.counts))==old_counts
    assert model.updates==0 and not model.weights.flags.writeable
    assert result['counts']['value_predictions']==7
    assert result['counts']['table_lookups']==7*32
    assert result['counts']['terminal_goal_bypasses']==1
    assert result['counts']['prediction_terminal_checks']==8


def test_feature_addresses_keep_all_duplicate_occurrences_and_exact_native_order():
    model=leaf();rows=boards()[[0,1,2,4]]
    result=features(model,rows,BUILD)
    expected=np.asarray([model.model.feature_indices(row) for row in rows])
    np.testing.assert_array_equal(result['features'],expected)
    zero=result['features'][2]
    assert len(np.unique(zero))==4
    np.testing.assert_array_equal(zero,np.repeat(np.arange(4)*model.radix**6,8))
    assert result['counts']['feature_occurrences']==4*32
    assert result['counts']['feature_digit_reads']==4*32*6
    assert result['counts'].get('table_lookups',0)==0
    with pytest.raises(ValueError,match='analytic'):
        features(model,[boards()[3]],BUILD)


@pytest.mark.parametrize('p',[0.,.1057988166,.6,1.])
def test_h2_source_current_are_bit_exact_original_planner_with_learned_spawn_law(p):
    source,current=leaf(1,p),leaf(2,p)
    rows=boards();source_before=source.weights.copy();current_before=current.weights.copy()
    result=decompose_h2(source,current,rows,p,BUILD)
    for name,model in [('source',source),('current',current)]:
        planner=FrozenLeafPlanner(model,2,BUILD)
        for i,row in enumerate(rows):
            expected=planner.choose(row)
            expected_action=-2 if expected['status']=='WON' else -1 if expected['status']=='LOST' else ACTIONS.index(expected['action'])
            assert result[f'{name}_actions'][i]==expected_action
            for a,action in enumerate(ACTIONS):
                assert result['legal'][i,a]==(action in expected['action_values'])
                if action in expected['action_values']:
                    assert result[f'{name}_q'][i,a]==expected['action_values'][action]['value']
    np.testing.assert_array_equal(source.weights,source_before)
    np.testing.assert_array_equal(current.weights,current_before)
    assert source.updates==current.updates==0
    assert result['counts']['root_swipe_calls']==4*7
    assert result['counts']['second_ply_swipe_calls']%8==0
    assert result['counts']['generated_spawn_outcomes']==2*result['counts']['spawn_rank1_outcomes']
    assert result['counts']['generated_spawn_outcomes']==2*result['counts']['spawn_rank2_outcomes']


def test_same_weights_give_identical_values_and_actions_all_three_conditions():
    source=leaf();result=decompose_h2(source,source,boards(),.6,BUILD)
    np.testing.assert_array_equal(result['source_q'],result['current_q'])
    np.testing.assert_array_equal(result['source_q'],result['frozen_second_q'])
    np.testing.assert_array_equal(result['source_actions'],result['current_actions'])
    np.testing.assert_array_equal(result['source_actions'],result['frozen_second_actions'])
    assert result['counts'].get('reselected_second_actions',0)==0
    # Goal action contains its own merge reward once and ignores the learned weights.
    winning_q=result['source_q'][1]
    for action in ('LEFT','RIGHT'):
        assert winning_q[ACTIONS.index(action)]==16/2048.+4.


def fixed_second_reference(source,current,root,p):
    result=np.full(4,-np.inf)
    for a,action in enumerate(ACTIONS):
        after,reward,changed=source.rule.swipe(root,action)
        if not changed:continue
        if max(after)>=source.radix:result[a]=reward/2048.+source.target_query['goal_bonus'];continue
        empty=[cell for cell,rank in enumerate(after) if rank==0]
        expectation=0.
        for cell in empty:
            for rank in (1,2):
                state=list(after);state[cell]=rank
                source_choice=source.choose(state)
                current_choice=current.choose(state)
                value=(source_choice['value'] if source_choice['action'] is None else
                    current_choice['action_values'][source_choice['action']]['value'])
                probability=(1.-p if rank==1 else p)/len(empty)
                expectation+=probability*value
        result[a]=reward/2048.+expectation
    return result


def test_fixed_second_action_uses_source_selection_and_max_reselection_is_nonnegative():
    source,current=leaf(1),leaf(2);rows=boards()[[1,4,5,6,7]]
    result=decompose_h2(source,current,rows,np.full(len(rows),.6),BUILD)
    expected=np.asarray([fixed_second_reference(source,current,row,.6) for row in rows])
    np.testing.assert_array_equal(result['frozen_second_q'],expected)
    legal=result['legal']
    reselection=result['current_q'][legal]-result['frozen_second_q'][legal]
    assert np.all(reselection>=-1e-12)
    assert np.any(reselection>1e-5)
    assert result['counts']['reselected_second_actions']>0
    for q,name in ((result['frozen_second_q'],'frozen_second_actions'),):
        np.testing.assert_array_equal(result[name],np.argmax(q,axis=1))


def test_empty_batches_and_zero_offset_source_query_need_no_predictions():
    model=leaf(same_query=True)
    assert predict(model,[],BUILD)['predictions'].shape==(0,)
    assert features(model,[],BUILD)['features'].shape==(0,32)
    result=decompose_h2(model,model,[],[],BUILD)
    assert result['source_q'].shape==(0,4)
    assert result['counts']=={}
    row=boards()[4]
    expected=model.model.library.ntuple_value_v120(row,model.model.patterns,model.radix,model.weights)
    assert predict(model,[row],BUILD)['predictions'][0]==expected
