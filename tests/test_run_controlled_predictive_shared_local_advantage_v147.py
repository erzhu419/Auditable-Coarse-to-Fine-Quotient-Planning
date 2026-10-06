"""Frozen experiment wiring checks with synthetic data and mocked learners."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_shared_local_advantage_v147 as runner

TEMP = Path(__file__).resolve().parents[1]/'reports/v147_runtime_tmp'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True); before=request.session.testsfailed
    yield
    path=TEMP/'runner_checks.json'
    payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before, environment_samples=0, model_samples=0,
        reason='Initial wiring checks' if not payload['attempts'] else 'Pre-freeze ZERO control addition; rerun only affected training, streams and settings checks',
        training_updates=0, scope='Synthetic retained examples and mocked models, planners, episodes and phase workers.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_',dir=TEMP) as folder:yield Path(folder)


def source_inputs():
    capsule=dict(prior_examples_ref='/retained/old.json', snapshots=[dict(life=life,
        leaves={q:{'SINGLE':{'model_ref':f'/retained/{life}_{q}.npz'}} for q in runner.QUERIES}) for life in runner.LIVES])
    run=dict(status='complete',lifecycles=[dict(life=life,queries={q:dict(models=dict(UPDATED=dict(
        model_ref=f'train_{life}/{q}_UPDATED.json'))) for q in runner.QUERIES}) for life in runner.LIVES])
    return capsule,run,dict(complete=True,primary_complete=True,costs={'retained':123}),dict(complete=True),dict(complete=True)


def examples(origin,life=0):
    return [dict(root_id=f'{origin}:{life}:{q}:{replica}:{slot}',life=life,query=q,replica=replica,slot=slot,
        split='TRAIN' if replica<4 else 'VALIDATION',candidate_action='RIGHT',baseline_action='LEFT',
        candidate_after=[2,1]+[0]*14,baseline_after=[1,2]+[0]*14,immediate_difference=.25,
        target_tail=[replica+(10. if origin=='NEW' else 0.),float(slot),0.])
        for q in runner.QUERIES for replica in range(8) for slot in range(4)]


class MockModel:
    instances=[]
    def __init__(self):
        self.frozen=False;self.updates=0;self.loaded=False;self.calls=[]
        self.counts=Counter();self.setup_counts=Counter();self.instances.append(self)
    def state(self):return dict(frozen=self.frozen,updates=self.updates,weights=[])
    def update(self,candidate,baseline,target,alpha):
        assert not self.frozen
        self.calls.append((deepcopy(candidate),deepcopy(baseline),deepcopy(target),alpha))
        self.updates+=1;self.counts['update_calls']+=1
    def freeze(self):self.frozen=True
    def predict(self,candidate,baseline):
        assert self.frozen;self.counts['pair_predictions']+=1;return [0.,0.,0.]
    def to_payload(self):return self.state()
    @classmethod
    def from_payload(cls,payload):
        result=cls();result.frozen=payload['frozen'];result.updates=payload['updates'];result.loaded=True;return result


def test_source_keeps_retained_models_and_cost_references_without_copying_payloads():
    inputs=source_inputs();before=deepcopy(inputs);source=runner.extract_source(*inputs)
    assert inputs==before
    assert source['old_examples_ref']=='/retained/old.json'
    assert source['new_examples_ref']==str((runner.SOURCE/'examples.json').resolve())
    assert source['cost_refs']==[
        dict(path=str((runner.SOURCE/'analysis.json').resolve()),fields=['costs','inherited_work']),
        dict(path=str((runner.DIAGNOSIS/'analysis.json').resolve()),fields=['costs']),
        dict(path=str((runner.DIAGNOSIS/'verification.json').resolve()),fields=['work'])]
    for row in source['snapshots']:
        for query in runner.QUERIES:
            assert row['updated_models'][query]==str((runner.SOURCE/f"train_{row['life']}/{query}_UPDATED.json").resolve())
    source['snapshots'][0]['leaves']['changed']=1
    assert inputs==before and 'inherited_costs' not in source


def test_training_reuses_exact_labels_order_and_freezes_before_both_holdouts(local_tmp,monkeypatch):
    source=runner.extract_source(*source_inputs())['snapshots'][0];old,new=examples('OLD'),examples('NEW')
    before=deepcopy((old,new));retained={}
    for query in runner.QUERIES:
        path=local_tmp/f'{query}.json';path.write_text(json.dumps(dict(frozen=True,updates=17,weights=[])))
        source['updated_models'][query]=str(path);retained[path]=path.read_bytes()
    MockModel.instances=[]
    monkeypatch.setattr(runner,'PairedAdvantage',MockModel);monkeypatch.setattr(runner,'SharedLocalAdvantage',MockModel)
    monkeypatch.setattr(runner,'load_teacher',lambda *a:pytest.fail('training initialized a native planner'))
    result=runner.train_lifecycle(source,old,new,local_tmp)
    assert len(MockModel.instances)==6
    for index,query in enumerate(runner.QUERIES):
        zero,prior,shared=MockModel.instances[3*index:3*index+3]
        train={o:[e for e in rows if e['query']==query and e['split']=='TRAIN'] for o,rows in [('OLD',old),('NEW',new)]}
        sequence=train['OLD']+train['NEW'];cell=result['queries'][query]
        assert shared.calls==[(e['candidate_after'],e['baseline_after'],e['target_tail'],.1) for e in sequence]*32
        assert len(shared.calls)==1024 and not prior.calls and prior.loaded and prior.updates==17
        assert shared.frozen and prior.frozen and zero.frozen
        assert not zero.calls and not zero.loaded and zero.updates==0
        assert zero.state()['weights']==[] and cell['models']['ZERO']['training_roots']==[]
        assert cell['train_roots']=={o:[e['root_id'] for e in rows] for o,rows in train.items()}
        assert cell['binding']['life']==0 and cell['binding']['query']==query and cell['binding']['continuation']=='H2'
        for method,model in [('ZERO',zero),('UPDATED',prior),('SHARED',shared)]:
            assert cell['models'][method]['frozen_state']==cell['models'][method]['after_validation']==model.state()
            for origin,rows in [('OLD',old),('NEW',new)]:
                ids=[e['root_id'] for e in rows if e['query']==query and e['split']=='VALIDATION']
                assert [p['root_id'] for p in cell['validation'][origin][method]]==ids
    assert (old,new)==before and all(path.read_bytes()==data for path,data in retained.items())


def test_fresh_streams_are_paired_and_previous_action_and_cutoffs_are_retained(monkeypatch):
    calls=[];seeds=[]
    class Planner:
        def __init__(self):self.counts=Counter()
        def choose(self,board,query,**kwargs):
            calls.append(kwargs);self.counts['mock_choose']+=1
            return dict(action='LEFT',afterstate=[2]+[0]*15,score=4,value=1.,status='ACTIVE',action_values={})
    def episode(seed,act,p_four,max_steps):
        assert (p_four,max_steps)==(.1,2000);seeds.append(seed)
        return dict(seed=seed,actions=[act([1,1]+[0]*14,0),act([2,1]+[0]*14,1)])
    monkeypatch.setattr(runner.old,'run_episode',episode)
    monkeypatch.setattr(runner.old,'compact_trace',lambda game:dict(actions=game['actions']))
    monkeypatch.setattr(runner.old,'game_result',lambda *args:dict(status='CUTOFF',utility=99.))
    for query in runner.QUERIES:
        for method in runner.METHODS:
            row=runner.play(Planner(),2,query,method,7)
            assert row['seed']==14790200007 and row['result']['utility'] is None
            assert [c['previous_action'] for c in row['choices']]==['DOWN','LEFT']
            expected=[None,None] if method=='H2' else [14782070000,14782070001]
            assert [c['simulation_seed'] for c in row['choices']]==expected
    assert seeds==[14790200007]*8
    assert calls[:2]==[{},{}]
    assert calls[2:4]==[dict(simulation_seed=14782070000,previous_action='DOWN'),dict(simulation_seed=14782070001,previous_action='LEFT')]


def test_all_lifecycles_freeze_before_any_control(local_tmp,monkeypatch):
    source=runner.extract_source(*source_inputs());retained=local_tmp/'retained';retained.mkdir()
    for name in ('source_capsule','run','analysis','verification'):(retained/f'{name}.json').write_text('{}')
    for origin,key in [('OLD','old_examples_ref'),('NEW','new_examples_ref')]:
        path=retained/f'{origin}.json';path.write_text(json.dumps(dict(examples=[dict(life=l,origin=origin) for l in runner.LIVES])))
        source[key]=str(path)
    events=[]
    class Pool:
        def __init__(self,**kwargs):assert kwargs==dict(max_workers=4)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,function,*args):return SimpleNamespace(result=lambda value=function(*args):value)
    def train(snapshot,old,new,directory):
        assert old==[dict(life=snapshot['life'],origin='OLD')] and new==[dict(life=snapshot['life'],origin='NEW')]
        assert json.loads((directory/'frozen_inputs.json').read_text())['status']=='frozen'
        events.append(('train',snapshot['life']));return dict(life=snapshot['life'])
    def evaluate(snapshot,trained,directory):
        frozen=json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status']=='trained_frozen' and [r['life'] for r in frozen['lifecycles']]==list(runner.LIVES)
        assert sum(stage=='train' for stage,_ in events)==4 and not frozen['eval_lifecycles']
        events.append(('control',snapshot['life']));return dict(life=snapshot['life'])
    monkeypatch.setattr(runner,'SOURCE',retained);monkeypatch.setattr(runner,'DIAGNOSIS',retained)
    monkeypatch.setattr(runner,'extract_source',lambda *a:deepcopy(source));monkeypatch.setattr(runner,'snapshot_code',lambda directory:None)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool);monkeypatch.setattr(runner,'as_completed',lambda tasks:reversed(tasks))
    monkeypatch.setattr(runner,'train_lifecycle',train);monkeypatch.setattr(runner,'evaluate_lifecycle',evaluate)
    output=local_tmp/'run';runner.run(output)
    assert events==[(stage,l) for stage in ('train','control') for l in runner.LIVES]
    result=json.loads((output/'run.json').read_text())
    assert result['status']=='complete' and result['inherited_cost_refs']==source['cost_refs']


def test_settings_fix_one_representation_and_same_learning_budget():
    settings=runner.settings()
    assert settings['methods']==['H2','ZERO','UPDATED','SHARED'] and settings['physical_games']==256
    assert settings['train_replicas']==[0,1,2,3] and settings['validation_replicas']==[4,5,6,7]
    assert settings['epochs']==32 and settings['alpha']==.1 and settings['new_training_environment_samples']==0
    assert settings['continuation']=='H2' and settings['feature_definition']==runner.FEATURE_DEFINITION
    assert settings['version_base']==14700000000
