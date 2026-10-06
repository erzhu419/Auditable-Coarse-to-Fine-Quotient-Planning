"""Real retained-critic fits and exact replay budgets without world acquisition."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import experience_replay_v307 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1]/'reports/experience_replay_v307/runtime/tests/driver'


def dataset(reward=.1):
    memory = SpawnMemory('POOLED')
    for _ in range(256):
        memory.observe(1)
    return dict(lifecycle=0, parent=0,
        afterstates=np.tile([1,1,0,0]+[0]*12, (7,1)).astype(np.int32),
        rewards=np.asarray([reward]*4+[31.,47.,59.]),
        ends=np.asarray([2,4,7], dtype=np.int64), terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2, fit_step_end=4, fit_end_raw=8, fit_memory=memory.to_payload(),
        costs=dict(excluded_tail_raw_tiles=3),
        games=[dict(episode=i, split='FIT' if i<2 else 'HELDOUT', status='LOST',
                    steps=2 if i<2 else 3) for i in range(3)])


def fixture(monkeypatch):
    rule = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
        ((1,Fraction(9,10)),(2,Fraction(1,10))), 'uniform', 11)
    template = QueryTD(QueryParent(NtupleValue(rule,BUILD),core.QUERY,core.QUERY,.5), 'PRIOR',BUILD)
    template.freeze()
    old, current = dataset(), dataset(.8)
    initial, _ = core.new_head(template,BUILD)
    initial_fit = core.fit_split(initial,old,BUILD,alpha=.0025)
    initial.freeze()
    next_head, _ = core.new_head(template,BUILD,initial)
    current_fit = core.fit_split(next_head,current,BUILD,alpha=.0025)
    memory = SpawnMemory.from_payload(old['fit_memory']); p = memory.predict()
    previous = dict(lifecycle=0, parent=0,
        evaluation_beliefs={'A':dict(memory=memory.to_payload(),estimated_p_four=p)},
        stages={'A1':dict(arms={'LOCAL_RISK':dict(fit=initial_fit)})})
    receipt = dict(arms={'CURRENT_DATA':dict(fit=current_fit)})
    evaluations = []
    def evaluate(leaf, planning_p, true_p, seeds, runtime, max_steps):
        assert planning_p==1/258 and true_p==.1 and max_steps==8192
        assert seeds==[307900000000+episode for episode in range(32)]
        assert not leaf.reward_weights.flags.writeable and not leaf.risk_weights.flags.writeable
        evaluations.append(leaf.updates)
        return dict(game_summaries=[dict(seed=seed,status='LOST',utility=-4.,steps=1) for seed in seeds],
            counts=dict(environment={},planning={}),representation_counts={},setup_counts={},
            seconds=0.,cpu_seconds=0.)
    monkeypatch.setattr(core,'evaluate_split',evaluate)
    return template, previous, receipt, old, current, evaluations


def test_real_update_branches_copy_identical_a1_and_reproduce_unmasked_new_fit(monkeypatch):
    template,previous,receipt,old,current,evaluations = fixture(monkeypatch)
    fits = []; native = core.fit_masked_split
    def tracked(leaf,data,mask,runtime,alpha):
        fits.append(dict(updates=leaf.updates,reward=leaf.reward_weights.copy(),
            risk=leaf.risk_weights.copy(),data=data,mask=mask.copy()))
        return native(leaf,data,mask,runtime,alpha=alpha)
    monkeypatch.setattr(core,'fit_masked_split',tracked)
    result = core._run_lifecycle(template,previous,receipt,old,current,BUILD)
    assert len(fits)==2 and fits[0]['updates']==fits[1]['updates']==4
    np.testing.assert_array_equal(fits[0]['reward'],fits[1]['reward'])
    np.testing.assert_array_equal(fits[0]['risk'],fits[1]['risk'])
    assert core.scientific_identity(result['initial_fit'])==core.scientific_identity(previous['stages']['A1']['arms']['LOCAL_RISK']['fit'])
    assert core._new_identity(result['arms']['NEW_ONLY']['fit'])==core.scientific_identity(receipt['arms']['CURRENT_DATA']['fit'])
    assert evaluations==[0,4,8,8]
    assert template.updates==0 and result['arms']['SOURCE']['head_updates_after']==0
    assert result['arms']['A1_FROZEN']['head_updates_after']==4
    for arm in ('NEW_ONLY','MIXED_REPLAY'):
        row = result['arms'][arm]
        assert (row['head_updates_before'],row['head_updates_after'])==(4,8)
        assert row['head_setup']['setup_counts']['a1_weight_bytes_copied']==row['head_setup']['private_weight_bytes']


def test_exact_selection_budget_preserves_full_game_targets_and_excludes_heldout(monkeypatch):
    template,previous,receipt,old,current,_ = fixture(monkeypatch)
    saved = [deepcopy(data) for data in (old,current)]
    fits = []; native = core.fit_masked_split
    def tracked(leaf,data,mask,runtime,alpha):
        fits.append((data,mask.copy()))
        return native(leaf,data,mask,runtime,alpha=alpha)
    monkeypatch.setattr(core,'fit_masked_split',tracked)
    result = core._run_lifecycle(template,previous,receipt,old,current,BUILD)
    replay = result['replay']
    assert replay['budget']==4
    assert replay['plans']['MIXED_REPLAY']['quotas']==dict(OLD_A1=2,CURRENT_DATA=2)
    assert [int(mask.sum()) for _,mask in fits]==[4,4]
    assert fits[0][0] is current
    assert fits[0][1].shape==(current['fit_step_end'],)
    mixed_data, _ = fits[1]
    assert mixed_data['fit_game_count']==2 and mixed_data['fit_step_end']==4
    assert mixed_data['rewards'].tolist()==[.1,.1,.8,.8]
    assert mixed_data['ends'].tolist()==[2,4]
    assert mixed_data['terminal_codes'].tolist()==[-1,-1]
    for record in replay['plans']['MIXED_REPLAY']['games']:
        source = old if record['source']=='OLD_A1' else current
        assert source['games'][record['source_game']]['split']=='FIT'
        assert record['source_end']<=source['fit_step_end']
    # Afterstate targets use the remaining game rewards, excluding the current action.
    fit = result['arms']['MIXED_REPLAY']['fit']
    assert fit['first_sample']['reward_target']==pytest.approx(.1)
    assert fit['last_sample']['reward_target']==0.
    assert fit['target_counts']['reward_suffix_target_assignments']==4
    assert fit['first_sample']['risk_target']==fit['last_sample']['risk_target']==0.
    for actual,before in zip((old,current),saved):
        for key in ('afterstates','rewards','ends','terminal_codes'):
            np.testing.assert_array_equal(actual[key],before[key])
        assert actual['games']==before['games'] and actual['costs']==before['costs']


def test_bad_retained_a1_receipt_stops_before_any_evaluation_or_replay_fit(monkeypatch):
    template,previous,receipt,old,current,evaluations = fixture(monkeypatch)
    previous['stages']['A1']['arms']['LOCAL_RISK']['fit']['alpha']=.01
    calls = []
    monkeypatch.setattr(core,'fit_masked_split',lambda *a,**k:calls.append(a))
    with pytest.raises(ValueError,match='initial A1 fit did not reproduce V303'):
        core._run_lifecycle(template,previous,receipt,old,current,BUILD)
    assert not calls and not evaluations


def test_bad_new_only_fit_receipt_stops_before_updating_arm_evaluations(monkeypatch):
    template,previous,receipt,old,current,evaluations = fixture(monkeypatch)
    receipt['arms']['CURRENT_DATA']['fit']['alpha']=.01
    calls = []; native = core.fit_masked_split
    def tracked(leaf,data,mask,runtime,alpha):
        calls.append(leaf.updates)
        return native(leaf,data,mask,runtime,alpha=alpha)
    monkeypatch.setattr(core,'fit_masked_split',tracked)
    with pytest.raises(ValueError,match='new-only fit did not reproduce V306 CURRENT_DATA'):
        core._run_lifecycle(template,previous,receipt,old,current,BUILD)
    assert calls==[4]
    assert evaluations==[0,4]


def test_wrong_supervised_receipt_budget_cannot_reach_updating_arm_evaluation(monkeypatch):
    template,previous,receipt,old,current,evaluations = fixture(monkeypatch)
    native = core.fit_masked_split
    def wrong(leaf,data,mask,runtime,alpha):
        result = native(leaf,data,mask,runtime,alpha=alpha)
        result['trained_afterstates']-=1
        return result
    monkeypatch.setattr(core,'fit_masked_split',wrong)
    with pytest.raises(ValueError,match='supervised-state budgets differ'):
        core._run_lifecycle(template,previous,receipt,old,current,BUILD)
    assert evaluations==[0,4]


def test_retained_raw_is_paid_without_new_acquisition_and_updates_match_exact_budget(monkeypatch):
    template,previous,receipt,old,current,_ = fixture(monkeypatch)
    row = core._run_lifecycle(template,previous,receipt,old,current,BUILD)
    inherited = dict(accounting=dict(inherited_a1_raw_tiles=27,
        new_training_raw_tiles_by_actor={'CURRENT_DATA':64},
        economic_training_raw_tiles_per_arm=dict(SOURCE=132,A1_FROZEN=132,CURRENT_DATA=196),
        inherited_costs_per_arm={'SOURCE':dict(source_training_raw_tiles=100,dynamics_raw_tiles=5)}))
    parent = dict(reconstruction={source:dict(cpu_seconds=.1,counts={}) for source in ('OLD_A1','CURRENT_DATA')},
        cpu_seconds=1.,compiler_cpu_seconds=.2)
    cost = core.build_accounting(inherited,[row],[parent],.1,1.)
    assert cost['new_training_environment_observations']==cost['new_training_acquisitions']==0
    assert cost['inherited_a1_raw_tiles']==27 and cost['inherited_current_raw_tiles']==64
    assert cost['economic_training_raw_tiles_per_arm']==dict(SOURCE=132,A1_FROZEN=132,NEW_ONLY=196,MIXED_REPLAY=196)
    assert cost['matched_supervised_state_budget_per_updating_arm']==4
    assert cost['new_processed_training_samples']==dict(SOURCE=0,A1_FROZEN=0,NEW_ONLY=4,MIXED_REPLAY=4)
    assert cost['initial_replayed_training_samples']==4
    assert cost['new_evaluation_games']==128
    assert cost['head_setup_counts']['A1_FROZEN']==row['initial_head_setup']['setup_counts']
    assert cost['worker_cpu_seconds']==1. and cost['coordinator_cpu_seconds']==.1
    assert not cost['historical_total_compute_closed']


def test_freeze_reuses_training_facts_and_only_introduces_v307_evaluation_seeds():
    settings = core.configuration(BUILD/'v303.json',BUILD/'v306.json')
    assert settings['arms']==core.ARMS
    assert settings['seed_evaluation']==307900000000
    assert settings['new_training_environment_observations']==0 and settings['new_evaluation_games']==8192
    assert settings['retained_actor']=='CURRENT_DATA'
    assert settings['primary']=='MIXED_REPLAY_minus_NEW_ONLY'
    assert settings['training_budget']=='ALL_CURRENT_FIT_NONWINNING_AFTERSTATES_PER_LIFECYCLE'
    assert settings['targets']=='ORIGINAL_COMPLETE_NATURAL_GAME_SUFFIX_AND_WIN_LABEL'
    assert settings['fit_scope']=='ORIGINAL_80_PERCENT_COMPLETE_GAME_PREFIX_NO_HELDOUT_OR_TAIL'
    assert settings['bootstrap_seed']==30700001 and settings['interval_scope']==core.INTERVAL_SCOPE
    assert core.evaluation_seed(5,31)==307905000031
