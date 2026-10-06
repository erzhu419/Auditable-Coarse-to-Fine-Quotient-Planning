"""Synthetic common-seed replication wiring; no physical or native games."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_module_replication_v152 as runner

TEMP=Path(__file__).resolve().parents[1]/'reports/v152_runtime_tmp'
MOCK_WORK=Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True)
    before=request.session.testsfailed
    yield
    path=TEMP/'runner_checks.json'
    payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before,environment_samples=0,
        native_calls=0,training_updates=0,synthetic_work=dict(MOCK_WORK),
        scope='Mocked source models, policy games and workers; no original checkpoint reads.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_',dir=TEMP) as folder:
        yield Path(folder)


def test_common_fresh_seed_rosters_count_physical_games_once():
    physical,logical=runner.rosters()
    assert len(physical)==1152 and len(logical)==2560
    ids={r['physical_id']:r for r in physical}
    assert len(ids)==len(physical)
    expected_seeds={runner.evaluation_seed(l,r) for l in range(4) for r in range(16)}
    assert len(expected_seeds)==64 and min(expected_seeds)==15290000000
    assert {r['seed'] for r in physical}=={r['seed'] for r in logical}==expected_seeds
    assert Counter(r['method'] for r in physical)=={'H2':128,'LEARN1':512,'LEARN8':512}
    assert Counter(r['checkpoint'] for r in physical)=={-1:128,1:256,2:256,3:256,4:256}
    for row in logical:
        source=ids[row['physical_id']]
        assert source['life']==row['life'] and source['replica']==row['replica'] and source['seed']==row['seed']
        key=runner.physical_key(row['life'],row['query'],row['checkpoint'],row['method'],row['replica'])
        assert key==tuple(source[k] for k in ('life','query','checkpoint','method','replica'))
        if row['method']=='ALT':
            assert source['query']!=row['query'] and source['method']=='H2' and source['checkpoint']==-1
        elif row['method']=='H2' or row['checkpoint']==0:
            assert source['query']==row['query'] and source['method']=='H2' and source['checkpoint']==-1
        else:
            assert all(source[k]==row[k] for k in ('query','checkpoint','method','duration'))
    assert Counter(Counter(r['physical_id'] for r in logical).values())=={12:128,1:1024}


def synthetic_sources(folder):
    source=folder/'source';source.mkdir();run=dict(status='complete',lifecycles=[])
    capsule=dict(snapshots=[dict(life=l) for l in range(4)],cost_refs=[dict(path='earlier',fields=['costs'])])
    for life in range(4):
        lifecycle=dict(life=life,checkpoints=[]);run['lifecycles'].append(lifecycle)
        for cp in range(5):
            checkpoint=dict(checkpoint=cp,models={});lifecycle['checkpoints'].append(checkpoint)
            for query in runner.QUERIES:
                checkpoint['models'][query]={}
                for duration in (1,8):
                    payload=dict(schema='acfqp.root_consequences.v151',radix=11,frozen=True,
                        updates=cp*10,weights=[] if cp==0 else [[duration,float(cp),0.,-1.]])
                    relative=f'life_{life}/{query}_{cp}_{duration}.json';path=source/relative
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload))
                    checkpoint['models'][query][str(duration)]=dict(model_ref=relative,
                        frozen_state=runner.model_state(payload))
    return source,capsule,run,dict(complete=True,primary_complete=True)


@pytest.mark.parametrize('patch,valid',[
    ({},True),({'frozen':False},False),({'updates':1},False),({'weights':[[1,0.,0.,0.]]},False)])
def test_zero_alias_requires_the_actual_unchanged_zero_checkpoint(patch,valid):
    payload=dict(radix=11,frozen=True,updates=0,weights=[]);payload.update(patch)
    assert runner.zero_checkpoint_valid(payload) is valid


def test_source_copies_all_checkpoints_before_execution_without_changing_them(local_tmp,monkeypatch):
    source,capsule,run,analysis=synthetic_sources(local_tmp);before=deepcopy((capsule,run))
    monkeypatch.setattr(runner,'SOURCE',source);target=local_tmp/'frozen';target.mkdir()
    extracted=runner.extract_source(capsule,run,analysis,target)
    assert (capsule,run)==before and len(extracted['models'])==80
    assert Counter(e['checkpoint'] for e in extracted['models'])=={c:16 for c in range(5)}
    assert extracted['source_run_ref']==str(source/'run.json')
    for entry in extracted['models']:
        original=Path(entry['source_model_ref']);copied=target/entry['model_ref']
        assert original.read_bytes()==copied.read_bytes()
        assert json.loads(copied.read_text())['frozen']
    entry=extracted['models'][-1];original=Path(entry['source_model_ref']);copy_before=(target/entry['model_ref']).read_bytes()
    original.write_text('{"changed_after_freeze":true}')
    assert (target/entry['model_ref']).read_bytes()==copy_before


def test_nonzero_checkpoint_zero_is_rejected_before_aliasing(local_tmp,monkeypatch):
    source,capsule,run,analysis=synthetic_sources(local_tmp);monkeypatch.setattr(runner,'SOURCE',source)
    item=run['lifecycles'][0]['checkpoints'][0]['models']['risk1']['1']
    payload=json.loads((source/item['model_ref']).read_text());payload['weights']=[[3,1.,0.,0.]]
    item['frozen_state']=runner.model_state(payload);(source/item['model_ref']).write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='checkpoint zero'):
        runner.extract_source(capsule,run,analysis,local_tmp/'rejected')


class Model:
    instances=[]
    @classmethod
    def from_payload(cls,payload):
        model=cls();model.payload=deepcopy(payload);model.frozen=payload['frozen']
        model.counts=Counter();model.setup_counts=Counter(stub_load=1);model.setup_seconds=0.
        cls.instances.append(model);MOCK_WORK['model_load_stubs']+=1;return model
    def state(self):return runner.model_state(self.payload)
    def update(self,*args,**kwargs):pytest.fail('V152 attempted to fit a model')
    def predict(self,board):
        assert self.frozen
        self.counts['root_predictions']+=1;MOCK_WORK['prediction_stubs']+=1
        return [1.,0.,0.]


def test_lifecycle_runs_only_distinct_physical_games_and_never_fits(local_tmp,monkeypatch):
    source,capsule,run,analysis=synthetic_sources(local_tmp);monkeypatch.setattr(runner,'SOURCE',source)
    target=local_tmp/'frozen';target.mkdir();extracted=runner.extract_source(capsule,run,analysis,target)
    Model.instances=[];monkeypatch.setattr(runner,'RootConsequences',Model)
    monkeypatch.setattr(runner,'load_teacher',lambda *a:({}, {},SimpleNamespace(counts=Counter()),{}))
    monkeypatch.setattr(runner,'leaf_state',lambda *a:{})
    calls=[]
    def play(bank,query,method,duration,model,seed,max_steps):
        calls.append((query,method,duration,seed,max_steps));MOCK_WORK['game_stubs']+=1
        assert max_steps==2000 and method!='ALT'
        if model is not None:model.predict([1]+[0]*15)
        else:assert method=='H2' and duration==0
        bank[query].counts['choose_calls']+=1
        cutoff=method=='H2' and query=='risk8' and seed==runner.evaluation_seed(1,15)
        result=dict(score=2048,steps=2,status='CUTOFF' if cutoff else 'WON',components=[1.,0.,float(not cutoff)],
            utility=None if cutoff else 1.+runner.QUERIES[query]['goal_bonus'],
            environment_counts=dict(sampled_transitions=2),policy_counts=dict(choose_calls=1))
        return dict(seed=seed,query=query,method=method,duration=duration,result=result),{}
    monkeypatch.setattr(runner,'play_game',play)
    result=runner.lifecycle(dict(life=1),extracted['models'],target)
    assert len(calls)==result['physical_games']==288
    assert Counter(c[1] for c in calls)=={'H2':32,'LEARN1':128,'LEARN8':128}
    assert len(Model.instances)==len(result['models'])==16
    assert all(m.counts['root_predictions']==16 for m in Model.instances)
    assert all(m['before']==m['after'] for m in result['models'])
    assert result['environment_counts']=={'sampled_transitions':576}
    assert result['policy_counts']=={'choose_calls':288}
    assert result['statuses']=={'WON':287,'CUTOFF':1}
    with gzip.open(target/result['control_trace'],'rt') as stream:rows=[json.loads(line) for line in stream]
    physical,_=runner.rosters();expected={r['physical_id'] for r in physical if r['life']==1}
    assert {r['physical_id'] for r in rows}==expected and len(rows)==len(expected)
    assert all(r['checkpoint']!=0 and r['method']!='ALT' for r in rows)
    assert sum(r['result']['utility'] is None for r in rows)==1


def test_all_rosters_and_copied_models_are_frozen_before_any_worker(local_tmp,monkeypatch):
    events=[];capsule=dict(snapshots=[dict(life=l) for l in range(4)],models=[dict(marker='copied')],cost_refs=[])
    class Pool:
        def __init__(self,**kwargs):assert kwargs==dict(max_workers=4)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,function,*args):return SimpleNamespace(result=lambda value=function(*args):value)
    def snapshot(directory):
        assert json.loads((directory/'source_capsule.json').read_text())==capsule
        events.append('source_frozen')
    def life(source,models,directory):
        assert events[0]=='source_frozen' and models==capsule['models']
        frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status']=='frozen'
        assert len(frozen['physical_roster'])==1152 and len(frozen['logical_roster'])==2560
        assert frozen['settings']['new_training_transitions']==frozen['settings']['new_training_updates']==0
        events.append(source['life']);return dict(life=source['life'])
    monkeypatch.setattr(runner,'read',lambda *a:{})
    monkeypatch.setattr(runner,'extract_source',lambda *a:capsule)
    monkeypatch.setattr(runner,'snapshot_code',snapshot)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(runner,'as_completed',lambda futures:reversed(futures))
    monkeypatch.setattr(runner,'lifecycle',life)
    output=local_tmp/'experiment';runner.run(output)
    result=json.loads((output/'run.json').read_text())
    assert result['status']=='complete' and [r['life'] for r in result['lifecycles']]==list(range(4))
    assert events==['source_frozen',0,1,2,3]
