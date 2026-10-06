"""Small driver receipts and a real tiny-model continuation, without formal RNGs."""
from copy import deepcopy
from fractions import Fraction
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import long_horizon_advantage_v296 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


def old_anchor():
    actions = ('DOWN', 'LEFT', 'RIGHT', 'UP')
    utilities = dict(DOWN=0., LEFT=-1., RIGHT=2., UP=2.)
    rollouts = [dict(action=a, replica_index=i, seed=294600010000+i,
        total_utility=utilities[a], suffix_utility=utilities[a]-(.25 if a=='RIGHT' else 0.),
        first_score=512 if a=='RIGHT' else 0, total_score=int((utilities[a]+4.)*2048),
        status='LOST', steps=20, final_board=[1, 2]*8) for a in actions for i in range(32)]
    return dict(anchor_id='L00-B-Q0', lifecycle=0, parent=0, phase='B', phase_index=1,
        anchor_index=0, episode=7, step=5, board_before_action=[0]*5+[2, 2]+[0]*9,
        model_p_four=.03, choices={
            'FROZEN':dict(action='DOWN', action_values={a:{} for a in actions}),
            'BELLMAN_CONDITIONED':dict(action='LEFT', action_values={a:{} for a in actions})},
        reference=dict(rollouts=rollouts, counts=dict(environment={'sampled_transitions':2560},
            planning={}, rollout={}), seconds=1., cpu_seconds=1., model_p_four=.03, environment_p_four=.5),
        choice_counts={})


def original():
    accounting = dict(economic_training_raw_tiles_per_arm={'FROZEN':1000},
        inherited_costs_per_arm={'FROZEN':{'source_training_raw_tiles':700}},
        reused_carrier_raw_tiles=200, reused_carrier_counts={}, reused_warmup_raw_tiles=100,
        reused_warmup_environment_counts={}, reused_warmup_direct_counts={}, reused_warmup_memory_counts={},
        physical_ranking_rollouts=128, ranking_reference_counts={'environment':{'sampled_transitions':2560}},
        ranking_reference_cpu_seconds=1., ranking_choice_counts_per_arm={'FROZEN':{},'BELLMAN_CONDITIONED':{}},
        fit_counts_per_arm={'BELLMAN_CONDITIONED':{}}, fit_cpu_seconds_per_arm={'BELLMAN_CONDITIONED':2.},
        processed_training_samples_per_arm={'BELLMAN_CONDITIONED':10})
    return dict(by_lifecycle=[dict(lifecycle=0,parent=0,ranking={p:dict(anchors=[old_anchor()] if p=='B' else [])
        for p,_ in core.PHASES})],accounting=accounting,source_provenance={'parents':[{'parent':0}]})


def selection():
    return core.freeze_selection(original(), 'old_summary.json')


def isolate_seeds(monkeypatch):
    monkeypatch.setattr(core, 'validation_seed', lambda life, phase, anchor, replica:
        296000030000+life*1000+phase*100+anchor*10+replica)


def test_selection_uses_old_total_utility_and_lexical_tie_preserving_all_candidates():
    data = original()
    selected = core.freeze_selection(data, 'old_summary.json')
    anchor = selected['by_lifecycle'][0]['phases']['B']['anchors'][0]
    assert anchor['discovery_action'] == 'RIGHT'  # suffix would choose UP.
    assert anchor['validation_actions'] == ['DOWN','LEFT','RIGHT']
    assert anchor['source_action']=='DOWN' and anchor['bellman_action']=='LEFT'
    assert anchor['discovery_action_means']['LEFT'] == -1.
    assert selected['anchor_count']==1 and selected['physical_validation_rollouts']==96
    changed = deepcopy(data)
    changed['by_lifecycle'][0]['ranking']['B']['anchors'][0]['validation_reference']={'rollouts':[{'total_utility':1e6}]}
    assert core.freeze_selection(changed,'old_summary.json')['by_lifecycle'][0]['phases']['B']['anchors'][0]['discovery_action']=='RIGHT'


def test_worker_requires_saved_selection_and_preserves_union_model_env_and_paired_seeds(tmp_path, monkeypatch):
    isolate_seeds(monkeypatch)
    selected = selection(); calls=[]
    leaf = SimpleNamespace(weights=np.zeros(1),updates=0)
    leaf.weights.flags.writeable=False
    monkeypatch.setattr(core,'load_leaf',lambda source,runtime:(leaf,{'setup_counts':{},'cpu_seconds':.1}))
    class MockContinuation:
        def __init__(self,leaf,runtime):
            self.setup_counts={};self.setup_seconds=0.
        def evaluate(self,board,actions,p,seeds,max_steps,environment_p_four):
            assert (tmp_path/'selection.json').exists()
            calls.append((list(actions),p,environment_p_four,list(seeds),max_steps))
            rows=[dict(action=a,replica_index=i,seed=s,total_utility=-1.,suffix_utility=-1.,
                first_score=0,total_score=6144,status='LOST',steps=3,final_board=[1,2]*8)
                for a in actions for i,s in enumerate(seeds)]
            return dict(rollouts=rows,counts=dict(environment={'sampled_transitions':3*len(rows),
                'environment_random_draws':6*len(rows)},planning={},rollout={'completed_rollouts':len(rows)}),
                seconds=.2,cpu_seconds=.1)
    monkeypatch.setattr(core,'NativeContinuation',MockContinuation)
    with pytest.raises(ValueError,match='saved before'):
        core._run_parent({'parent':0},selected['by_lifecycle'],tmp_path,replicas=2,max_steps=4)
    assert not calls
    (tmp_path/'selection.json').write_text(json.dumps(selected))
    parent=core._run_parent({'parent':0},selected['by_lifecycle'],tmp_path,replicas=2,max_steps=4)
    assert calls==[(['DOWN','LEFT','RIGHT'],.03,.5,[296000030100,296000030101],4)]
    result=parent['lifecycles'][0]['phases']['B']['anchors'][0]
    assert result['discovery_action']=='RIGHT' and result['validation_reference']['model_p_four']==.03
    assert result['validation_reference']['environment_p_four']==.5
    with gzip.open(parent['trace_file'],'rt') as stream:
        rows=[json.loads(line) for line in stream]
    assert len(rows)==1 and rows[0]['kind']=='VALIDATION_ANCHOR'
    assert parent['source_updates_before']==parent['source_updates_after']==0


def test_actual_tiny_native_driver_costs_censoring_and_readonly_source(tmp_path,monkeypatch):
    isolate_seeds(monkeypatch)
    selected=selection()
    anchor=selected['by_lifecycle'][0]['phases']['B']['anchors'][0]
    anchor['source_action']=anchor['bellman_action']=anchor['discovery_action']='LEFT'
    anchor['validation_actions']=['LEFT']
    (tmp_path/'selection.json').write_text(json.dumps(selected))
    captured={}
    def load(source,runtime):
        rule=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
            ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform',4)
        native=NtupleValue(rule,runtime)
        leaf=QueryTD(QueryParent(native,core.QUERY,core.QUERY,.5),'PRIOR',runtime)
        leaf.freeze();captured['leaf']=leaf;captured['before']=leaf.weights.copy()
        return leaf,dict(setup_counts=dict(native.setup_counts+leaf.setup_counts),cpu_seconds=0.)
    monkeypatch.setattr(core,'load_leaf',load)
    parent=core._run_parent({'parent':0},selected['by_lifecycle'],tmp_path,replicas=2,max_steps=2)
    lives=parent['lifecycles'];ref=lives[0]['phases']['B']['anchors'][0]['validation_reference']
    assert len(ref['rollouts'])==2 and {r['seed'] for r in ref['rollouts']}=={296000030100,296000030101}
    assert ref['counts']['environment']['sampled_transitions']==sum(r['steps'] for r in ref['rollouts'])
    assert ref['counts']['environment']['environment_random_draws']==2*sum(r['steps'] for r in ref['rollouts'])
    assert all(r['steps']==2 and r['status']=='CUTOFF' for r in ref['rollouts'])
    for r in ref['rollouts']:
        bonus=4. if r['status']=='WON' else -4. if r['status']=='LOST' else 0.
        assert r['total_utility']==r['total_score']/2048.+bonus
        assert r['suffix_utility']+r['first_score']/2048.==r['total_utility']
    np.testing.assert_array_equal(captured['leaf'].weights,captured['before'])
    assert captured['leaf'].updates==0 and not captured['leaf'].weights.flags.writeable
    costs=core.build_accounting(selected,lives,[parent],.1,.2)
    assert costs['physical_validation_rollouts']==2 and costs['logical_candidate_references']==6
    assert costs['new_environment_raw_tiles']==sum(r['steps'] for r in ref['rollouts'])
    assert costs['reused_selection_costs']==selected['reused_selection_costs']
    assert costs['new_training_environment_raw_tiles']==costs['new_value_updates']==0


def test_actual_roster_freeze_is_readonly_and_keeps_all_144_old_anchors():
    # Reading retained compact values starts no new environment or source model.
    path=Path(__file__).resolve().parents[1]/'reports/conditional_bellman_v294/summary.json'
    data=json.loads(path.read_text())
    selected=core.freeze_selection(data,path)
    assert selected['anchor_count']==144
    assert selected['union_size_counts']=={'1':58,'2':80,'3':6}
    assert selected['physical_validation_rollouts']==7552
    assert selected['paired_replica_seedstreams']==4608
    assert selected['logical_candidate_references']==13824
    assert selected['reused_selection_costs']['discovery_rollouts']==16096
