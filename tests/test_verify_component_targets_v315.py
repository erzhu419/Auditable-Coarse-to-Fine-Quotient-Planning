"""Finite V315 component ownership, new paired streams, no invented fitting cost."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_component_targets_v315 as audit
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import SplitLeaf

BUILD=Path(__file__).resolve().parents[1]/'reports/component_targets_v315/runtime/tests/independent_audit'


def previous_life():
    first=dict(file='FIRST_v0.npz',arm='FIRST_LOCAL',version=0,context_id=7)
    mc=dict(file='MC_v2.npz',arm='MC_LOCAL',version=2,context_id=7)
    td=dict(file='TD_v2.npz',arm='TD_LOCAL',version=2,context_id=7)
    return dict(initial={'A':dict(head_versions={'FIRST_LOCAL':first})},
        rounds={'2':{'A':dict(arms={'MC_LOCAL':dict(head_version=mc),'TD_LOCAL':dict(head_version=td)})}})


@pytest.mark.parametrize('arm',('TD_MC','MC_TD'))
def test_conditional_hybrid_cannot_swap_reward_and_win_component_versions(arm):
    old=previous_life(); components=audit.expected_components(old,'A',arm)
    audit.check_component_link(components,old,'A',arm)
    swapped=dict(reward_version=components['win_version'],win_version=components['reward_version'])
    with pytest.raises(ValueError,match='actual reward/WIN components'):
        audit.check_component_link(swapped,old,'A',arm)


def test_hybrid_cannot_borrow_other_context_or_stale_v1_component():
    old=previous_life(); components=audit.expected_components(old,'A','TD_TD')
    stale=deepcopy(components);stale['win_version']['version']=1
    with pytest.raises(ValueError,match='actual reward/WIN components'):
        audit.check_component_link(stale,old,'A','TD_TD')
    foreign=deepcopy(components);foreign['reward_version']['context_id']=8
    with pytest.raises(ValueError,match='actual reward/WIN components'):
        audit.check_component_link(foreign,old,'A','TD_TD')


@pytest.fixture(scope='module')
def probe():
    rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',11)
    source=NtupleValue(rule,BUILD)
    template=QueryTD(QueryParent(source,dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),.5),'PRIOR',BUILD);template.freeze()
    hybrid=SplitLeaf(template,'LOCAL_RISK',BUILD)
    hybrid.reward_weights[:]=.02;hybrid.risk_weights[:]=-.03;hybrid.freeze()
    seed=audit.evaluation_seed(0,'A',0);board,spawns=audit.initial_state(seed,.1)
    chosen=hybrid.choose(board,.37)
    return dict(episode=0,seed=seed,board=board,initial_spawns=spawns,chosen=chosen,
        origin='NATIVE_NEW_EVALUATION_INITIAL_STATE_SAME_H2_ENTRYPOINT',repeated_initial_random_draws=4),SimpleNamespace(
        reward=hybrid.reward_weights.reshape(-1),terminal=hybrid.risk_weights.reshape(-1))


def test_actual_initial_board_native_hybrid_probe_matches_literal_all_actions(probe):
    row,head=probe
    assert audit.check_probe(row,0,'A',.37,head,head)['action']==row['chosen']['action']


def test_declared_correct_components_cannot_hide_actual_wrong_win_table(probe):
    row,head=probe;wrong=SimpleNamespace(terminal=np.zeros_like(head.terminal))
    with pytest.raises(ValueError,match='literal H2 candidate'):
        audit.check_probe(row,0,'A',.37,head,wrong)


@pytest.mark.parametrize('field',('seed','board'))
def test_probe_cannot_use_stale_seed_or_arbitrary_unrecorded_board(probe,field):
    row,head=probe;changed=deepcopy(row)
    changed[field]=314900000000 if field=='seed' else [1,1]+[0]*14
    with pytest.raises(ValueError,match='actual seeded initial board'):
        audit.check_probe(changed,0,'A',.37,head,head)


def test_new_component_evaluation_cannot_reuse_v314_game_seed():
    games=[dict(seed=314900000000+episode) for episode in range(32)]
    with pytest.raises(ValueError,match='new V315 paired'):
        audit.check_evaluation(dict(estimated_p_four=.37,planner='H2',game_summaries=games),0,'A',.37)


def test_all_new_component_evaluation_cells_keep_same_observed_bank_probability():
    with pytest.raises(ValueError,match='immutable V314 bank probability'):
        audit.check_evaluation(dict(estimated_p_four=.1),0,'A',.37)
def test_component_state_cannot_claim_new_fit_copies_or_parameter_writes():
    components=dict(reward_version=dict(updates=40),win_version=dict(updates=50))
    before=dict(reward_updates=40,win_updates=50)
    state=dict(before=before,after=dict(before),weight_copy_parameters=0,allocated_weight_bytes=0,
        weight_files_saved=0,new_fit_states=0,new_parameter_writes=0)
    audit.check_component_state(state,components)
    for key in ('weight_copy_parameters','allocated_weight_bytes','weight_files_saved','new_fit_states','new_parameter_writes'):
        changed=dict(state,**{key:1})
        with pytest.raises(ValueError,match='without fitting parameter copies'):
            audit.check_component_state(changed,components)
    changed=deepcopy(state);changed['after']['win_updates']+=1
    with pytest.raises(ValueError,match='immutable references'):
        audit.check_component_state(changed,components)


def test_prior_pipeline_cpu_is_carried_once_and_new_costs_are_not_double_added():
    prior=dict(economic_source_and_target_cpu_seconds=100.)
    account=dict(worker_cpu_seconds=5.,compiler_cpu_seconds=2.,coordinator_cpu_seconds=1.,
        new_evaluation_total_cpu_seconds=8.,economic_source_and_target_and_new_cpu_seconds=108.)
    audit.check_compute(account,prior)
    account['economic_source_and_target_and_new_cpu_seconds']+=2.
    with pytest.raises(ValueError,match='inherited once'):
        audit.check_compute(account,prior)


def family_contrast():
    values=[-.2]*4+[.8]*4+[-.2]*4+[.8]*4
    return dict(mean=.3,ci95=[.02,.58],ci99=[-.05,.65],lifecycle_deltas={str(i):v for i,v in enumerate(values)},
        parent_mean_deltas={str(p):.3 for p in range(4)},interval_scope=audit.INTERVAL_SCOPE,
        improved_equal_worse=[8,0,8],adverse_lifecycles=[i for i,v in enumerate(values) if v<0],family_status='UNRESOLVED'),values


def test_positive_pointwise_interval_cannot_select_positive_family_effect():
    contrast,values=family_contrast();audit.check_contrast(contrast,values,True)
    assert audit.effect_status(contrast['ci95'],True)=='SUPPORTED_POSITIVE'
    assert audit.effect_status(contrast['ci99'],True)=='UNRESOLVED'
    narrowed=dict(contrast,ci99=[.03,.57])
    with pytest.raises(ValueError,match='enclose the pointwise 95%'):
        audit.check_contrast(narrowed,values,True)


def test_task_or_secondary_effect_cannot_be_upgraded_to_adjusted_family_decision():
    contrast,values=family_contrast()
    with pytest.raises(ValueError,match='do not acquire family decisions'):
        audit.check_contrast(contrast,values,False)
    descriptive={key:value for key,value in contrast.items() if key not in ('ci99','family_status')}
    audit.check_contrast(descriptive,values,False)


def test_signed_component_effect_cannot_drop_adverse_lifecycle():
    contrast,values=family_contrast();contrast['adverse_lifecycles'].pop()
    with pytest.raises(ValueError,match='adverse realized component effects'):
        audit.check_contrast(contrast,values,True)


def test_exact_new_config_has_zero_fit_and_five_family_components():
    import json
    from acfqp.science.component_target_run_v315 import configuration
    prior=Path(__file__).resolve().parents[1]/'reports/local_targets_v314/summary.json'
    actual=json.loads(json.dumps(configuration(prior)))
    audit.equal_tree(actual,audit.expected_configuration(prior),'exact V315 configuration')
    assert actual['expected_evaluation_games']==5120 and actual['new_fit_states']==0
    assert len(actual['mechanism_family'])==5 and actual['mechanism_family_ci']==.99
