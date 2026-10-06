"""Synthetic boundary-root diagnosis wiring; no native or physical sampling."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_module_diagnosis_v153 as runner

TEMP=Path(__file__).resolve().parents[1]/'reports/v153_runtime_tmp'
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
        training_updates=0,synthetic_work=dict(MOCK_WORK),
        scope='Synthetic retained games, source models and branch workers.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_',dir=TEMP) as folder:
        yield Path(folder)


def synthetic_game(life=0,query='risk1',method='LEARN8',replica=0,boundaries=None):
    boundaries=(list(range(37)) if method=='H2' else [0,1,9,10,18,19,27,28,36]) if boundaries is None else boundaries
    n=max(boundaries)+1
    return dict(life=life,query=query,method=method,checkpoint=4 if method=='LEARN8' else -1,
        physical_id=f'{life}:{query}:{4 if method=="LEARN8" else -1}:{method}:{replica}',
        seed=15290000000+life*1000000+replica,replica=replica,initial_board=[2]+[0]*15,
        choices=[dict(action='LEFT',afterstate=[i%10+1]*15+[0],module_decision=dict(
            boundary=i in boundaries,remaining_before=0 if i in boundaries else 7)) for i in range(n)],
        spawned_cells=[15]*n,spawned_ranks=[1+i%2 for i in range(n)])


def test_roots_are_predecision_module_boundaries_with_recorded_spawn_reconstruction():
    row=synthetic_game();before=deepcopy(row)
    roots=[runner.select_root(row,slot,'retained/control.jsonl.gz') for slot in range(4)]
    assert [r['selected_boundary_index'] for r in roots]==[1,3,5,7]
    assert [r['source_step'] for r in roots]==[1,10,19,28]
    for slot,root in enumerate(roots):
        step=root['source_step'];expected=list(row['choices'][step-1]['afterstate'])
        expected[row['spawned_cells'][step-1]]=row['spawned_ranks'][step-1]
        assert root['board']==expected and root['source_boundary_count']==9
        assert root['source_ref']=='retained/control.jsonl.gz'
        assert root['source_physical_id']==row['physical_id'] and root['source_seed']==row['seed']
        assert root['source_method']=='LEARN8' and root['query']=='risk1'
        assert row['choices'][step]['module_decision']['boundary']
    assert row==before
    initial=synthetic_game(boundaries=[0]);root=runner.select_root(initial,0,'initial')
    assert root['source_step']==0 and root['board']==initial['initial_board']


def test_four_modes_share_suffix_seeds_but_roots_queries_and_sources_do_not():
    roots=[]
    for life in range(4):
        for query in runner.QUERIES:
            for method in ('H2','LEARN8'):
                for slot,replica in enumerate((0,4,8,12)):
                    roots.append(runner.select_root(synthetic_game(life,query,method,replica),slot,'retained'))
    roster=runner.branch_roster(roots)
    assert len(roots)==64 and len(roster)==4096
    assert len({r['branch_id'] for r in roster})==4096
    grouped={}
    for row in roster:grouped.setdefault((row['root_id'],row['suffix']),[]).append(row)
    assert len(grouped)==1024 and len({r['seed'] for r in roster})==1024
    root_index={r['root_id']:r for r in roots}
    for (root_id,suffix),rows in grouped.items():
        root=root_index[root_id]
        assert {r['mode'] for r in rows}=={'H_H2','M_H2','H_GATE','M_GATE'}
        expected=runner.branch_seed(root['life'],root['query'],root['source_method'],root['slot'],suffix)
        assert {r['seed'] for r in rows}=={expected}
        assert 15300000000<=expected<15400000000


def synthetic_sources(folder):
    source=folder/'source';source.mkdir();models=[]
    for life in range(4):
        for query in runner.QUERIES:
            for checkpoint in range(5):
                for duration in (1,8):
                    payload=dict(schema='acfqp.root_consequences.v151',radix=11,frozen=True,
                        updates=checkpoint*10,weights=[] if not checkpoint else [[duration,float(checkpoint),0.,-1.]])
                    ref=f'{life}/{query}/{checkpoint}/module_{duration}.json';path=source/ref
                    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload))
                    models.append(dict(life=life,query=query,checkpoint=checkpoint,duration=duration,
                        model_ref=ref,frozen_state=runner.prior.model_state(payload)))
    capsule=dict(snapshots=[dict(life=l) for l in range(4)],models=models,cost_refs=[])
    run=dict(status='complete',lifecycles=[dict(life=l,control_trace=f'life_{l}/control.jsonl.gz') for l in range(4)])
    return source,capsule,run,dict(complete=True,primary_complete=True)


class Model:
    instances=[]
    @classmethod
    def from_payload(cls,payload):
        model=cls();model.payload=deepcopy(payload);model.frozen=payload['frozen']
        model.counts=Counter();model.setup_counts=Counter(stub_load=1);model.setup_seconds=0.
        cls.instances.append(model);MOCK_WORK['model_load_stubs']+=1;return model
    def state(self):return runner.prior.model_state(self.payload)
    def update(self,*args,**kwargs):pytest.fail('diagnosis must never train a model')
    def predict(self,board):
        assert self.frozen
        self.counts['root_predictions']+=1;MOCK_WORK['prediction_stubs']+=1
        return [2.,.5,.1]


def prepared_fixture(local_tmp,monkeypatch):
    source,capsule,run,analysis=synthetic_sources(local_tmp);monkeypatch.setattr(runner,'SOURCE',source)
    target=local_tmp/'frozen';target.mkdir();extracted=runner.extract_source(capsule,run,analysis,target)
    Model.instances=[];monkeypatch.setattr(runner,'RootConsequences',Model)
    trace_rows={}
    for trace in extracted['source_traces']:
        life=trace['life'];wanted=[synthetic_game(life,q,m,r) for q in runner.QUERIES
            for m in ('H2','LEARN8') for r in (0,4,8,12)]
        wrong_checkpoint=synthetic_game(life);wrong_checkpoint['checkpoint']=3
        unrelated=synthetic_game(life);unrelated['method']='LEARN1'
        trace_rows[trace['path']]=[wrong_checkpoint,unrelated]+list(reversed(wanted))
    def read_rows(path):
        for row in trace_rows[str(path)]:
            MOCK_WORK['source_rows_yielded']+=1
            yield deepcopy(row)
        pytest.fail('root preparation read beyond its complete predeclared source roster')
    monkeypatch.setattr(runner.prior.prior,'read_rows',read_rows)
    roots,preparation=runner.prepare_roots(extracted,target)
    return extracted,target,roots,preparation


def test_source_uses_only_final_eight_step_models_and_freezes_all_root_predictions(local_tmp,monkeypatch):
    capsule,target,roots,preparation=prepared_fixture(local_tmp,monkeypatch)
    assert len(capsule['models'])==8 and all(e['checkpoint']==4 and e['duration']==8 for e in capsule['models'])
    for entry in capsule['models']:
        assert Path(entry['source_model_ref']).read_bytes()==(target/entry['model_ref']).read_bytes()
    assert len(roots)==64 and preparation['source_games_selected']==64 and preparation['source_rows_read']==72
    assert len(Model.instances)==8 and all(m.counts['root_predictions']==8 for m in Model.instances)
    assert all(m['before']==m['after'] for m in preparation['prediction_models'])
    expected=[(l,q,m,s,r) for l in range(4) for q in runner.QUERIES for m in ('H2','LEARN8')
        for s,r in enumerate((0,4,8,12))]
    assert [(r['life'],r['query'],r['source_method'],r['slot'],r['replica']) for r in roots]==expected
    for root in roots:
        prediction=root['prediction'];assert prediction['components']==[2.,.5,.1]
        assert prediction['advantage']==pytest.approx(1.6 if root['query']=='risk1' else -1.2)
        assert prediction['accept']==(root['query']=='risk1')
        assert root['prediction_counts']=={'root_predictions':1}


def test_lifecycle_preserves_every_branch_cost_and_cutoff_without_updating_models(local_tmp,monkeypatch):
    capsule,target,roots,_=prepared_fixture(local_tmp,monkeypatch)
    monkeypatch.setattr(runner,'load_teacher',lambda *a:({}, {},SimpleNamespace(counts=Counter()),{}))
    monkeypatch.setattr(runner,'leaf_state',lambda *a:{})
    calls=[]
    cutoff_seed=runner.branch_seed(0,'risk8','LEARN8',3,15)
    def branch(board,bank,query,mode,model,seed,max_steps,p_four):
        assert max_steps==2000 and p_four==.1 and model.frozen
        calls.append((query,mode,seed));MOCK_WORK['branch_stubs']+=1
        if mode.endswith('_GATE'):model.predict(board)
        bank[query].counts['choose_calls']+=1
        cutoff=mode=='M_GATE' and seed==cutoff_seed
        return dict(root_board=list(board),query=query,mode=mode,seed=seed,result=dict(
            status='CUTOFF' if cutoff else 'WON',steps=2,utility=None if cutoff else 1.,
            environment_counts=dict(sampled_transitions=2),policy_counts=dict(stub_policy_calls=1)))
    monkeypatch.setattr(runner,'run_branch',branch)
    result=runner.lifecycle(dict(life=0),capsule['models'],roots,target)
    assert len(calls)==result['physical_branches']==1024
    assert Counter(c[1] for c in calls)=={m:256 for m in runner.MODES}
    assert result['environment_counts']=={'sampled_transitions':2048}
    assert result['policy_counts']=={'stub_policy_calls':1024}
    assert result['statuses']=={'WON':1023,'CUTOFF':1}
    assert all(m['before']==m['after'] and m['counts']=={'root_predictions':256} for m in result['models'])
    with gzip.open(target/result['branch_trace'],'rt') as stream:rows=[json.loads(line) for line in stream]
    expected=runner.branch_roster([r for r in roots if r['life']==0])
    assert [r['branch_id'] for r in rows]==[r['branch_id'] for r in expected]
    assert sum(r['result']['utility'] is None for r in rows)==1
    assert [(r['root_id'],r['mode'],r['seed']) for r in rows]==[
        (r['root_id'],r['mode'],r['seed']) for r in expected]


def test_full_root_predictions_and_branch_roster_are_frozen_before_any_dispatch(local_tmp,monkeypatch):
    events=[];capsule=dict(snapshots=[dict(life=l) for l in range(4)],models=[dict(marker='copied')],cost_refs=[])
    roots=[runner.select_root(synthetic_game(l,q,m,r),s,'retained') for l in range(4)
        for q in runner.QUERIES for m in ('H2','LEARN8') for s,r in enumerate((0,4,8,12))]
    for root in roots:root['prediction']=dict(components=[1.,0.,0.],advantage=1.,accept=True)
    class Pool:
        def __init__(self,**kwargs):assert kwargs==dict(max_workers=4)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,function,*args):return SimpleNamespace(result=lambda value=function(*args):value)
    def snapshot(directory):
        assert json.loads((directory/'source_capsule.json').read_text())==capsule
        events.append('source_snapshot')
    def prepare(*args):
        events.append('predictions_frozen');return roots,dict(source_games_selected=64)
    def lifecycle(source,models,selected,directory):
        assert events[:2]==['source_snapshot','predictions_frozen']
        frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status']=='frozen' and frozen['roots']==roots==selected
        assert len(frozen['branch_roster'])==4096
        assert frozen['settings']['new_training_updates']==0
        events.append(source['life']);return dict(life=source['life'])
    monkeypatch.setattr(runner,'read',lambda *a:{})
    monkeypatch.setattr(runner,'extract_source',lambda *a:capsule)
    monkeypatch.setattr(runner,'snapshot_code',snapshot)
    monkeypatch.setattr(runner,'prepare_roots',prepare)
    monkeypatch.setattr(runner,'lifecycle',lifecycle)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool)
    monkeypatch.setattr(runner,'as_completed',lambda futures:reversed(futures))
    output=local_tmp/'experiment';runner.run(output)
    result=json.loads((output/'run.json').read_text())
    assert result['status']=='complete' and [r['life'] for r in result['lifecycles']]==list(range(4))
    assert events==['source_snapshot','predictions_frozen',0,1,2,3]
