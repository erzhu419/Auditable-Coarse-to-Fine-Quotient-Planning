"""Factual detector prefixes, first-acquisition ordering, and blind reuse."""
from collections import Counter
from copy import deepcopy

import pytest

from acfqp.science import first_adapt_data_v308 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.observed_context_v305 import ObservedContexts
from test_independent_actor_data_v291 import FrozenTemplate, RetainedStream, prepare


def setup(monkeypatch):
    budget = prepare(monkeypatch)
    monkeypatch.setattr(core, 'NativeValueStream', RetainedStream)
    return budget


def acquire(template, router, records, runtime, stage='A1', p_four=.1, budget=512):
    return core.acquire_stage(template,21,1,stage,router,records.append,runtime,
        p_four=p_four,warmup_seed_base=308100000000,training_seed_base=308200000000,raw_budget=budget)


def test_new_context_routes_from_full_warmup_before_one_physical_cohort(monkeypatch,tmp_path):
    budget=setup(monkeypatch); template=FrozenTemplate();router=ObservedContexts();records=[]
    result=acquire(template,router,records,tmp_path,budget=budget)
    kinds=[r['kind'] for r in records]
    detection=kinds.index('DETECTION_SNAPSHOT')
    assert all(k=='WARMUP' for k in kinds[:detection])
    assert kinds[detection+1]=='TRAIN' and kinds[-1]=='ACQUISITION_SNAPSHOT'
    assert kinds.count('DETECTION_SNAPSHOT')==kinds.count('ACQUISITION_SNAPSHOT')==1
    assert result['route']['created'] and result['route']['context_id']==0
    warm=result['acquisition']['warmup'];dataset=result['dataset']
    assert result['route']['statistics']['observations']==warm['raw_tiles']>=256
    assert router.banks[0]['observations']==warm['raw_tiles']
    assert dataset['actor_memory_A1_end']['observations_seen']==warm['raw_tiles']+budget
    assert dataset['fit_game_count']==6 and len(dataset['games'])==8
    assert result['acquisition']['physical_acquisitions']==1
    assert result['acquisition']['new_value_updates']==0 and template.updates==99
    assert result['acquisition']['training']['raw_tiles']==budget
    assert RetainedStream.instances[-1].closed
    assert all(r['summary']['seed']==308100000000+21*1000000+i for i,r in enumerate(records[:detection]))
    assert all(r['start']['stream_seed']==308200000000+21*10000000 for r in records if r['kind']=='TRAIN')
    assert result['detector_belief']==records[detection]['detector_belief']
    assert result['route']==records[detection]['route']


def test_reuse_pays_new_detector_games_but_never_constructs_training_stream(monkeypatch,tmp_path):
    budget=setup(monkeypatch);template=FrozenTemplate();router=ObservedContexts()
    first=acquire(template,router,[],tmp_path,budget=budget)
    before=deepcopy(router.banks);records=[]
    def no_stream(*args,**kwargs):
        raise AssertionError('A reused context constructed a training stream')
    monkeypatch.setattr(core,'NativeValueStream',no_stream)
    # Identical observed ranks must reuse even when the supplied world/task metadata changes.
    reused=acquire(template,router,records,tmp_path,stage='B',p_four=.5,budget=budget)
    assert reused['route']['context_id']==0 and not reused['route']['created']
    assert reused['dataset'] is None and reused['acquisition']['training'] is None
    assert reused['acquisition']['snapshot'] is None and reused['acquisition']['native_setup_counts']=={}
    assert reused['acquisition']['physical_acquisitions']==0
    assert reused['acquisition']['new_value_updates']==0 and template.updates==99
    assert {r['kind'] for r in records}=={'WARMUP','DETECTION_SNAPSHOT'}
    assert reused['acquisition']['warmup']['raw_tiles']==first['acquisition']['warmup']['raw_tiles']
    assert router.banks[0]['visits']==2
    assert router.banks[0]['observations']==2*before[0]['observations']
    assert router.counts['prototype_commits']==2


class BranchReplay:
    def __init__(self,expected,phase):
        self.expected=expected;self.phase=phase;self.memory=SpawnMemory('LIBRARY')
        self.processing=Counter();self.chunks=0;self.cpu_seconds=0.

    def train(self,row):
        for spawn in row['raw_spawns']: self.memory.observe(spawn['rank'])
        self.chunks+=1

    def checkpoint(self,row): pass

    def finish(self): return dict(costs={})


class BranchStream:
    creations=0

    def __init__(self,template,seed,runtime,max_steps):
        type(self).creations+=1;self.raw=0;self.setup_counts=Counter();self.setup_seconds=0.
        self.counts={kind:Counter() for kind in ('environment','planning','learning')}

    def state(self): return dict(raw_tiles=self.raw,pending_bank_id=None)

    def advance(self,template,bank,pending,pmodel,ptrue,tile_budget,max_postaction):
        before=self.state();self.raw+=tile_budget
        self.counts['environment']['raw_tile_productions']+=tile_budget
        return dict(start=before,end=self.state(),raw_spawns=[dict(rank=1) for _ in range(tile_budget)],
            actions=[],scores=[],completed_games=[],counts=dict(environment={'raw_tile_productions':tile_budget},
            planning={},learning={}),updates=[],seconds=0.,cpu_seconds=0.)

    def close(self): pass


def test_observed_a_b_a_sequence_commits_only_detector_evidence_and_skips_return_training(monkeypatch,tmp_path):
    # Branch-only fixture: native physics is covered by the first two retained-world tests.
    prefixes=iter((30,150,32));BranchStream.creations=0
    def warmup(template,life,parent,emit,replay,stage,ptrue,seed):
        memory=SpawnMemory('LIBRARY');k=next(prefixes)
        for rank in [2]*k+[1]*(300-k): memory.observe(rank)
        replay.memory=SpawnMemory.from_payload(memory.to_payload())
        emit(dict(kind='WARMUP',phase=stage,raw_spawns=[dict(rank=2)]*k+[dict(rank=1)]*(300-k)))
        return memory,dict(raw_tiles=300,memory_counts=dict(memory.counts))
    monkeypatch.setattr(core,'_warmup',warmup)
    monkeypatch.setattr(core,'_Replay',BranchReplay)
    monkeypatch.setattr(core,'NativeValueStream',BranchStream)
    router=ObservedContexts();template=FrozenTemplate();outcomes=[]
    for stage,p in [('A1',.1),('B',.5),('A2',.1)]:
        outcomes.append(acquire(template,router,[],tmp_path,stage=stage,p_four=p,budget=8))
    assert [x['route']['context_id'] for x in outcomes]==[0,1,0]
    assert [x['route']['created'] for x in outcomes]==[True,True,False]
    assert BranchStream.creations==2
    assert router.banks==[dict(context_id=0,observations=600,fours=62,visits=2),
        dict(context_id=1,observations=300,fours=150,visits=1)]
    assert router.counts['prototype_commits']==3
    assert outcomes[2]['dataset'] is None


def test_actual_training_cutoff_remains_retained_and_aborts_labels(monkeypatch,tmp_path):
    budget=setup(monkeypatch);monkeypatch.setattr(RetainedStream,'cutoff',True)
    records=[]
    with pytest.raises(ValueError,match='cutoff retained'):
        acquire(FrozenTemplate(),ObservedContexts(),records,tmp_path,budget=budget)
    assert any(r['kind']=='DETECTION_SNAPSHOT' for r in records)
    assert records[-1]['kind']=='TRAIN'
    assert any(g['status']=='CUTOFF' for g in records[-1]['completed_games'])
    assert not any(r['kind']=='ACQUISITION_SNAPSHOT' for r in records)
    assert RetainedStream.instances[-1].closed
