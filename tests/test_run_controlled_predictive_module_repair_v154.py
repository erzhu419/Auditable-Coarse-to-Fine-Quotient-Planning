"""Synthetic paired-target repair wiring; no real source or native execution."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_module_repair_v154 as runner

TEMP=Path(__file__).resolve().parents[1]/'reports/v154_runtime_tmp'
MOCK_WORK=Counter()


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'runner_checks.json'
    payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before,environment_samples=0,native_calls=0,
        real_training_updates=0,synthetic_work=dict(MOCK_WORK),
        scope='Synthetic source quartets, frozen models and game workers.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_',dir=TEMP) as folder:
        yield Path(folder)


def test_paired_new_game_roster_reuses_only_other_query_baseline_for_alt():
    physical,logical=runner.rosters()
    assert len(physical)==512 and len(logical)==640
    sources={row['physical_id']:row for row in physical}
    assert len(sources)==512
    assert Counter(r['arm'] for r in physical)=={'H2':128,'OLD':128,'REPAIR_H2':128,'REPAIR_GATE':128}
    assert Counter(r['arm'] for r in logical)=={'H2':128,'ALT':128,'OLD':128,'REPAIR_H2':128,'REPAIR_GATE':128}
    seeds={runner.evaluation_seed(l,r) for l in range(4) for r in range(16)}
    assert len(seeds)==64 and min(seeds)==15490000000
    assert {r['seed'] for r in physical}=={r['seed'] for r in logical}==seeds
    for row in logical:
        source=sources[row['physical_id']]
        assert all(row[k]==source[k] for k in ('life','replica','seed'))
        if row['arm']=='ALT':assert source['arm']=='H2' and source['query']!=row['query']
        else:assert source['arm']==row['arm'] and source['query']==row['query']
        assert source['duration']==(0 if source['arm']=='H2' else 8)
        assert source['method']==('H2' if source['arm']=='H2' else 'LEARN8')
    assert Counter(Counter(r['physical_id'] for r in logical).values())=={2:128,1:384}


def synthetic_pool(folder):
    models=[];roots=[];traces={}
    for life in range(4):
        traces[f'trace:{life}']=[]
        for qi,query in enumerate(runner.QUERIES):
            ref=f'frozen/{life}/{query}/OLD.json';path=folder/ref;path.parent.mkdir(parents=True,exist_ok=True)
            payload=dict(radix=11,updates=23+life,frozen=True,weights=[[0,1.,2.,3.]])
            path.write_text(json.dumps(payload))
            models.append(dict(life=life,query=query,arm='OLD',model_ref=ref,frozen_state=deepcopy(payload)))
            for mi,method in enumerate(('H2','LEARN8')):
                for slot in range(4):
                    root=dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,source_method=method,
                        slot=slot,board=[life+1,qi+1,mi+1,slot+1]+[0]*12,
                        prediction=dict(accept=slot%2==0),old_training_target=[999.,999.,999.])
                    roots.append(root)
                    for suffix in range(16):
                        values={'H_H2':[100.+suffix,1.,0.], 'M_H2':[100.+slot+2*suffix,0.,1.],
                            'H_GATE':[200.+suffix,0.,1.], 'M_GATE':[200.+2*slot+3*suffix,1.,0.]}
                        for mode in ('H_H2','M_H2','H_GATE','M_GATE'):
                            traces[f'trace:{life}'].append(dict(root_id=root['root_id'],suffix=suffix,mode=mode,
                                result=dict(components=values[mode],status='LOST' if values[mode][1] else 'WON',steps=suffix+1)))
    return dict(models=models,roots=roots,snapshots=[dict(life=l) for l in range(4)],cost_refs=[],
        source_traces=[dict(life=l,path=f'trace:{l}') for l in range(4)]),traces


def install_traces(monkeypatch,traces):
    def rows(path):
        for row in reversed(traces[str(path)]):
            MOCK_WORK['retained_row_stubs']+=1
            yield deepcopy(row)
    monkeypatch.setattr(runner,'read_rows',rows)


def test_both_targets_use_all_same_roots_and_suffix_component_means(local_tmp,monkeypatch):
    capsule,traces=synthetic_pool(local_tmp);before=deepcopy(capsule);install_traces(monkeypatch,traces)
    examples,work=runner.prepare_examples(capsule)
    assert capsule==before and len(examples)==64
    assert [e['root_id'] for e in examples]==[r['root_id'] for r in capsule['roots']]
    assert sum(r['prediction']['accept'] for r in capsule['roots'])==32
    assert Counter(e['source_method'] for e in examples)=={'H2':32,'LEARN8':32}
    for e in examples:
        slot=e['slot'];assert e['suffixes']==16
        assert e['targets']=={'REPAIR_H2':[slot+7.5,-1.,1.],'REPAIR_GATE':[2*slot+15.,1.,-1.]}
        assert 'old_training_target' not in e
    assert work==dict(retained_rows_read=4096,retained_environment_transitions=34816,
        new_training_environment_samples=0,matched_budget_views={'REPAIR_H2':34816,'REPAIR_GATE':34816})


class Model:
    instances=[]
    @classmethod
    def from_payload(cls,payload):
        model=cls();model.radix=payload['radix'];model.frozen=payload['frozen'];model.updates=payload['updates']
        model.weights=deepcopy(payload['weights']);model.calls=[];model.counts=Counter()
        model.setup_counts=Counter(stub_load=1);model.setup_seconds=0.
        cls.instances.append(model);MOCK_WORK['model_load_stubs']+=1;return model
    def state(self):return dict(radix=self.radix,frozen=self.frozen,updates=self.updates,weights=deepcopy(self.weights))
    def update(self,board,target,alpha):
        assert not self.frozen
        self.calls.append((deepcopy(board),deepcopy(target),alpha));self.updates+=1
        self.weights[0][1]+=target[0];self.counts['update_calls']+=1;MOCK_WORK['update_stubs']+=1
    def freeze(self):self.frozen=True
    def to_payload(self):
        assert self.frozen
        self.counts['checkpoint_saves']+=1
        return self.state()
    def predict(self,board):
        assert self.frozen and not self.calls
        self.counts['root_predictions']+=1;MOCK_WORK['prediction_stubs']+=1
        return [1.,0.,0.]


def fitted_fixture(local_tmp,monkeypatch):
    capsule,traces=synthetic_pool(local_tmp);install_traces(monkeypatch,traces)
    examples,_=runner.prepare_examples(capsule);Model.instances=[];monkeypatch.setattr(runner,'RootConsequences',Model)
    metadata=runner.fit_models(capsule,examples,local_tmp)
    return capsule,examples,metadata


def test_repairs_share_old_initialization_but_never_share_updates_or_old_labels(local_tmp,monkeypatch):
    capsule,examples,metadata=fitted_fixture(local_tmp,monkeypatch)
    assert len(metadata)==len(Model.instances)==16
    assert sum(m['new_updates'] for m in metadata)==sum(len(m.calls) for m in Model.instances)==4096
    old_index={(m['life'],m['query']):m for m in capsule['models']}
    for data,model in zip(metadata,Model.instances):
        old=old_index[data['life'],data['query']]
        assert data['before']==old['frozen_state']==json.loads((local_tmp/old['model_ref']).read_text())
        selected=[e for e in examples if (e['life'],e['query'])==(data['life'],data['query'])]
        assert data['root_ids']==[e['root_id'] for e in selected]
        assert [e['source_method'] for e in selected]==['H2']*4+['LEARN8']*4
        assert model.calls==[(e['board'],e['targets'][data['arm']],.1) for e in selected]*32
        assert data['new_updates']==256 and data['fit_counts']=={'update_calls':256}
        assert data['total_counts']=={'update_calls':256,'checkpoint_saves':1}
        assert json.loads((local_tmp/data['model_ref']).read_text())==data['frozen_state']==model.state()
        assert data['frozen_state']['frozen']
    for i in range(0,16,2):
        assert metadata[i]['before']==metadata[i+1]['before']
        assert metadata[i]['frozen_state']!=metadata[i+1]['frozen_state']


def test_evaluation_keeps_all_physical_game_costs_and_never_refits(local_tmp,monkeypatch):
    capsule,_,metadata=fitted_fixture(local_tmp,monkeypatch)
    monkeypatch.setattr(runner,'load_teacher',lambda *a:({}, {},SimpleNamespace(counts=Counter()),{}))
    monkeypatch.setattr(runner,'leaf_state',lambda *a:{})
    calls=[]
    def play(bank,query,method,duration,model,seed,max_steps):
        assert method in ('H2','LEARN8') and max_steps==2000
        if model is None:assert method=='H2' and duration==0
        else:assert duration==8;model.predict([1]+[0]*15)
        calls.append((query,method,seed));MOCK_WORK['game_stubs']+=1;bank[query].counts['choose_calls']+=1
        cutoff=query=='risk8' and method=='H2' and seed==runner.evaluation_seed(0,15)
        return dict(query=query,method=method,seed=seed,duration=duration,result=dict(
            status='CUTOFF' if cutoff else 'WON',utility=None if cutoff else 1.,steps=2,
            environment_counts=dict(sampled_transitions=2),policy_counts=dict(stub_policy_calls=1))),{}
    monkeypatch.setattr(runner,'play_game',play)
    result=runner.lifecycle(dict(life=0),capsule['models']+metadata,local_tmp)
    assert len(calls)==result['physical_games']==128
    assert Counter(c[1] for c in calls)=={'H2':32,'LEARN8':96}
    assert result['environment_counts']=={'sampled_transitions':256}
    assert result['policy_counts']=={'stub_policy_calls':128} and result['statuses']=={'WON':127,'CUTOFF':1}
    assert len(result['models'])==6 and all(m['before']==m['after'] for m in result['models'])
    assert all(m['counts']=={'root_predictions':16} for m in result['models'])
    with gzip.open(local_tmp/result['control_trace'],'rt') as stream:rows=[json.loads(line) for line in stream]
    physical,_=runner.rosters()
    assert {r['physical_id'] for r in rows}=={r['physical_id'] for r in physical if r['life']==0}
    assert len(rows)==128 and sum(r['result']['utility'] is None for r in rows)==1


def test_protocol_precedes_fitting_and_all_twenty_four_models_precede_evaluation(local_tmp,monkeypatch):
    events=[];capsule,traces=synthetic_pool(local_tmp/'fixture');fit_records=[]
    class Pool:
        def __init__(self,**kwargs):assert kwargs==dict(max_workers=4)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,function,*args):return SimpleNamespace(result=lambda value=function(*args):value)
    def extract(*args):
        directory=args[-1]
        for model in capsule['models']:
            path=directory/model['model_ref'];path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(model['frozen_state']))
        return capsule
    def prepare(source):
        directory=local_tmp/'experiment';frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status']=='frozen' and frozen['training_root_ids']==[r['root_id'] for r in capsule['roots']]
        assert len(frozen['physical_roster'])==512 and len(frozen['logical_roster'])==640
        events.append('prepare');return [dict(marker='all64')],dict(retained_rows_read=4096)
    def fit(source,examples,directory):
        assert events==['snapshot','prepare'] and examples==[dict(marker='all64')]
        for old in source['models']:
            for arm in ('REPAIR_H2','REPAIR_GATE'):
                path=Path(old['model_ref']).with_name(arm+'.json')
                state=dict(old['frozen_state'],updates=old['frozen_state']['updates']+256)
                (directory/path).write_text(json.dumps(state))
                fit_records.append(dict(life=old['life'],query=old['query'],arm=arm,model_ref=str(path),frozen_state=state))
        events.append('fit');return fit_records
    def lifecycle(source,all_models,directory):
        assert events[:3]==['snapshot','prepare','fit'] and len(all_models)==24
        frozen=json.loads((directory/'frozen_training.json').read_text())
        assert frozen['models']==fit_records
        for model in all_models:
            assert json.loads((directory/model['model_ref']).read_text())['frozen']
        events.append(source['life']);return dict(life=source['life'])
    monkeypatch.setattr(runner,'read',lambda *a:{})
    monkeypatch.setattr(runner,'extract_source',extract)
    monkeypatch.setattr(runner,'snapshot_code',lambda *a:events.append('snapshot'))
    monkeypatch.setattr(runner,'prepare_examples',prepare)
    monkeypatch.setattr(runner,'fit_models',fit)
    monkeypatch.setattr(runner,'lifecycle',lifecycle)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(runner,'as_completed',lambda futures:reversed(futures))
    output=local_tmp/'experiment';runner.run(output)
    result=json.loads((output/'run.json').read_text())
    assert result['status']=='complete' and [r['life'] for r in result['lifecycles']]==list(range(4))
    assert events==['snapshot','prepare','fit',0,1,2,3]
