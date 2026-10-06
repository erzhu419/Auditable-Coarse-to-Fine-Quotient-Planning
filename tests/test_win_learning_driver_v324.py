"""Finite orchestration fixtures; no natural learning or evaluation pilot games."""
from collections import Counter
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import win_learning_run_v324 as driver

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'reports/win_learning_v324/test_logs' / f'driver_fixture_{os.getpid()}'


class Head:
    def __init__(self, model=None):
        self.model = model or SimpleNamespace(weights=np.zeros(8))
        self.kind = 'LOCAL_RISK'; self.updates = 0; self.counts = Counter()
        self.reward_weights = np.zeros(8); self.risk_weights = np.zeros(8)
    def freeze(self):
        self.reward_weights.flags.writeable = self.risk_weights.flags.writeable = False


def endpoints(seeds):
    return dict(game_summaries=[dict(seed=seed,status='LOST',utility=0.) for seed in seeds],
        counts=dict(environment={},planning={}),cpu_seconds=0.)


@pytest.mark.parametrize('split',[False,True])
def test_evaluate_uses_only_the_fixed_64_paired_natural_streams(monkeypatch,split):
    leaf = Head(); leaf.freeze(); leaf.updates = 7
    calls = []
    def natural(head,p_model,p_true,seeds,**kwargs):
        assert head is leaf and not head.reward_weights.flags.writeable and not head.risk_weights.flags.writeable
        assert (p_model,p_true) == (.375,.5)
        assert kwargs == dict(depth=2,max_steps=8192)
        calls.append(list(seeds)); return endpoints(seeds)
    def split_natural(head,p_model,p_true,seeds,runtime,**kwargs):
        assert runtime == BUILD and kwargs == dict(max_steps=8192)
        return natural(head,p_model,p_true,seeds,depth=2,**kwargs)
    monkeypatch.setattr(driver,'evaluate_split',split_natural)
    version = dict(file='fixture_v2.npz',updates=7) if split else None
    result = driver._evaluate(leaf,6,'B',dict(estimated_p_four=.375),BUILD,
        SimpleNamespace(evaluate_games=natural),version)
    assert calls == [[324900000000+6*1000000+100000+i for i in range(64)]]
    assert leaf.updates == 7 and result['head_version'] == version
    assert result['planner'] == 'H2' and result['static_evaluation_valid']


def test_evaluate_rejects_an_engine_that_updates_its_frozen_head():
    leaf = Head(); leaf.freeze()
    def hidden_fit(head,p_model,p_true,seeds,**kwargs):
        head.updates += 1; return endpoints(seeds)
    with pytest.raises(ValueError,match='evaluation changed'):
        driver._evaluate(leaf,0,'A',dict(estimated_p_four=.1),BUILD,
            SimpleNamespace(evaluate_games=hidden_fit))


def source_costs():
    return dict(source_training_raw_tiles=100,dynamics_raw_tiles=7,
        fresh_source_compute=dict(full_source_cpu_seconds=3.))


def test_training_cutoff_keeps_paid_partial_trace_and_stops_parent_before_another_life(monkeypatch):
    out = BUILD/'cutoff'; out.mkdir(parents=True,exist_ok=True)
    monkeypatch.setattr(driver,'load_leaf',lambda *args:(object(),{}))
    closed = []
    monkeypatch.setattr(driver,'NativeValueStream',lambda *args:SimpleNamespace(close=lambda:closed.append(True)))
    seen = []
    paid = dict(kind='TRAIN',phase='A0',lifecycle=0,parent=0,
        raw_spawns=[dict(rank=1,cell=0),dict(rank=2,cell=1),dict(rank=1,cell=2)],
        completed_games=[dict(episode=0,status='CUTOFF',steps=8192)])
    def cutoff(template,life,parent,stage,router,emit,runtime,**kwargs):
        seen.append((life,stage)); emit(deepcopy(paid))
        raise ValueError('V309 requires natural terminal games; training cutoff retained')
    monkeypatch.setattr(driver,'acquire_stage',cutoff)
    result = driver._run_parent(dict(parent=0),out)
    assert seen == [(0,'A0')] and closed == [True]
    assert result['status'] == 'COHORT_HOLD' and len(result['lifecycles']) == 1
    row = result['lifecycles'][0]
    assert row['failure'] == dict(kind='HOLD_TRAINING_CUTOFF',
        reason='V309 requires natural terminal games; training cutoff retained',task='A',round=0)
    assert row['initial'] == {} and row['rounds'] == {}
    assert json.loads((out/'lifecycle_receipts/life_0.json').read_text()) == row
    with gzip.open(result['trace_file'],'rt') as stream:
        tape = [json.loads(line) for line in stream]
    assert tape[0] == paid and tape[1]['kind'] == 'COHORT_HOLD'
    assert result['paid_factual_raw_tiles'] == 3 and result['paid_raw_by_phase'] == dict(A0=3,NONE=0)
    account = driver.accounting(source_costs(),[row],[result],0.,0.)
    assert account['new_initial_raw_tiles'] == account['new_training_raw_tiles'] == 3
    assert account['new_post_factual_raw_tiles'] == account['new_supervision_raw_tiles'] == 0
    assert account['new_evaluation_games'] == account['new_head_files'] == 0
    assert account['economic_training_raw_tiles_per_arm'] == dict(
        SOURCE=107,FIRST_LOCAL=110,FACTUAL_WIN=110,QUERY_WIN=110)


def install_finite_lifecycle(monkeypatch,events):
    monkeypatch.setattr(driver,'GROUPS',2)
    model = SimpleNamespace(weights=np.zeros(8))
    created, evaluated, collections, fits = [], [], [], []
    def new_head(template,kind,runtime,initial=None):
        head = Head(model)
        if initial is not None:
            np.copyto(head.reward_weights,initial.reward_weights); np.copyto(head.risk_weights,initial.risk_weights)
            head.updates = initial.updates
        created.append(head)
        return head,dict(private_weight_bytes=128)
    monkeypatch.setattr(driver,'_new_head',new_head)
    def initial(template,life,parent,stage,router,emit,runtime,**kwargs):
        index = 0 if stage=='A0' else 1
        return dict(route=dict(created=True,context_id=index),
            dataset=dict(fit_memory=dict(probability=.1 if index==0 else .5),fit_step_end=1,fit_game_count=1),
            acquisition=dict(cpu_seconds=0.))
    monkeypatch.setattr(driver,'acquire_stage',initial)
    def memory(payload):
        return SimpleNamespace(predict=lambda:payload['probability'],to_payload=lambda:payload)
    monkeypatch.setattr(driver,'SpawnMemory',SimpleNamespace(from_payload=memory))
    def first_fit(head,dataset,runtime,**kwargs):
        head.reward_weights[:] = 1.; head.risk_weights[:] = .25; head.updates = 1
        return dict(cpu_seconds=0.)
    monkeypatch.setattr(driver,'fit_split',first_fit)
    def evaluate(head,life,task,belief,runtime,engine,version=None):
        if version is not None:
            assert not head.reward_weights.flags.writeable and not head.risk_weights.flags.writeable
        evaluated.append((task,deepcopy(version)))
        return dict(endpoints([driver.evaluation_seed(life,task,i) for i in range(64)]),
            head_version=deepcopy(version),estimated_p_four=belief['estimated_p_four'])
    monkeypatch.setattr(driver,'_evaluate',evaluate)
    def collection(first,life,parent,arm,p_model,p_true,seed,batch,emit,runtime,**kwargs):
        assert first.updates == 1 and not first.reward_weights.flags.writeable and not first.risk_weights.flags.writeable
        collections.append((batch,seed,kwargs['actor_version']['version']))
        return dict(dataset=dict(fit_step_end=4,fit_game_count=1),acquisition=dict(cpu_seconds=0.,
            training=dict(before_stream=dict(stream_seed=seed))))
    monkeypatch.setattr(driver,'acquire_policy_data',collection)
    roots = np.ones((4,16),dtype=np.int32)
    monkeypatch.setattr(driver,'prepare_anchors',lambda *args:dict(preboards=roots,natural_roots=roots,
        indices=np.arange(4,dtype=np.int64),counts={},cpu_seconds=.125))
    monkeypatch.setattr(driver,'query_roots',lambda *args,**kwargs:dict(chosen_afterstates=roots,
        root_afterstates=roots+1,validmask=np.ones(4,dtype=np.int32),provenance=np.zeros((4,6),dtype=np.int64),
        selection_rule='FIXTURE',counts={},cpu_seconds=0.))
    def supervise(first,roots,p_true,seed,runtime,repeats):
        assert first.updates == 1 and repeats == 4
        query = bool(np.all(roots==2)); value = .8 if query else .4
        return dict(targetwin=np.full((2,4),value),targetreward=np.full((2,4),99.),
            selected_action=np.zeros((2,4),np.int32),targetkind=np.ones((2,4),np.int32),
            spawn_cells=np.zeros((2,4),np.int32),spawn_ranks=np.ones((2,4),np.int32),
            target_rule='FIXTURE',draw_seed=seed,counts=dict(supervision_start_spawns=8))
    monkeypatch.setattr(driver,'supervise',supervise)
    def fit(head,roots,targetwin,runtime,**kwargs):
        assert not head.reward_weights.flags.writeable and head.risk_weights.flags.writeable
        assert np.all(head.reward_weights==1.)
        fits.append((id(head),head.updates,head.risk_weights.copy(),float(targetwin[0,0])))
        head.risk_weights[:] += targetwin.mean(); head.updates += 2
        return dict(fitted_rootgroups=2,learning_counts=dict(rootgroup_updates=2))
    monkeypatch.setattr(driver,'fit_win_supervision',fit)
    return created,evaluated,collections,fits


def test_complete_orchestration_keeps_first_frozen_and_continues_each_private_win_lineage(monkeypatch):
    out = BUILD/'complete'; out.mkdir(parents=True,exist_ok=True); events = []
    created,evaluated,collections,fits = install_finite_lifecycle(monkeypatch,events)
    result = driver._run_life(object(),dict(parent=0,checkpoint='fixture_source.npz'),0,out/'runtime',out,None,events.append)
    assert 'failure' not in result and result['initial_context_precondition_met']
    assert [batch for batch,seed,version in collections] == ['A_R1','B_R1','A_R2','B_R2']
    assert [seed for batch,seed,version in collections] == [driver.collection_seed(0,t,n) for n in (1,2) for t in ('A','B')]
    assert all(version==0 for batch,seed,version in collections) and len(evaluated)==12
    assert len(created)==6 and len(fits)==8
    for task in ('A','B'):
        first = result['initial'][task]['head_version']; previous = {arm:first for arm in driver.UPDATING_ARMS}
        for number in ('1','2'):
            stage = result['rounds'][number][task]
            assert stage['teacher_unchanged'] and stage['teacher_version']==first
            assert stage['inactive_head_versions_before']==stage['inactive_head_versions_after']
            for arm in driver.UPDATING_ARMS:
                cell = stage['arms'][arm]; version = cell['head_version']
                assert version['base_file']==previous[arm]['file'] and version['reward_indices_count']==0
                assert version['updates']==1+2*int(number) and cell['reward_unchanged']
                with np.load(version['file'],allow_pickle=False) as saved:
                    assert saved['reward_indices'].size==saved['reward_values'].size==0
                    assert np.allclose(saved['terminal_values'],.25+int(number)*(.4 if arm=='FACTUAL_WIN' else .8))
                assert cell['supervision']['draw_seed']==driver.draw_seed(0,task,int(number))
                previous[arm] = version
    assert sum(event['kind']=='CONSOLIDATED_HEAD' for event in events)==8


def test_insufficient_census_retains_actual_collector_and_never_samples_labels(monkeypatch):
    out = BUILD/'census_hold'; out.mkdir(parents=True,exist_ok=True); events = []
    created,evaluated,collections,fits = install_finite_lifecycle(monkeypatch,events)
    def insufficient(*args):
        raise ValueError('V319 insufficient eligible complete FIT anchors for the frozen census')
    monkeypatch.setattr(driver,'prepare_anchors',insufficient)
    def no_labels(*args,**kwargs):
        raise AssertionError('A failed census cannot collect or fit replacement supervision')
    monkeypatch.setattr(driver,'supervise',no_labels)
    result = driver._run_life(object(),dict(parent=0,checkpoint='fixture_source.npz'),0,out/'runtime',out,None,events.append)
    assert result['failure']['kind']=='HOLD_CENSUS' and len(evaluated)==4 and fits==[]
    assert [batch for batch,seed,version in collections]==['A_R1']
    stage = result['rounds']['1']['A']
    assert stage['arms']=={} and stage['collectors']['FIXED_FIRST']['acquisition']['training']['before_stream']['stream_seed']==driver.collection_seed(0,'A',1)
    assert events[-1]['kind']=='COHORT_HOLD'
