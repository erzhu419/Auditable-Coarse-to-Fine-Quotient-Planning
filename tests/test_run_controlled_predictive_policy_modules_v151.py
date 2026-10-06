"""Synthetic V151 experiment wiring; no native planning or physical samples."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_policy_modules_v151 as runner

TEMP = Path(__file__).resolve().parents[1]/'reports/v151_runtime_tmp'
MOCK_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP/'runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, environment_samples=0,
        model_samples=0, real_training_updates=0, synthetic_work=dict(MOCK_WORK),
        scope='Stubbed games, branch triplets and learners; no native execution.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    with TemporaryDirectory(prefix='runner_', dir=TEMP) as folder:
        yield Path(folder)


def fake_game(seed=0, steps=4):
    return dict(seed=seed, steps=[dict(board=[1+i]+[0]*15) for i in range(steps)])


def fake_result(steps, status='WON', components=None):
    return dict(steps=steps, status=status, components=components or [1., 0., 1.],
        utility=None if status=='CUTOFF' else 1.,
        environment_counts=dict(sampled_transitions=steps), policy_counts={})


def fake_play(bank, query, method, duration, model, seed, max_steps=2000):
    assert method=='H2' and duration==0 and model is None and max_steps>=4
    MOCK_WORK['source_game_stubs'] += 1
    return dict(seed=seed, query=query, result=fake_result(4)), fake_game(seed)


def test_root_selection_and_phase_seeds_are_fixed_before_outcomes():
    game=fake_game(17, 20)
    roots=runner.select_roots(game, 2, 'risk8', 3, 1)
    assert [r['step'] for r in roots]==[2, 7, 12, 17]
    assert [r['board'] for r in roots]==[game['steps'][i]['board'] for i in (2, 7, 12, 17)]
    assert [r['root_id'] for r in roots]==[f'2:risk8:3:1:{s}' for s in range(4)]
    changed=deepcopy(game); changed['status']='LOST'; changed['return_score']=-999
    assert runner.select_roots(changed, 2, 'risk8', 3, 1)==roots
    sources=[runner.source_seed(l,q,b,r) for l in runner.LIVES for q in runner.QUERIES
        for b in range(1,5) for r in range(2)]
    branches=[runner.branch_seed(l,q,b,r,s,k) for l in runner.LIVES for q in runner.QUERIES
        for b in range(1,5) for r in range(2) for s in range(4) for k in range(8)]
    evaluations=[runner.evaluation_seed(l,c,r) for l in runner.LIVES for c in range(5) for r in range(4)]
    assert (len(sources),len(branches),len(evaluations))==(64,2048,80)
    combined=sources+branches+evaluations
    assert len(set(combined))==len(combined)
    assert all(runner.BASE<=s<runner.BASE+100000000 for s in combined)


def test_h2_zero_duration_uses_own_query_without_learned_gate(monkeypatch):
    calls=[]
    class Teacher:
        def __init__(self, query): self.query=query;self.counts=Counter()
        def choose(self, board, query):
            assert query==runner.QUERIES[self.query]
            self.counts['choose_calls']+=1;calls.append(self.query)
            return dict(action='LEFT',afterstate=list(board),score=0,value=0.,tail_value=0.,status='ACTIVE')
    bank={q:Teacher(q) for q in runner.QUERIES}
    def episode(seed, act, p_four, limit):
        assert act(tuple([1]+[0]*15),0)=='LEFT'
        MOCK_WORK['episode_callback_stubs']+=1
        return fake_game(seed)
    monkeypatch.setattr(runner.old.old,'run_episode',episode)
    monkeypatch.setattr(runner.old.old,'game_result',lambda game,q,counts,seconds:fake_result(4))
    monkeypatch.setattr(runner.old.old,'compact_trace',lambda game:{})
    row,_=runner.play_game(bank,'risk8','H2',0,None,123)
    assert calls==['risk8'] and row['duration']==0
    assert row['choices'][0]['module_decision']['predicted_components'] is None


@pytest.mark.parametrize('budget,suffixes,branch_steps',[(25,8,3),(1000,2,1)])
def test_shared_budget_keeps_partial_costs_and_suffix_outer_order(local_tmp,monkeypatch,budget,suffixes,branch_steps):
    monkeypatch.setattr(runner,'BUDGET',budget);monkeypatch.setattr(runner,'SUFFIXES',suffixes)
    monkeypatch.setattr(runner,'play_game',fake_play);calls=[]
    def branch(board,bank,query,duration,seed,max_steps,p_four):
        steps=min(branch_steps,max_steps);status='WON' if steps==branch_steps else 'CUTOFF'
        calls.append((duration,seed,max_steps));MOCK_WORK['branch_stubs']+=1
        return dict(seed=seed,duration=duration,result=fake_result(steps,status,[float(duration),0.,1.]))
    monkeypatch.setattr(runner,'run_module_branch',branch)
    result,examples=runner.acquire_batch({},0,'risk1',1,local_tmp,local_tmp)
    with gzip.open(local_tmp/result['triplet_trace'],'rt') as stream: rows=[json.loads(line) for line in stream]
    assert result['actual_training_transitions']==sum(steps for steps in [8]+[
        b['result']['steps'] for r in rows for b in r['branches'].values()])
    assert result['matched_budget_views']=={'1':result['actual_training_transitions'],'8':result['actual_training_transitions']}
    assert result['actual_training_transitions']<=budget
    for row in rows:
        assert all(b['seed']==row['seed'] for b in row['branches'].values())
    root_ids=[r['root_id'] for r in result['roots']]
    if budget==25:
        assert result['actual_training_transitions']==25 and result['attempted_triplets']==2
        assert result['complete_triplets']==1 and result['physical_branches']==6
        assert [r['root_id'] for r in rows]==root_ids[:2]
        assert rows[-1]['branches']['8']['result']['status']=='CUTOFF' and not rows[-1]['complete']
        assert [e['root_id'] for e in examples]==root_ids[:1]
        assert examples[0]['triplet_ids']==[rows[0]['triplet_id']]
        assert examples[0]['targets']=={'1':[1.,0.,0.],'8':[8.,0.,0.]}
    else:
        assert [r['root_id'] for r in rows]==root_ids*2
        assert [r['suffix'] for r in rows]==[0]*8+[1]*8
        assert result['complete_triplets']==16 and all(e['samples']==2 for e in examples)


class Model:
    instances=[]
    def __init__(self):
        self.frozen=False;self.updates=0;self.calls=[];self.counts=Counter();self.setup_counts=Counter(stub=1)
        self.instances.append(self)
    def state(self): return dict(updates=self.updates,frozen=self.frozen,weights=[[0,self.updates]])
    def update(self,board,target,alpha):
        assert not self.frozen
        self.calls.append((deepcopy(board),deepcopy(target),alpha));self.updates+=1
        self.counts['update_calls']+=1;MOCK_WORK['update_stubs']+=1
    def freeze(self): self.frozen=True
    def to_payload(self):
        assert self.frozen
        self.counts['checkpoint_saves']+=1
        return self.state()
    def predict(self,board):
        assert self.frozen
        self.counts['root_predictions']+=1;MOCK_WORK['prediction_stubs']+=1
        return [1.,0.,0.]


def example(root_id,board_value=1):
    return dict(root_id=root_id,board=[board_value]+[0]*15,triplet_ids=[root_id+':0'],samples=1,
        targets={'1':[1.,0.,0.],'8':[8.,0.,0.]})


def test_root_means_exclude_censoring_and_warm_fit_weights_roots_equally(local_tmp):
    roots=[dict(root_id='a',board=[1]+[0]*15),dict(root_id='b',board=[2]+[0]*15)]
    def triplet(key,suffix,value,complete=True):
        return dict(root_id=key,triplet_id=f'{key}:{suffix}',complete=complete,branches={
            str(d):dict(result=dict(components=[float(value*d),float(d==0),float(d!=0)])) for d in (0,1,8)})
    rows=[triplet('a',0,2),triplet('a',1,4),triplet('b',0,10),triplet('b',1,999,False)]
    means=runner.root_means(roots,rows)
    assert [e['samples'] for e in means]==[2,1]
    assert means[0]['targets']=={'1':[3.,-1.,1.],'8':[24.,-1.,1.]}
    assert means[1]['targets']=={'1':[10.,-1.,1.],'8':[80.,-1.,1.]}
    models={d:Model() for d in (1,8)};first=local_tmp/'first';first.mkdir()
    result=runner.fit_models(models,means,first,local_tmp)
    states={d:m.state() for d,m in models.items()}
    for d,m in models.items():
        assert m.calls==[(e['board'],e['targets'][str(d)],.1) for e in means]*32
        assert result[str(d)]['fit_counts']['update_calls']==64
        assert json.loads((local_tmp/result[str(d)]['model_ref']).read_text())==states[d]
    second=local_tmp/'second';second.mkdir();accumulated=means+[example('c',3)]
    next_result=runner.fit_models(models,accumulated,second,local_tmp)
    for d,m in models.items():
        assert next_result[str(d)]['before']==states[d] and m.updates==160
        assert m.calls[64:]==[(e['board'],e['targets'][str(d)],.1) for e in accumulated]*32
        assert next_result[str(d)]['training_triplet_ids']==['a:0','a:1','b:0','c:0']
        assert json.loads((local_tmp/result[str(d)]['model_ref']).read_text())==states[d]


def test_checkpoint_predictions_are_readonly_and_common_eval_seeds(local_tmp,monkeypatch):
    models={q:{d:Model() for d in (1,8)} for q in runner.QUERIES}
    for group in models.values():
        for model in group.values(): model.freeze()
    accumulated={q:[example(q)] for q in runner.QUERIES};before=deepcopy(accumulated);calls=[]
    def play(bank,q,method,duration,model,seed,max_steps=2000):
        calls.append((q,method,duration,seed))
        if model is not None:
            assert model.frozen and not model.calls
            model.predict([9]+[0]*15)
        return dict(seed=seed,result=fake_result(4)),fake_game(seed)
    monkeypatch.setattr(runner,'play_game',play)
    result=runner.evaluate_checkpoint({},models,accumulated,2,3,local_tmp,local_tmp)
    assert accumulated==before and len(calls)==32
    for q,data in result['queries'].items():
        assert data['models_before']==data['models_after']
        assert all(not model.calls for model in models[q].values())
        for method in runner.METHODS:
            assert [x[3] for x in calls if x[:2]==(q,method)]==[
                runner.evaluation_seed(2,3,r) for r in range(4)]
    with gzip.open(local_tmp/result['diagnostics_trace'],'rt') as stream: diagnostics=[json.loads(line) for line in stream]
    assert len(diagnostics)==32 and sum(r['seen_in_training'] for r in diagnostics)==8


def test_lifecycle_saves_frozen_models_before_eval_and_carries_only_training(local_tmp,monkeypatch):
    monkeypatch.setattr(runner,'BATCHES',2);monkeypatch.setattr(runner,'RootConsequences',Model)
    monkeypatch.setattr(runner,'load_teacher',lambda *args:({}, {},SimpleNamespace(counts=Counter()),{}))
    monkeypatch.setattr(runner,'leaf_state',lambda *args:{})
    events=[]
    def acquire(bank,life,query,batch,folder,directory):
        events.append(('acquire',query,batch))
        return dict(actual_training_transitions=11),[example(f'{query}:{batch}',batch)]
    def evaluate(bank,models,accumulated,life,checkpoint,folder,directory):
        frozen=json.loads((folder/'frozen_models.json').read_text())
        assert 'evaluation' not in frozen and frozen['checkpoint']==checkpoint
        for q in runner.QUERIES:
            assert [e['root_id'] for e in accumulated[q]]==[f'{q}:{b}' for b in range(1,checkpoint+1)]
            for d in (1,8):
                metadata=frozen['models'][q][str(d)]
                assert json.loads((directory/metadata['model_ref']).read_text())==models[q][d].state()
                assert models[q][d].frozen and models[q][d].updates==32*sum(range(1,checkpoint+1))
                models[q][d].predict([1]+[0]*15)
        events.append(('evaluate',checkpoint));return dict(external_evaluation_label=999.)
    monkeypatch.setattr(runner,'acquire_batch',acquire);monkeypatch.setattr(runner,'evaluate_checkpoint',evaluate)
    result=runner.lifecycle(dict(life=1),local_tmp)
    assert events==[('evaluate',0),('acquire','risk1',1),('acquire','risk8',1),('evaluate',1),
        ('acquire','risk1',2),('acquire','risk8',2),('evaluate',2)]
    assert [r['checkpoint'] for r in result['checkpoints']]==[0,1,2]
