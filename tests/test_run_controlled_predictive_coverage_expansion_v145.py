"""Finite schedule, freeze and stream checks without native calls or real games."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace

import pytest

from scripts import run_controlled_predictive_coverage_expansion_v145 as runner


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    failed, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_coverage_expansion_v145.runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-failed, seconds=perf_counter()-started,
        reason='Initial runner checks' if not payload['attempts'] else 'Changed source and phase checks after preserving the original failed V144 analysis work',
        environment_samples=0, environment_random_draws=0, native_model_calls=0,
        model_updates=0, source_refits=0,
        scope='Mocked old/new schedules, held-out games, retained prior, frozen models, fresh paired streams and acquisition phase order.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


@pytest.fixture
def local_tmp():
    root = ROOT/'reports/v145_runtime_tmp'; root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='runner_test_', dir=root) as path:
        yield Path(path)


def source_fixture():
    capsule = dict(snapshots=[dict(life=life,
        leaves={q: {'SINGLE': {'model_ref': f'/retained/leaf_{life}_{q}.npz'}} for q in runner.QUERIES},
        factored_ref=f'/retained/factors_{life}.json',
        paired_consequences_trace=f'/retained/v143_{life}.jsonl.gz') for life in runner.LIVES],
        inherited_costs={'prior': 1})
    run = dict(status='complete',
        lifecycles=[dict(life=life, queries={q: dict(model_ref=f'train_{life}/{q}.json')
            for q in runner.QUERIES}) for life in runner.LIVES],
        eval_lifecycles=[dict(life=life, control_trace=f'eval_{life}/control.jsonl.gz') for life in runner.LIVES])
    analysis = dict(complete=True, primary_complete=True, costs={'v144': 2})
    history=dict(extra_initial_work=dict(analysis_replay_swipes=345,analysis_lms_attempts=128),
        attempts=[dict(status='failed',seconds=.3,stderr_bytes=0),dict(status='complete',seconds=.4,stderr_bytes=0)])
    return capsule, run, analysis, history


def example_fixture(origin):
    """Different targets identify precisely which cohort was used for each update."""
    examples = []
    for life in runner.LIVES:
        for query in runner.QUERIES:
            for replica in range(8):
                for slot in range(4):
                    same = origin == 'OLD' and slot == 0
                    examples.append(dict(root_id=f'{origin}:{life}:{query}:{replica}:{slot}',
                        life=life,query=query,replica=replica,slot=slot,step=32*(slot+1),
                        split='TRAIN' if replica < 4 else 'VALIDATION',
                        candidate_action='LEFT' if same else 'RIGHT', baseline_action='LEFT',
                        candidate_after=([1,2] if same else [2,1])+[0]*14,
                        baseline_after=[1,2]+[0]*14,immediate_difference=0. if same else 4/2048.,
                        target_total=[float(replica)+(0. if origin == 'OLD' else 10.),float(slot),0.],
                        target_tail=[float(replica)+(0. if origin == 'OLD' else 10.),float(slot),0.],
                        suffixes=8))
    return examples


def test_source_references_retain_prior_models_and_costs_without_mutating_capsule():
    capsule, run, analysis, history = source_fixture(); original = deepcopy(capsule); original_history=deepcopy(history)
    source = runner.extract_source(capsule, run, analysis, history)
    assert source['inherited_costs'] == dict(prior=1, v144_experiment={'v144':2},v144_analysis_history=history)
    assert source['prior_examples_ref'] == str((runner.SOURCE/'examples.json').resolve())
    assert source['prior_run_ref'] == str((runner.SOURCE/'run.json').resolve())
    for row, prior in zip(source['snapshots'], capsule['snapshots']):
        assert {key:row[key] for key in prior} == prior
        assert row['advantage_control_trace'] == str((runner.SOURCE/f"eval_{row['life']}/control.jsonl.gz").resolve())
        assert row['prior_models'] == {q:str((runner.SOURCE/f"train_{row['life']}/{q}.json").resolve()) for q in runner.QUERIES}
    source['snapshots'][0]['leaves']['changed'] = 1
    source['inherited_costs']['v144_analysis_history']['extra_initial_work']['analysis_replay_swipes'] += 1
    source['inherited_costs']['v144_analysis_history']['attempts'][0]['seconds'] += 1
    assert capsule == original
    assert history == original_history


@pytest.mark.parametrize('failed', ['status', 'complete', 'primary_complete'])
def test_incomplete_prior_experiment_blocks_new_acquisition(failed):
    capsule, run, analysis, history = source_fixture()
    if failed == 'status': run[failed] = 'evaluation'
    else: analysis[failed] = False
    with pytest.raises(ValueError, match='V144'):
        runner.extract_source(capsule,run,analysis,history)


class MockModel:
    instances = []
    def __init__(self):
        self.frozen=False; self.updates=0; self.loaded=False
        self.counts=Counter(); self.setup_counts=Counter(mock_allocations=1)
        self.calls=[]; self.radix=11; self.instances.append(self)
    def state(self):
        return dict(frozen=self.frozen,updates=self.updates,
            weights=[] if not self.updates else [[1,float(self.updates),0.,0.]])
    def update(self,candidate,baseline,target,alpha):
        assert not self.frozen
        self.calls.append((deepcopy(candidate),deepcopy(baseline),deepcopy(target),alpha))
        self.counts['update_calls'] += 1
        if candidate != baseline:
            self.updates += 1; self.counts['pair_updates'] += 1
    def freeze(self): self.frozen=True
    def predict(self,candidate,baseline):
        assert self.frozen
        self.counts['pair_predictions'] += 1
        return [float(self.updates),0.,0.]
    def to_payload(self):
        self.counts['checkpoint_saves'] += 1
        return dict(schema='mock',**self.state())
    @classmethod
    def from_payload(cls,payload):
        model=cls(); model.frozen=payload['frozen']; model.updates=payload['updates']; model.loaded=True
        model.setup_counts['mock_loads'] += 1
        return model


def test_matched_training_schedule_keeps_prior_and_both_holdouts_out_of_updates(local_tmp,monkeypatch):
    source=runner.extract_source(*source_fixture())['snapshots'][0]
    old=[e for e in example_fixture('OLD') if e['life']==0]
    new=[e for e in example_fixture('NEW') if e['life']==0]
    originals=deepcopy((old,new)); prior_bytes={}
    for query in runner.QUERIES:
        path=local_tmp/f'prior_{query}.json'
        path.write_text(json.dumps(dict(frozen=True,updates=17,weights=[[1,17.,0.,0.]])))
        prior_bytes[path]=path.read_bytes(); source['prior_models'][query]=str(path)
    MockModel.instances=[]
    monkeypatch.setattr(runner,'PairedAdvantage',MockModel)
    monkeypatch.setattr(runner,'load_teacher',lambda *a,**k:pytest.fail('training loaded an environment planner'))
    data=runner.train_lifecycle(source,old,new,local_tmp)
    assert len(MockModel.instances)==6
    for index,query in enumerate(runner.QUERIES):
        models=MockModel.instances[3*index:3*index+3]
        prior=next(m for m in models if m.loaded)
        fitted=[m for m in models if not m.loaded]
        replay=next(m for m in fitted if all(c[2][0]<4 for c in m.calls))
        updated=next(m for m in fitted if any(c[2][0]>=10 for c in m.calls))
        trains={origin:[e for e in rows if e['query']==query and e['split']=='TRAIN']
            for origin,rows in [('OLD',old),('NEW',new)]}
        heldout={origin:[e for e in rows if e['query']==query and e['split']=='VALIDATION']
            for origin,rows in [('OLD',old),('NEW',new)]}
        calls=lambda rows:[(e['candidate_after'],e['baseline_after'],e['target_tail'],.1) for e in rows]
        assert replay.calls == (calls(trains['OLD'])+calls(trains['OLD']))*32
        assert updated.calls == (calls(trains['OLD'])+calls(trains['NEW']))*32
        assert len(replay.calls)==len(updated.calls)==1024
        assert not prior.calls and prior.updates==17
        assert all(m.frozen for m in models)
        cell=data['queries'][query]
        assert cell['old_train_roots']==[e['root_id'] for e in trains['OLD']]
        assert cell['new_train_roots']==[e['root_id'] for e in trains['NEW']]
        for origin in ('OLD','NEW'):
            assert cell['validation_roots'][origin]==[e['root_id'] for e in heldout[origin]]
            for method in ('PRIOR','REPLAY','UPDATED'):
                assert [p['root_id'] for p in cell['validation'][origin][method]]==[e['root_id'] for e in heldout[origin]]
                assert cell['validation_work'][origin][method]==dict(pair_predictions=12 if origin=='OLD' else 16)
        for method,model in [('PRIOR',prior),('REPLAY',replay),('UPDATED',updated)]:
            saved=cell['models'][method]
            assert saved['frozen_state']==saved['after_validation']==model.state()
            assert saved['fit_counts'].get('update_calls',0)==(0 if method=='PRIOR' else 1024)
            assert (local_tmp/saved['model_ref']).is_file()
        assert cell['binding']['life']==0 and cell['binding']['query']==query and cell['binding']['continuation']=='H2'
    assert (old,new)==originals
    assert all(path.read_bytes()==content for path,content in prior_bytes.items())


def test_evaluation_uses_four_frozen_methods_and_separate_costs(local_tmp,monkeypatch):
    source=runner.extract_source(*source_fixture())['snapshots'][0]
    factors=local_tmp/'factors.json'; factors.write_text(json.dumps({'rules':[]}));source['factored_ref']=str(factors)
    trained=dict(queries={});MockModel.instances=[];calls=[];teachers=[];candidates=[]
    for query in runner.QUERIES:
        trained['queries'][query]=dict(models={})
        for method,updates in [('PRIOR',17),('REPLAY',768),('UPDATED',896)]:
            path=local_tmp/f'{query}_{method}.json';path.write_text(json.dumps(dict(frozen=True,updates=updates,weights=[])))
            trained['queries'][query]['models'][method]=dict(model_ref=path.name)
    def load(source,representation,query,folder):
        assert representation=='SINGLE' and folder.is_dir()
        teacher=SimpleNamespace(counts=Counter(),query=query);teachers.append(teacher)
        leaf=SimpleNamespace(query=query)
        return leaf,leaf,teacher,dict(checkpoint_loads=1)
    def candidate(leaf,factors,build_dir):
        assert factors=={'rules':[]} and build_dir.parent.is_dir()
        value=SimpleNamespace(counts=Counter(),setup_counts=dict(cpp_library_cache_hits=1),setup_seconds=.2)
        candidates.append(value);return value
    def gate(teacher,candidate,model,query):
        assert model.frozen
        return SimpleNamespace(teacher=teacher,candidate=candidate,model=model,counts=Counter())
    def play(planner,life,query,method,replica):
        calls.append((life,query,method,replica,planner))
        if method=='H2':planner.counts['native_h2']+=2
        else:
            assert planner.model.frozen and planner.model.updates==dict(PRIOR=17,REPLAY=768,UPDATED=896)[method]
            planner.counts.update(baseline_native_h2=2,candidate_model_swipes=3,learner_pair_predictions=1)
            planner.teacher.counts['native_h2']+=2;planner.candidate.counts['model_swipes']+=3
        return dict(life=life,query=query,method=method,replica=replica,result=dict(utility=1.))
    monkeypatch.setattr(runner,'PairedAdvantage',MockModel);monkeypatch.setattr(runner,'AdvantagePlanner',gate)
    monkeypatch.setattr(runner,'H1ContinuationPlanner',candidate);monkeypatch.setattr(runner,'load_teacher',load)
    monkeypatch.setattr(runner,'leaf_state',lambda leaf,parent=False:dict(query=leaf.query,readonly=True))
    monkeypatch.setattr(runner,'play',play)
    monkeypatch.setattr(runner,'read_rows',lambda *a:pytest.fail('evaluation reread training branch traces'))
    result=runner.evaluate_lifecycle(source,trained,local_tmp)
    assert [(l,q,m,r) for l,q,m,r,_ in calls]==[(0,q,m,r) for q in runner.QUERIES for m in ('H2','PRIOR','REPLAY','UPDATED') for r in range(8)]
    with gzip.open(local_tmp/result['control_trace'],'rt') as stream:assert len(list(stream))==64
    for query in runner.QUERIES:
        cell=result['queries'][query]
        assert cell['parent_before']==cell['parent_after']==cell['leaf_before']==cell['leaf_after']
        assert cell['planners']['H2']['counts']==dict(native_h2=16)
        assert cell['teacher_total_counts']==dict(native_h2=64)
        assert cell['candidate_total_counts']==dict(model_swipes=72)
        gates=[]
        for method in ('PRIOR','REPLAY','UPDATED'):
            selected=[p for _,q,m,_,p in calls if q==query and m==method]
            assert all(p is selected[0] for p in selected);gates.append(selected[0])
            assert cell['planners'][method]['counts']==dict(baseline_native_h2=16,candidate_model_swipes=24,learner_pair_predictions=8)
            assert cell['planners'][method]['model_before']==cell['planners'][method]['model_after']
        assert len({id(g.model) for g in gates})==3
    assert all(not model.calls for model in MockModel.instances)


def test_fresh_game_streams_are_paired_and_cutoffs_are_preserved(local_tmp,monkeypatch):
    calls=[];environment_seeds=[]
    class Planner:
        def __init__(self,method):self.method=method;self.counts=Counter()
        def choose(self,board,query,**kwargs):
            calls.append((self.method,deepcopy(query),kwargs));self.counts['mock_choose']+=1
            action='LEFT' if self.counts['mock_choose']==1 else 'UP'
            choice=dict(action=action,afterstate=[2]+[0]*15,score=4,value=1.,status='ACTIVE',value_kind='estimated_return',
                action_values={action:dict(afterstate=[2]+[0]*15,score=4,value=1.,tail_value=1.-4/2048.)})
            if self.method!='H2':choice['selection']=dict(baseline_choice=deepcopy(choice),candidate_choice=deepcopy(choice))
            return choice
    def episode(seed,act,p_four,max_steps):
        assert (p_four,max_steps)==(.1,2000);environment_seeds.append(seed)
        return dict(seed=seed,actions=[act([1,1]+[0]*14,0),act([2,1]+[0]*14,1)])
    monkeypatch.setattr(runner.old,'run_episode',episode)
    monkeypatch.setattr(runner.old,'compact_trace',lambda game:dict(actions=game['actions']))
    status=['CUTOFF']
    monkeypatch.setattr(runner.old,'game_result',lambda game,query,counts,seconds:dict(status=status[0],utility=7.,policy_counts=counts))
    for query in runner.QUERIES:
        for method in ('H2','PRIOR','REPLAY','UPDATED'):
            row=runner.play(Planner(method),2,query,method,7)
            assert row['seed']==14590200007 and row['result']['utility'] is None
            assert [r['previous_action'] for r in row['choices']]==['DOWN','LEFT']
            assert [r['simulation_seed'] for r in row['choices']]==([None,None] if method=='H2' else [14582070000,14582070001])
            assert row['result']['policy_counts']==dict(mock_choose=2)
            for choice in row['choices']:
                assert choice['work']==dict(mock_choose=1)
                if method!='H2':
                    assert choice['selection']['candidate_choice']['action_values']
                    assert choice['selection']['baseline_choice']['action_values']
    assert environment_seeds==[14590200007]*8
    assert [c[2] for c in calls if c[0]=='H2']==[{}]*4
    for method in ('PRIOR','REPLAY','UPDATED'):
        assert [c[2] for c in calls if c[0]==method]==[dict(simulation_seed=14582070000,previous_action='DOWN'),dict(simulation_seed=14582070001,previous_action='LEFT')]*2
    status[0]='WON'
    assert runner.play(Planner('H2'),2,'risk1','H2',7)['result']['utility']==7.


def test_acquisition_runs_both_actions_on_every_paired_suffix_and_retains_cutoffs(local_tmp,monkeypatch):
    source=runner.extract_source(*source_fixture())['snapshots'][0]
    roots=[dict(root_id=query,life=0,query=query,board=[1,2]+[0]*14,
        actions=['LEFT','RIGHT'],suffix_seeds=list(range(8))) for query in runner.QUERIES]
    calls=[]
    def load(source,representation,query,folder):
        assert representation=='SINGLE' and folder.is_dir()
        teacher=SimpleNamespace(counts=Counter(),spawn_probabilities=[.9,.1])
        leaf=SimpleNamespace(query=query)
        return leaf,leaf,teacher,dict(checkpoint_loads=1)
    def branch(board,action,teacher,query,seed,max_steps,p_four):
        calls.append((deepcopy(board),action,deepcopy(query),seed,max_steps,p_four))
        teacher.counts['native_h2']+=1
        return dict(first_action=action,seed=seed,result=dict(status='CUTOFF' if seed==0 and action=='LEFT' else 'WON',
            environment_counts=dict(sampled_transitions=2,environment_random_draws=4),policy_counts=dict(native_h2=1)))
    monkeypatch.setattr(runner,'load_teacher',load);monkeypatch.setattr(runner,'run_branch',branch)
    monkeypatch.setattr(runner,'leaf_state',lambda leaf,parent=False:dict(query=leaf.query,readonly=True))
    result=runner.acquire_lifecycle(source,roots,local_tmp)
    assert [(a,q,s,m,p) for _,a,q,s,m,p in calls]==[(a,runner.QUERIES[q],s,2000,.1)
        for q in runner.QUERIES for s in range(8) for a in ('LEFT','RIGHT')]
    with gzip.open(local_tmp/result['consequences_trace'],'rt') as stream:rows=[json.loads(line) for line in stream]
    assert len(rows)==16
    for query in runner.QUERIES:
        cell=result['queries'][query]
        assert cell['physical_branches']==16 and cell['paired_records']==8
        assert cell['statuses']==dict(CUTOFF=1,WON=15)
        assert cell['environment_counts']==dict(sampled_transitions=32,environment_random_draws=64)
        assert cell['policy_counts']==dict(native_h2=16)
        assert cell['parent_before']==cell['parent_after']==cell['leaf_before']==cell['leaf_after']
        selected=[r for r in rows if r['root_id']==query]
        assert [r['suffix'] for r in selected]==list(range(8))
        assert all(r['continuation']=='H2' and r['seed']==r['suffix'] for r in selected)
        assert selected[0]['branches']['LEFT']['result']['status']=='CUTOFF'


@pytest.mark.parametrize('incomplete',[False,True])
def test_acquisition_precedes_fit_and_all_fits_are_frozen_before_control(local_tmp,monkeypatch,incomplete):
    retained=local_tmp/'retained';retained.mkdir()
    for name,payload in zip(('source_capsule.json','run.json','analysis.json'),source_fixture()):
        (retained/name).write_text(json.dumps(payload))
    history=source_fixture()[3]
    (retained/'analysis_initial_fail').mkdir()
    (retained/'analysis_initial_fail/analysis.json').write_text(json.dumps(dict(costs=history['extra_initial_work'])))
    (retained/'analysis_initial_fail/analysis_attempt.json').write_text(json.dumps(history['attempts'][0]))
    (retained/'analysis_attempt2.json').write_text(json.dumps(history['attempts'][1]))
    old=example_fixture('OLD');new=example_fixture('NEW')
    (retained/'examples.json').write_text(json.dumps(dict(examples=old)))
    cohort=dict(roots=[dict(life=e['life'],root_id=e['root_id']) for e in new])
    events=[];evaluated=[]
    class Pool:
        def __init__(self,**kwargs):assert kwargs==dict(max_workers=4)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def submit(self,function,*args):return SimpleNamespace(result=lambda value=function(*args):value)
    def snapshot(directory):
        assert (directory/'source_capsule.json').is_file()
        assert json.loads((directory/'cohort.json').read_text())==cohort
        events.append('snapshot')
    def acquire(source,roots,directory):
        frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status']=='frozen'
        assert frozen['lifecycles']==frozen['eval_lifecycles']==frozen['acquisition_lifecycles']==[]
        assert len(roots)==64 and {r['life'] for r in roots}=={source['life']}
        assert events[0]=='snapshot' and not any(isinstance(e,tuple) and e[0]=='train' for e in events)
        events.append(('acquire',source['life']))
        return dict(life=source['life'],consequences_trace=f"acquire_{source['life']}/paired.jsonl.gz",charged_samples=123)
    def examples(frozen_cohort,records):
        assert frozen_cohort==cohort
        assert list(records)==[dict(life=life,status='CUTOFF' if incomplete and life==3 else 'WON') for life in runner.LIVES]
        assert len([e for e in events if isinstance(e,tuple) and e[0]=='acquire'])==4
        events.append('examples')
        if incomplete:raise ValueError('paired terminal supervision is incomplete')
        return dict(examples=new)
    def train(source,old_rows,new_rows,directory):
        assert not evaluated and events.count('examples')==1
        frozen=json.loads((directory/'frozen_inputs.json').read_text())
        assert frozen['status']=='frozen' and frozen['settings']['epochs']==32
        assert old_rows==[e for e in old if e['life']==source['life']]
        assert new_rows==[e for e in new if e['life']==source['life']]
        assert json.loads((directory/'run.json').read_text())['status']=='training'
        events.append(('train',source['life']));return dict(life=source['life'],queries={'frozen':True})
    def evaluate(source,trained,directory):
        frozen=json.loads((directory/'frozen_training.json').read_text())
        assert frozen['status']=='trained_frozen'
        assert [r['life'] for r in frozen['lifecycles']]==list(runner.LIVES)
        assert [r['life'] for r in frozen['acquisition_lifecycles']]==list(runner.LIVES)
        assert frozen['eval_lifecycles']==[] and trained['queries']=={'frozen':True}
        assert len([e for e in events if isinstance(e,tuple) and e[0]=='train'])==4
        evaluated.append(source['life']);events.append(('eval',source['life']))
        return dict(life=source['life'])
    monkeypatch.setattr(runner,'SOURCE',retained);monkeypatch.setattr(runner,'build_cohort',lambda sources:deepcopy(cohort))
    monkeypatch.setattr(runner,'build_examples',examples);monkeypatch.setattr(runner,'snapshot_code',snapshot)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',Pool);monkeypatch.setattr(runner,'as_completed',lambda futures:reversed(futures))
    monkeypatch.setattr(runner,'acquire_lifecycle',acquire);monkeypatch.setattr(runner,'train_lifecycle',train)
    monkeypatch.setattr(runner,'evaluate_lifecycle',evaluate)
    monkeypatch.setattr(runner,'read_rows',lambda path:iter([dict(life=int(path.parent.name.split('_')[-1]),
        status='CUTOFF' if incomplete and path.parent.name=='acquire_3' else 'WON')]))
    directory=local_tmp/'run'
    if incomplete:
        with pytest.raises(ValueError,match='paired terminal supervision is incomplete'):runner.run(directory)
    else:runner.run(directory)
    result=json.loads((directory/'run.json').read_text())
    prefix=['snapshot',*[('acquire',life) for life in runner.LIVES],'examples']
    if incomplete:
        assert events==prefix and result['status']=='supervision_incomplete'
        assert result['lifecycles']==result['eval_lifecycles']==[] and not (directory/'frozen_training.json').exists()
        assert result['error']=='paired terminal supervision is incomplete'
    else:
        assert events==prefix+[(stage,life) for stage in ('train','eval') for life in runner.LIVES]
        assert result['status']=='complete' and [r['life'] for r in result['eval_lifecycles']]==list(runner.LIVES)
    assert len(result['acquisition_lifecycles'])==4 and sum(r['charged_samples'] for r in result['acquisition_lifecycles'])==492
    assert result['settings']['physical_games']==256 and result['settings']['physical_branches']==4096
    assert result['inherited_costs']==dict(prior=1,v144_experiment={'v144':2},v144_analysis_history=history)
